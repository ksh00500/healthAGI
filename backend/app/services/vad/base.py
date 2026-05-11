from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VADResult:
    """Output of a one-shot VAD check on a PCM16 mono buffer."""

    has_speech: bool
    speech_ms: int
    silence_tail_ms: int


class VADClient(ABC):
    name: str = "base"

    @abstractmethod
    async def check(self, pcm16_mono: bytes, sample_rate: int = 16000) -> VADResult:
        """Return whether the buffer contains speech (heuristic, not gated)."""
