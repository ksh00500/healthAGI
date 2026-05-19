from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from app.services.tts.base import TTSClient, TTSResult

logger = logging.getLogger(__name__)


class XTTSClient(TTSClient):
    """Coqui XTTS v2 backend (lazy-loaded).

    Install with: `pip install TTS` (or `coqui-tts` fork).
    """

    name = "xtts"

    def __init__(
        self,
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        speaker_wav: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.speaker_wav = speaker_wav
        self._model: Any | None = None
        self._lock = asyncio.Lock()

    async def _load(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._lock:
            if self._model is not None:
                return self._model
            try:
                from TTS.api import TTS
            except ImportError as e:
                raise RuntimeError(
                    "Coqui TTS not installed. `pip install TTS`"
                ) from e
            logger.info("loading xtts model=%s", self.model_name)
            self._model = await asyncio.to_thread(TTS, self.model_name)
            return self._model

    async def synthesize(self, text: str, language: str = "ko") -> TTSResult:
        import wave

        model = await self._load()

        def _run() -> tuple[bytes, int]:
            wav_data = model.tts(
                text=text,
                language=language,
                speaker_wav=self.speaker_wav,
            )
            # Coqui returns float32 list at 24kHz for XTTS v2.
            sample_rate = getattr(model, "output_sample_rate", 24000) or 24000
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                # Convert float [-1, 1] to int16 PCM
                int16 = (
                    (max(-1.0, min(1.0, float(s))) * 32767) for s in wav_data
                )
                w.writeframes(b"".join(int(x).to_bytes(2, "little", signed=True) for x in int16))
            return buf.getvalue(), int(sample_rate)

        audio, sr = await asyncio.to_thread(_run)
        return TTSResult(audio_bytes=audio, mime="audio/wav", sample_rate=sr)
