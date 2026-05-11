from __future__ import annotations

import base64
import io
import struct
import wave

import pytest
from httpx import AsyncClient

from app.services.llm.mock_client import get_mock_client
from app.services.stt.mock_client import get_mock_stt
from app.services.tts.mock_client import get_mock_tts


def _fake_wav_bytes(seconds: float = 0.5) -> bytes:
    """A short silent WAV the client could plausibly upload."""
    sr = 16000
    n = int(seconds * sr)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack("<" + "h" * n, *([0] * n)))
    return buf.getvalue()


async def _register(client: AsyncClient, email: str = "voice@x.com") -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_voice_turn_creates_conversation(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    get_mock_stt().push("오늘 가슴 운동해도 될까?")
    get_mock_client().queue("회복 상태를 보면 가슴은 준비됨이라 가능합니다.")

    files = {"audio": ("clip.wav", _fake_wav_bytes(), "audio/wav")}
    r = await client.post("/v1/voice/turn", headers=h, files=files)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["transcript"] == "오늘 가슴 운동해도 될까?"
    assert "가슴" in data["reply_text"]
    assert data["audio_mime"] == "audio/wav"
    audio = base64.b64decode(data["audio_b64"])
    assert audio.startswith(b"RIFF") and b"WAVE" in audio[:12]

    # Conversation row created with mode=voice and 2 messages.
    cid = data["conversation_id"]
    r = await client.get(f"/v1/chat/conversations/{cid}", headers=h)
    body = r.json()
    assert body["mode"] == "voice"
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant"]


@pytest.mark.asyncio
async def test_voice_turn_continues_existing_conversation(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # First turn — creates a conversation.
    get_mock_stt().push("첫 메시지")
    get_mock_client().queue("첫 답변")
    files = {"audio": ("a.wav", _fake_wav_bytes(), "audio/wav")}
    r = await client.post("/v1/voice/turn", headers=h, files=files)
    cid = r.json()["conversation_id"]

    # Second turn — pass conversation_id, expect append.
    get_mock_stt().push("두 번째 질문")
    get_mock_client().queue("두 번째 답변")
    r = await client.post(
        "/v1/voice/turn",
        headers=h,
        files={"audio": ("b.wav", _fake_wav_bytes(), "audio/wav")},
        data={"conversation_id": cid},
    )
    assert r.status_code == 200
    assert r.json()["conversation_id"] == cid

    r = await client.get(f"/v1/chat/conversations/{cid}", headers=h)
    msgs = r.json()["messages"]
    assert len(msgs) == 4
    assert [m["content"] for m in msgs] == [
        "첫 메시지",
        "첫 답변",
        "두 번째 질문",
        "두 번째 답변",
    ]


@pytest.mark.asyncio
async def test_voice_turn_rejects_empty_audio(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/v1/voice/turn",
        headers=h,
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_voice_turn_rejects_silent_transcript(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    get_mock_stt().push("   ")  # whitespace only
    r = await client.post(
        "/v1/voice/turn",
        headers=h,
        files={"audio": ("silent.wav", _fake_wav_bytes(), "audio/wav")},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_tts_called_with_reply_text(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    get_mock_stt().push("물 얼마나 마셔야 해?")
    get_mock_client().queue("하루 2~3리터를 권장합니다.")
    r = await client.post(
        "/v1/voice/turn",
        headers=h,
        files={"audio": ("c.wav", _fake_wav_bytes(), "audio/wav")},
    )
    assert r.status_code == 200
    tts_calls = get_mock_tts().calls
    assert tts_calls, "TTS was not called"
    assert tts_calls[-1][0] == "하루 2~3리터를 권장합니다."
    assert tts_calls[-1][1] == "ko"
