from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class TTSResult:
    audio_bytes: bytes
    mime: str
    sample_rate: int


@dataclass
class TTSChunk:
    """One sentence-sized audio chunk in a streaming synthesis."""

    seq: int
    audio_bytes: bytes
    mime: str
    sample_rate: int
    text: str  # the sentence this chunk encodes


class TTSClient(ABC):
    """Text-to-speech backend."""

    name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, language: str = "ko") -> TTSResult: ...

    async def synthesize_stream(
        self, text: str, language: str = "ko"
    ) -> AsyncIterator[TTSChunk]:
        """Stream sentence-sized chunks. Default impl splits and synthesizes per sentence.

        Concrete clients can override for true streaming synthesis.
        """
        sentences = split_sentences(text)
        for i, sentence in enumerate(sentences):
            res = await self.synthesize(sentence, language=language)
            yield TTSChunk(
                seq=i,
                audio_bytes=res.audio_bytes,
                mime=res.mime,
                sample_rate=res.sample_rate,
                text=sentence,
            )


_SENTENCE_TERMINATORS = ".?!。？！\n"


def split_sentences(text: str) -> list[str]:
    """Lightweight sentence splitter — keeps CJK punctuation, never returns empty."""
    out: list[str] = []
    buf: list[str] = []
    for ch in text:
        buf.append(ch)
        if ch in _SENTENCE_TERMINATORS:
            sentence = "".join(buf).strip()
            if sentence:
                out.append(sentence)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out or [text.strip() or " "]

