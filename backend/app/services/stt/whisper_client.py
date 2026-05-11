from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from app.services.stt.base import STTClient, STTResult

logger = logging.getLogger(__name__)


class WhisperClient(STTClient):
    """faster-whisper backed STT.

    Heavy deps (`faster-whisper`, `ctranslate2`) are lazy-imported so the API
    server starts without them. Install with: `pip install faster-whisper`.
    """

    name = "faster-whisper"

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "auto",
        compute_type: str = "int8_float16",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Any | None = None
        self._lock = asyncio.Lock()

    async def _load(self) -> Any:
        if self._model is not None:
            return self._model
        async with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "faster-whisper not installed. `pip install faster-whisper`"
                ) from e
            logger.info(
                "loading whisper model size=%s device=%s compute=%s",
                self.model_size,
                self.device,
                self.compute_type,
            )
            # Run in a thread to avoid blocking the event loop.
            self._model = await asyncio.to_thread(
                WhisperModel,
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            return self._model

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime: str,
        language: str | None = "ko",
    ) -> STTResult:
        model = await self._load()

        def _run() -> tuple[str, str | None, float]:
            buf = io.BytesIO(audio_bytes)
            segments, info = model.transcribe(
                buf,
                language=language,
                vad_filter=True,
            )
            text = "".join(seg.text for seg in segments).strip()
            return text, info.language, float(getattr(info, "duration", 0.0))

        text, lang, duration = await asyncio.to_thread(_run)
        return STTResult(text=text, language=lang, duration_s=duration)
