from __future__ import annotations

import io
import struct
import wave

from app.services.tts.base import TTSClient, TTSResult


def _silent_wav(seconds: float = 0.5, sample_rate: int = 16000) -> bytes:
    """Generate a tiny silent WAV blob — valid playback target without any model."""
    n = max(1, int(seconds * sample_rate))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(struct.pack("<" + "h" * n, *([0] * n)))
    return buf.getvalue()


class MockTTSClient(TTSClient):
    """Returns a short silent WAV. Records inputs for assertion."""

    name = "mock"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def synthesize(self, text: str, language: str = "ko") -> TTSResult:
        self.calls.append((text, language))
        return TTSResult(audio_bytes=_silent_wav(), mime="audio/wav", sample_rate=16000)


_singleton: MockTTSClient | None = None


def get_mock_tts() -> MockTTSClient:
    global _singleton
    if _singleton is None:
        _singleton = MockTTSClient()
    return _singleton


def reset_mock_tts() -> None:
    global _singleton
    _singleton = MockTTSClient()
