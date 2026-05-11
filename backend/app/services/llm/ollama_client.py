from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import get_settings
from app.services.llm.base import ChatChunk, ChatTurn, LLMClient, parse_json_lenient


class OllamaClient(LLMClient):
    """Talks to a local Ollama instance via its HTTP API.

    Reference: https://github.com/ollama/ollama/blob/main/docs/api.md
    """

    name = "ollama"

    def __init__(self, base_url: str | None = None, default_model: str | None = None) -> None:
        s = get_settings()
        self.base_url = (base_url or s.ollama_base_url).rstrip("/")
        self.default_model = default_model or s.llm_text_model

    async def chat_stream(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[ChatChunk]:
        payload = {
            "model": model or self.default_model,
            "messages": [m.to_openai() for m in messages],
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    yield ChatChunk(
                        kind="error",
                        error=f"ollama {response.status_code}: {body.decode(errors='ignore')[:200]}",
                    )
                    return
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = data.get("message") or {}
                    token = message.get("content") or ""
                    if token:
                        yield ChatChunk(kind="token", text=token)
                    if data.get("done"):
                        yield ChatChunk(
                            kind="done",
                            eval_count=data.get("eval_count"),
                            prompt_eval_count=data.get("prompt_eval_count"),
                        )
                        return

    async def complete_json(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        payload = {
            "model": model or self.default_model,
            "messages": [m.to_openai() for m in messages],
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            content = (data.get("message") or {}).get("content") or ""
            return parse_json_lenient(content)
