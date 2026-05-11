from __future__ import annotations

from app.services.stt.base import STTClient, STTResult


class MockSTTClient(STTClient):
    """Returns canned transcripts. Useful for tests / when Whisper is absent."""

    name = "mock"

    def __init__(self, default: str = "안녕하세요. 오늘 운동 추천해줘.") -> None:
        self.default = default
        self.queue: list[str] = []
        self.calls: list[tuple[bytes, str, str | None]] = []

    def push(self, text: str) -> None:
        self.queue.append(text)

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime: str,
        language: str | None = "ko",
    ) -> STTResult:
        self.calls.append((audio_bytes, mime, language))
        text = self.queue.pop(0) if self.queue else self.default
        return STTResult(text=text, language=language, duration_s=1.0)


_singleton: MockSTTClient | None = None


def get_mock_stt() -> MockSTTClient:
    global _singleton
    if _singleton is None:
        _singleton = MockSTTClient()
    return _singleton


def reset_mock_stt() -> None:
    global _singleton
    _singleton = MockSTTClient()
