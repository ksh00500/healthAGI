from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from app.services.llm.base import ChatChunk, ChatTurn, LLMClient

DEFAULT_REPLY = "[MOCK LLM] 안녕하세요! 실제 LLM이 연결되지 않은 상태로 응답합니다."


class MockLLMClient(LLMClient):
    """Deterministic stand-in used for tests and when Ollama is unavailable.

    Callers can preload `replies` (FIFO) for chat or `json_replies` for structured.
    """

    name = "mock"

    def __init__(
        self,
        replies: list[str] | None = None,
        json_replies: list[dict[str, Any]] | None = None,
    ) -> None:
        self.replies = list(replies or [])
        self.json_replies = list(json_replies or [])
        self.calls: list[list[ChatTurn]] = []

    def queue(self, text: str) -> None:
        self.replies.append(text)

    def queue_json(self, obj: dict[str, Any]) -> None:
        self.json_replies.append(obj)

    async def chat_stream(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[ChatChunk]:
        self.calls.append(messages)
        reply = self.replies.pop(0) if self.replies else DEFAULT_REPLY
        # Yield small chunks so streaming behavior is exercised.
        chunk = ""
        for ch in reply:
            chunk += ch
            if len(chunk) >= 8 or ch in "。.!?\n ":
                yield ChatChunk(kind="token", text=chunk)
                chunk = ""
                await asyncio.sleep(0)
        if chunk:
            yield ChatChunk(kind="token", text=chunk)
        yield ChatChunk(
            kind="done",
            eval_count=len(reply),
            prompt_eval_count=sum(len(m.content) for m in messages),
        )

    async def complete_json(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        self.calls.append(messages)
        if self.json_replies:
            return self.json_replies.pop(0)
        # Default: echo back a tiny structure useful for unit tests.
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        return {"echo": last_user.content if last_user else ""}


_singleton: MockLLMClient | None = None


def get_mock_client() -> MockLLMClient:
    """Process-wide instance so tests can prime replies before issuing a request."""
    global _singleton
    if _singleton is None:
        _singleton = MockLLMClient()
    return _singleton


def reset_mock_client() -> None:
    global _singleton
    _singleton = MockLLMClient()
