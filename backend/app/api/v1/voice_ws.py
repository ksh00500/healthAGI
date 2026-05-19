from __future__ import annotations

import asyncio
import base64
import io
import logging
import wave
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.db import get_session
from app.core.security import decode_token
from app.models.chat import ChatConversation, ChatMessage
from app.models.user import User
from app.services.llm import get_llm_client
from app.services.llm.base import ChatTurn
from app.services.llm.prompts import build_system_prompt, turns_from_history
from app.services.stt import get_stt_client
from app.services.tts import get_tts_client
from app.services.vad import get_vad_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["voice-ws"])


MAX_AUDIO_BYTES = 20 * 1024 * 1024


def _open_session(ws: WebSocket) -> AsyncGenerator[AsyncSession, None]:
    """Resolve the get_session dep, honoring app.dependency_overrides (tests)."""
    factory = ws.app.dependency_overrides.get(get_session) or get_session
    return factory()


async def _authenticate(ws: WebSocket, token: str | None) -> User | None:
    if not token:
        await ws.close(code=4401, reason="missing token")
        return None
    try:
        user_id: UUID = decode_token(token, "access")
    except JWTError as e:
        await ws.close(code=4401, reason=f"invalid token: {e}")
        return None
    session_gen = _open_session(ws)
    session: AsyncSession = await session_gen.__anext__()
    try:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            await ws.close(code=4401, reason="user not found")
            return None
        return user
    finally:
        await session.close()
        try:
            await session_gen.aclose()
        except Exception:  # noqa: BLE001
            pass


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap raw PCM16 mono in a WAV container so faster-whisper can decode it."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)
    return buf.getvalue()


@router.websocket("/ws/voice")
async def voice_ws(
    ws: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """Full-duplex voice protocol.

    Client → server (JSON):
      {type:"start", conversation_id?, sample_rate?, audio_mime?}
      {type:"audio", pcm_b64}          — raw PCM16 mono chunks, OR
      {type:"audio_file", b64, mime}   — whole-file (m4a/wav) one-shot
      {type:"end_of_speech"}
      {type:"interrupt"}
      {type:"close"}

    Server → client (JSON):
      {type:"ready", conversation_id, sample_rate}
      {type:"stt_final", text, user_message_id}
      {type:"llm_token", text}
      {type:"llm_done", reply_text, assistant_message_id}
      {type:"tts_chunk", seq, audio_b64, mime, sample_rate, text}
      {type:"tts_done"}
      {type:"error", message}
    """
    await ws.accept()
    user = await _authenticate(ws, token)
    if user is None:
        return

    settings = get_settings()
    llm = get_llm_client()
    stt = get_stt_client()
    tts = get_tts_client()
    vad = get_vad_client()

    pcm_buffer = bytearray()
    audio_file: bytes | None = None
    audio_file_mime: str | None = None
    sample_rate = 16000
    conversation_id: UUID | None = None
    active_task: asyncio.Task[None] | None = None

    async def send(payload: dict[str, Any]) -> None:
        try:
            await ws.send_json(payload)
        except Exception:  # noqa: BLE001
            logger.exception("ws send failed")

    async def cancel_active() -> None:
        nonlocal active_task
        if active_task is None:
            return
        active_task.cancel()
        try:
            await active_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        active_task = None

    async def run_turn(audio_bytes: bytes, mime: str) -> None:
        session_gen = get_session()
        session: AsyncSession = await session_gen.__anext__()
        try:
            nonlocal conversation_id

            # Resolve / create conversation.
            if conversation_id is not None:
                conv = await session.scalar(
                    select(ChatConversation)
                    .options(selectinload(ChatConversation.messages))
                    .where(
                        ChatConversation.id == conversation_id,
                        ChatConversation.user_id == user.id,
                        ChatConversation.deleted_at.is_(None),
                    )
                )
                if not conv:
                    await send({"type": "error", "message": "conversation not found"})
                    return
            else:
                conv = ChatConversation(user_id=user.id, mode="voice")
                session.add(conv)
                await session.commit()
                await session.refresh(conv)
                conversation_id = conv.id

            # 1) STT
            try:
                stt_res = await stt.transcribe(audio_bytes, mime=mime, language="ko")
            except Exception as e:  # noqa: BLE001
                await send({"type": "error", "message": f"STT failed: {e}"})
                return
            transcript = (stt_res.text or "").strip()
            if not transcript:
                await send({"type": "error", "message": "no speech detected"})
                return

            user_msg = ChatMessage(
                conversation_id=conv.id, role="user", content=transcript
            )
            session.add(user_msg)
            await session.commit()
            await session.refresh(user_msg)
            await send(
                {
                    "type": "stt_final",
                    "text": transcript,
                    "user_message_id": str(user_msg.id),
                    "conversation_id": str(conv.id),
                }
            )

            # 2) LLM streaming
            system_prompt = await build_system_prompt(session, user)
            history_rows = await session.scalars(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conv.id)
                .order_by(ChatMessage.created_at)
            )
            history = [{"role": m.role, "content": m.content} for m in history_rows]
            turns: list[ChatTurn] = [ChatTurn(role="system", content=system_prompt)]
            turns.extend(turns_from_history(history))

            model = settings.llm_voice_model
            collected: list[str] = []
            pending_sentences: asyncio.Queue[str | None] = asyncio.Queue()

            async def tts_worker() -> None:
                seq = 0
                while True:
                    sentence = await pending_sentences.get()
                    if sentence is None:
                        return
                    try:
                        res = await tts.synthesize(sentence, language="ko")
                        await send(
                            {
                                "type": "tts_chunk",
                                "seq": seq,
                                "audio_b64": base64.b64encode(res.audio_bytes).decode("ascii"),
                                "mime": res.mime,
                                "sample_rate": res.sample_rate,
                                "text": sentence,
                            }
                        )
                        seq += 1
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:  # noqa: BLE001
                        await send({"type": "error", "message": f"TTS chunk failed: {e}"})

            sentence_buf: list[str] = []
            tts_task = asyncio.create_task(tts_worker())

            try:
                async for chunk in llm.chat_stream(turns, model=model, temperature=0.4):
                    if chunk.kind == "token":
                        collected.append(chunk.text)
                        sentence_buf.append(chunk.text)
                        await send({"type": "llm_token", "text": chunk.text})
                        joined = "".join(sentence_buf)
                        last = joined[-1] if joined else ""
                        if last in ".?!。？！\n" and len(joined.strip()) >= 2:
                            sentence = joined.strip()
                            sentence_buf = []
                            await pending_sentences.put(sentence)
                    elif chunk.kind == "done":
                        break
                    elif chunk.kind == "error":
                        await send({"type": "error", "message": chunk.error or "LLM error"})
                        await pending_sentences.put(None)
                        tts_task.cancel()
                        return
            except asyncio.CancelledError:
                tts_task.cancel()
                raise

            tail = "".join(sentence_buf).strip()
            if tail:
                await pending_sentences.put(tail)
            await pending_sentences.put(None)  # signal end

            reply_text = "".join(collected).strip() or "(빈 응답)"
            assistant_msg = ChatMessage(
                conversation_id=conv.id,
                role="assistant",
                content=reply_text,
                model=model,
            )
            session.add(assistant_msg)
            await session.commit()
            await session.refresh(assistant_msg)
            await send(
                {
                    "type": "llm_done",
                    "reply_text": reply_text,
                    "assistant_message_id": str(assistant_msg.id),
                }
            )

            # Drain remaining TTS chunks.
            try:
                await tts_task
            except asyncio.CancelledError:
                pass

            await send({"type": "tts_done"})
        except asyncio.CancelledError:
            await send({"type": "tts_done", "interrupted": True})
            raise
        finally:
            await session.close()
            try:
                await session_gen.aclose()
            except Exception:  # noqa: BLE001
                pass

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "start":
                conv_raw = msg.get("conversation_id")
                conversation_id = UUID(conv_raw) if conv_raw else None
                sample_rate = int(msg.get("sample_rate") or 16000)
                pcm_buffer = bytearray()
                audio_file = None
                audio_file_mime = None
                await send(
                    {
                        "type": "ready",
                        "conversation_id": str(conversation_id) if conversation_id else None,
                        "sample_rate": sample_rate,
                    }
                )

            elif mtype == "audio":
                if audio_file is not None:
                    await send(
                        {"type": "error", "message": "audio_file already set; reset with start"}
                    )
                    continue
                try:
                    frame = base64.b64decode(msg.get("pcm_b64") or "", validate=False)
                except Exception:  # noqa: BLE001
                    await send({"type": "error", "message": "invalid pcm_b64"})
                    continue
                if len(pcm_buffer) + len(frame) > MAX_AUDIO_BYTES:
                    await send({"type": "error", "message": "audio too large"})
                    pcm_buffer = bytearray()
                    continue
                pcm_buffer.extend(frame)

            elif mtype == "audio_file":
                try:
                    blob = base64.b64decode(msg.get("b64") or "", validate=False)
                except Exception:  # noqa: BLE001
                    await send({"type": "error", "message": "invalid b64"})
                    continue
                if len(blob) > MAX_AUDIO_BYTES:
                    await send({"type": "error", "message": "audio too large"})
                    continue
                audio_file = blob
                audio_file_mime = msg.get("mime") or "audio/m4a"

            elif mtype == "end_of_speech":
                if active_task is not None and not active_task.done():
                    await send({"type": "error", "message": "turn already in progress"})
                    continue
                if audio_file is not None:
                    bytes_ = audio_file
                    mime = audio_file_mime or "audio/m4a"
                    audio_file = None
                    audio_file_mime = None
                elif pcm_buffer:
                    # Optional server-side VAD check before paying for STT.
                    try:
                        vad_res = await vad.check(bytes(pcm_buffer), sample_rate=sample_rate)
                    except Exception:  # noqa: BLE001
                        vad_res = None
                    if vad_res is not None and not vad_res.has_speech:
                        await send({"type": "error", "message": "no speech detected (VAD)"})
                        pcm_buffer = bytearray()
                        continue
                    bytes_ = _pcm_to_wav(bytes(pcm_buffer), sample_rate)
                    mime = "audio/wav"
                    pcm_buffer = bytearray()
                else:
                    await send({"type": "error", "message": "no audio buffered"})
                    continue
                # Run the turn inline — keeps WS message loop and turn
                # output on the same task, which avoids TestClient WS
                # concurrency edge-cases. Interrupt during a turn is
                # therefore deferred to Phase 5 (streaming PCM mode).
                try:
                    await run_turn(bytes_, mime)
                except Exception as e:  # noqa: BLE001
                    await send({"type": "error", "message": f"turn failed: {e}"})

            elif mtype == "interrupt":
                # Inline-turn mode: nothing concurrent to cancel yet.
                await cancel_active()

            elif mtype == "close":
                await cancel_active()
                break

            else:
                await send({"type": "error", "message": f"unknown message type: {mtype}"})
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        logger.exception("voice ws error")
        try:
            await send({"type": "error", "message": str(e)})
        except Exception:  # noqa: BLE001
            pass
    finally:
        await cancel_active()
        try:
            await ws.close(code=status.WS_1000_NORMAL_CLOSURE)
        except Exception:  # noqa: BLE001
            pass
