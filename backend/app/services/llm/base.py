from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ChatTurn:
    role: Role
    content: str
    name: str | None = None  # for tool messages

    def to_openai(self) -> dict[str, Any]:
        d: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ChatChunk:
    """One streaming event from the LLM."""

    kind: Literal["token", "done", "error"]
    text: str = ""
    eval_count: int | None = None
    prompt_eval_count: int | None = None
    error: str | None = None


class LLMClient(ABC):
    """Pluggable backend for chat/streaming/structured calls."""

    name: str = "base"

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[ChatChunk]:
        """Stream assistant tokens. Yields token chunks then a final `done`."""
        if False:  # pragma: no cover - type marker
            yield ChatChunk(kind="done")

    @abstractmethod
    async def complete_json(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Non-streaming structured JSON output. Implementation must parse to a dict."""

    async def complete_vision_json(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Vision -> structured JSON. Default raises; concrete clients override."""
        raise NotImplementedError


def parse_json_lenient(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response.

    Strips markdown fences, trailing commentary, and tries the largest balanced
    {...} substring on failure.
    """
    s = text.strip()
    if s.startswith("```"):
        # ```json\n...\n```
        s = s.strip("`")
        s = s.removeprefix("json").strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Fallback: substring between first `{` and last `}`.
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(s[start : end + 1])
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM did not return valid JSON: {e}") from e
    raise ValueError("LLM did not return valid JSON")
