from __future__ import annotations

import os

from app.services.vad.base import VADClient
from app.services.vad.mock import get_mock_vad
from app.services.vad.silero import SileroVAD

_singleton: VADClient | None = None


def get_vad_client() -> VADClient:
    """Return the configured VAD backend.

    HEALTHAGI_VAD_BACKEND in {silero, mock}. Default: silero (lazy).
    """
    global _singleton
    if os.getenv("HEALTHAGI_VAD_BACKEND") == "mock":
        return get_mock_vad()
    if _singleton is None:
        _singleton = SileroVAD()
    return _singleton
