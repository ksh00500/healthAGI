from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSResult:
    audio_bytes: bytes
    mime: str
    sample_rate: int


class TTSClient(ABC):
    """Text-to-speech backend."""

    name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, language: str = "ko") -> TTSResult: ...
