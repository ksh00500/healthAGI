from __future__ import annotations

from app.services.vad.base import VADClient, VADResult


class MockVAD(VADClient):
    """Treats any non-trivial buffer as speech; useful for tests."""

    name = "mock"

    def __init__(self) -> None:
        self.queue: list[VADResult] = []
        self.calls: list[tuple[int, int]] = []  # (bytes, sample_rate)

    def push(self, result: VADResult) -> None:
        self.queue.append(result)

    async def check(self, pcm16_mono: bytes, sample_rate: int = 16000) -> VADResult:
        self.calls.append((len(pcm16_mono), sample_rate))
        if self.queue:
            return self.queue.pop(0)
        samples = max(1, len(pcm16_mono) // 2)
        duration_ms = int(samples / sample_rate * 1000)
        return VADResult(has_speech=duration_ms > 100, speech_ms=duration_ms, silence_tail_ms=0)


_singleton: MockVAD | None = None


def get_mock_vad() -> MockVAD:
    global _singleton
    if _singleton is None:
        _singleton = MockVAD()
    return _singleton


def reset_mock_vad() -> None:
    global _singleton
    _singleton = MockVAD()
