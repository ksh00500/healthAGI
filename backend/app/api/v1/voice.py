from __future__ import annotations

import base64
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.voice import VoiceTurnResponse
from app.services.llm import get_llm_client
from app.services.llm.base import ChatTurn
from app.services.llm.prompts import build_system_prompt, turns_from_history
from app.services.stt import get_stt_client
from app.services.tts import get_tts_client

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB ~ a couple of minutes of WAV @ 16k mono


@router.post("/turn", response_model=VoiceTurnResponse)
async def voice_turn(
    user: CurrentUser,
    session: SessionDep,
    audio: UploadFile = File(..., description="audio blob (wav/m4a/webm/ogg)"),
    conversation_id: UUID | None = Form(default=None),
) -> VoiceTurnResponse:
    """One push-to-talk turn: STT → LLM → TTS, persisted in a chat conversation.

    If `conversation_id` is omitted, a new voice conversation is created.
    """
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty audio")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"audio too large ({len(audio_bytes)} > {MAX_AUDIO_BYTES})",
        )
    mime = audio.content_type or "audio/wav"

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
            raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    else:
        conv = ChatConversation(user_id=user.id, mode="voice", title=None)
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

    # 1. STT
    stt = get_stt_client()
    try:
        stt_res = await stt.transcribe(audio_bytes, mime=mime, language="ko")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"STT failed: {e}"
        ) from e
    transcript = stt_res.text.strip()
    if not transcript:
        # 422 Unprocessable Content (the `_ENTITY` alias is deprecated upstream).
        raise HTTPException(422, "transcript empty — no speech detected")

    # 2. Persist user message.
    user_msg = ChatMessage(conversation_id=conv.id, role="user", content=transcript)
    session.add(user_msg)
    await session.commit()
    await session.refresh(user_msg)

    # 3. LLM (non-streaming for PTT — keep latency budget tight on assemble side).
    system_prompt = await build_system_prompt(session, user)
    history_rows = await session.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at)
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    settings = get_settings()
    # Use the smaller voice-tuned model for latency.
    model = settings.llm_voice_model
    llm = get_llm_client()

    turns: list[ChatTurn] = [ChatTurn(role="system", content=system_prompt)]
    turns.extend(turns_from_history(history))

    collected: list[str] = []
    eval_count: int | None = None
    prompt_eval_count: int | None = None
    try:
        async for chunk in llm.chat_stream(turns, model=model, temperature=0.4):
            if chunk.kind == "token":
                collected.append(chunk.text)
            elif chunk.kind == "done":
                eval_count = chunk.eval_count
                prompt_eval_count = chunk.prompt_eval_count
                break
            elif chunk.kind == "error":
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY, f"LLM error: {chunk.error}"
                )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"LLM failed: {e}") from e
    reply_text = "".join(collected).strip() or "(빈 응답)"

    # 4. Persist assistant message.
    assistant_msg = ChatMessage(
        conversation_id=conv.id,
        role="assistant",
        content=reply_text,
        model=model,
        tokens_in=prompt_eval_count,
        tokens_out=eval_count,
    )
    session.add(assistant_msg)
    await session.commit()
    await session.refresh(assistant_msg)

    # 5. TTS
    tts = get_tts_client()
    try:
        tts_res = await tts.synthesize(reply_text, language="ko")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"TTS failed: {e}"
        ) from e

    return VoiceTurnResponse(
        conversation_id=conv.id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
        transcript=transcript,
        reply_text=reply_text,
        audio_b64=base64.b64encode(tts_res.audio_bytes).decode("ascii"),
        audio_mime=tts_res.mime,
        audio_sample_rate=tts_res.sample_rate,
        stt_language=stt_res.language,
        stt_duration_s=stt_res.duration_s,
        tokens_in=prompt_eval_count,
        tokens_out=eval_count,
    )
