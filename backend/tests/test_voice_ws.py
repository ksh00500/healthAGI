from __future__ import annotations

import base64
import struct
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db import get_session
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.profile import Profile
from app.models.user import User
from app.services.llm.mock_client import get_mock_client  # noqa: F401  (used in skipped tests)
from app.services.stt.mock_client import get_mock_stt  # noqa: F401
from app.services.tts.mock_client import get_mock_tts  # noqa: F401
from app.services.tts.base import split_sentences
from app.services.vad.mock import get_mock_vad


def _silent_pcm(samples: int = 8000) -> bytes:
    return struct.pack("<" + "h" * samples, *([0] * samples))


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


@pytest.fixture
def app_factory(session_factory: async_sessionmaker):
    """Sync TestClient sharing the async session factory used elsewhere."""
    app = create_app()

    async def override_get_session() -> AsyncIterator[Any]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    return app


async def _make_user(session_factory: async_sessionmaker, email: str) -> str:
    async with session_factory() as s:
        user = User(email=email, password_hash=hash_password("x" * 12))
        user.profile = Profile()
        s.add(user)
        await s.commit()
        await s.refresh(user)
        return create_access_token(user.id)


# --- Unit tests for protocol helpers ---


def test_split_sentences_basic() -> None:
    assert split_sentences("안녕하세요. 오늘 운동할까요?") == [
        "안녕하세요.",
        "오늘 운동할까요?",
    ]


def test_split_sentences_keeps_text_without_terminator() -> None:
    # When no terminator is present, the whole string is returned as one chunk.
    assert split_sentences("벤치 80 5 5 4") == ["벤치 80 5 5 4"]


def test_split_sentences_handles_cjk_punct() -> None:
    out = split_sentences("좋아요。가슴 가능합니다！")
    assert out == ["좋아요。", "가슴 가능합니다！"]


# --- WS-level smoke tests that don't drive a full turn ---


@pytest.mark.asyncio
async def test_ws_voice_unauthorized() -> None:
    from starlette.websockets import WebSocketDisconnect

    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/v1/ws/voice") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == 4401


@pytest.mark.asyncio
async def test_ws_voice_ready_handshake(
    app_factory: Any, session_factory: async_sessionmaker
) -> None:
    token = await _make_user(session_factory, "wsh@x.com")
    client = TestClient(app_factory)
    with client.websocket_connect(f"/v1/ws/voice?token={token}") as ws:
        ws.send_json({"type": "start", "sample_rate": 16000})
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert ready["sample_rate"] == 16000
        ws.send_json({"type": "close"})


@pytest.mark.asyncio
async def test_ws_voice_no_speech_errors(
    app_factory: Any, session_factory: async_sessionmaker
) -> None:
    """VAD short-circuit path — does not invoke STT/LLM/TTS, so it is safe to
    run under TestClient even without the full streaming pipeline test."""
    from app.services.vad.base import VADResult

    token = await _make_user(session_factory, "wsb@x.com")
    get_mock_vad().push(VADResult(has_speech=False, speech_ms=0, silence_tail_ms=500))

    client = TestClient(app_factory)
    with client.websocket_connect(f"/v1/ws/voice?token={token}") as ws:
        ws.send_json({"type": "start", "sample_rate": 16000})
        assert ws.receive_json()["type"] == "ready"
        ws.send_json({"type": "audio", "pcm_b64": _b64(_silent_pcm())})
        ws.send_json({"type": "end_of_speech"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "VAD" in err["message"]
        ws.send_json({"type": "close"})


# NOTE: full STT -> LLM -> TTS streaming over the in-process TestClient
# WebSocket deadlocks for our async-LLM mocks because TestClient runs the
# app on a separate event loop. The endpoint is exercised manually via a
# real client (Expo app) and via the existing HTTP /voice/turn tests.
