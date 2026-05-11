from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.vad.base import VADClient, VADResult

logger = logging.getLogger(__name__)


class SileroVAD(VADClient):
    """ONNX-backed silero VAD. Heavy deps lazy-imported.

    Install: `pip install silero-vad onnxruntime`
    """

    name = "silero"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._model: Any | None = None
        self._utils: Any | None = None
        self._lock = asyncio.Lock()

    async def _load(self) -> tuple[Any, Any]:
        if self._model is not None and self._utils is not None:
            return self._model, self._utils
        async with self._lock:
            if self._model is not None and self._utils is not None:
                return self._model, self._utils
            try:
                import torch  # type: ignore # noqa: F401  (silero-vad uses torch)
                from silero_vad import load_silero_vad  # type: ignore

                # silero_vad>=5 also exposes get_speech_timestamps via the package
                from silero_vad import get_speech_timestamps  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "silero-vad not installed. `pip install silero-vad torch`"
                ) from e
            logger.info("loading silero VAD")
            self._model = await asyncio.to_thread(load_silero_vad)
            self._utils = get_speech_timestamps
            return self._model, self._utils

    async def check(self, pcm16_mono: bytes, sample_rate: int = 16000) -> VADResult:
        import numpy as np  # type: ignore

        model, get_ts = await self._load()

        def _run() -> tuple[list[dict[str, int]], int]:
            arr = np.frombuffer(pcm16_mono, dtype=np.int16).astype(np.float32) / 32768.0
            timestamps = get_ts(
                arr,
                model,
                sampling_rate=sample_rate,
                threshold=self.threshold,
                return_seconds=False,
            )
            return list(timestamps), arr.shape[0]

        timestamps, total_samples = await asyncio.to_thread(_run)
        if not timestamps:
            return VADResult(
                has_speech=False,
                speech_ms=0,
                silence_tail_ms=int(total_samples / sample_rate * 1000),
            )
        last_end = timestamps[-1]["end"]
        silence_tail = max(0, total_samples - last_end)
        speech_total = sum(seg["end"] - seg["start"] for seg in timestamps)
        return VADResult(
            has_speech=True,
            speech_ms=int(speech_total / sample_rate * 1000),
            silence_tail_ms=int(silence_tail / sample_rate * 1000),
        )
