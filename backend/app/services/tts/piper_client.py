from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.services.tts.base import TTSClient, TTSResult

logger = logging.getLogger(__name__)


class PiperClient(TTSClient):
    """Piper TTS backend (lazy-loaded). Faster, lower quality fallback for XTTS.

    Install with: `pip install piper-tts` and download a Korean voice model
    (e.g. ko_KR-glow_tts) into the configured path.
    """

    name = "piper"

    def __init__(self, voice_path: str) -> None:
        self.voice_path = voice_path
        self._voice: Any | None = None
        self._lock = asyncio.Lock()

    async def _load(self) -> Any:
        if self._voice is not None:
            return self._voice
        async with self._lock:
            if self._voice is not None:
                return self._voice
            try:
                from piper import PiperVoice  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "piper-tts not installed. `pip install piper-tts`"
                ) from e
            if not Path(self.voice_path).exists():
                raise RuntimeError(f"Piper voice file not found: {self.voice_path}")
            logger.info("loading piper voice=%s", self.voice_path)
            self._voice = await asyncio.to_thread(PiperVoice.load, self.voice_path)
            return self._voice

    async def synthesize(self, text: str, language: str = "ko") -> TTSResult:
        import io
        import wave

        voice = await self._load()

        def _run() -> tuple[bytes, int]:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                voice.synthesize(text, w)
            sr = voice.config.sample_rate
            return buf.getvalue(), int(sr)

        audio, sr = await asyncio.to_thread(_run)
        return TTSResult(audio_bytes=audio, mime="audio/wav", sample_rate=sr)
