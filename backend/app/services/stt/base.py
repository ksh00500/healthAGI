from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class STTResult:
    text: str
    language: str | None = None
    duration_s: float | None = None


class STTClient(ABC):
    """Speech-to-text backend."""

    name: str = "base"

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime: str,
        language: str | None = "ko",
    ) -> STTResult:
        """Transcribe an audio blob (full file). Returns the recognized text."""
