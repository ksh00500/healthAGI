from __future__ import annotations

import os

from app.services.stt.base import STTClient
from app.services.stt.mock_client import get_mock_stt
from app.services.stt.whisper_client import WhisperClient

_singleton: STTClient | None = None


def get_stt_client() -> STTClient:
    """Returns the configured STT backend.

    Set HEALTHAGI_STT_BACKEND=mock for tests / offline.
    Otherwise returns a process-singleton WhisperClient that lazy-loads on
    first use.
    """
    global _singleton
    if os.getenv("HEALTHAGI_STT_BACKEND") == "mock":
        return get_mock_stt()
    if _singleton is None:
        _singleton = WhisperClient(
            model_size=os.getenv("HEALTHAGI_WHISPER_MODEL", "large-v3"),
            device=os.getenv("HEALTHAGI_WHISPER_DEVICE", "auto"),
            compute_type=os.getenv("HEALTHAGI_WHISPER_COMPUTE", "int8_float16"),
        )
    return _singleton
