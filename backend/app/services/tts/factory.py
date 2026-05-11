from __future__ import annotations

import os

from app.services.tts.base import TTSClient
from app.services.tts.mock_client import get_mock_tts
from app.services.tts.piper_client import PiperClient
from app.services.tts.xtts_client import XTTSClient

_singleton: TTSClient | None = None


def get_tts_client() -> TTSClient:
    """Returns the configured TTS backend.

    HEALTHAGI_TTS_BACKEND in {mock, xtts, piper}; default xtts.
    For piper, set HEALTHAGI_PIPER_VOICE to the .onnx model path.
    """
    global _singleton
    backend = os.getenv("HEALTHAGI_TTS_BACKEND", "xtts")
    if backend == "mock":
        return get_mock_tts()
    if _singleton is None:
        if backend == "piper":
            voice = os.getenv("HEALTHAGI_PIPER_VOICE", "/models/piper/ko_KR-glow_tts.onnx")
            _singleton = PiperClient(voice_path=voice)
        else:
            _singleton = XTTSClient(
                model_name=os.getenv(
                    "HEALTHAGI_XTTS_MODEL",
                    "tts_models/multilingual/multi-dataset/xtts_v2",
                ),
                speaker_wav=os.getenv("HEALTHAGI_XTTS_SPEAKER"),
            )
    return _singleton
