from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.config import get_settings
from app.services.llm.base import ChatChunk, ChatTurn, LLMClient, parse_json_lenient

logger = logging.getLogger(__name__)


def _to_contents(messages: list[ChatTurn]) -> tuple[str | None, list[Any]]:
    """Split ChatTurns into (system_instruction, contents) for Gemini."""
    from google.genai import types  # lazy

    system_parts: list[str] = []
    contents: list[types.Content] = []
    for m in messages:
        if m.role == "system":
            if m.content:
                system_parts.append(m.content)
            continue
        # Gemini uses 'user' / 'model' (not 'assistant').
        role = "user" if m.role == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=m.content)])
        )
    system = "\n\n".join(system_parts) if system_parts else None
    return system, contents


def _safety_settings() -> list[Any]:
    """Permissive safety for our personal health app — eating/exercise/weight
    discussions are routinely (and incorrectly) flagged as 'dangerous content'
    by default settings."""
    from google.genai import types

    cats = (
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_HARASSMENT",
    )
    return [
        types.SafetySetting(category=c, threshold="BLOCK_ONLY_HIGH") for c in cats
    ]


class GeminiClient(LLMClient):
    """Google Gemini backed implementation of LLMClient.

    Uses the unified `google-genai` SDK (Gemini Developer API + Vertex AI).
    """

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
    ) -> None:
        s = get_settings()
        key = api_key or s.effective_gemini_key
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) not set. "
                "Set HEALTHAGI_LLM_BACKEND=ollama to keep using the local model."
            )
        try:
            from google import genai  # lazy
        except ImportError as e:
            raise RuntimeError(
                "google-genai not installed. `pip install google-genai`"
            ) from e
        self._client = genai.Client(api_key=key)
        self.default_model = default_model or s.effective_chat_model

    def _config(
        self,
        system: str | None,
        temperature: float,
        json_mode: bool = False,
    ) -> Any:
        from google.genai import types

        return types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if json_mode else None,
            safety_settings=_safety_settings(),
        )

    async def chat_stream(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
    ) -> AsyncIterator[ChatChunk]:
        system, contents = _to_contents(messages)
        cfg = self._config(system, temperature, json_mode=False)
        target_model = model or self.default_model

        prompt_tokens: int | None = None
        output_tokens: int | None = None
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=target_model,
                contents=contents,
                config=cfg,
            )
            async for chunk in stream:
                text = getattr(chunk, "text", None) or ""
                if text:
                    yield ChatChunk(kind="token", text=text)
                usage = getattr(chunk, "usage_metadata", None)
                if usage is not None:
                    prompt_tokens = getattr(usage, "prompt_token_count", None) or prompt_tokens
                    output_tokens = (
                        getattr(usage, "candidates_token_count", None) or output_tokens
                    )
        except Exception as e:  # noqa: BLE001
            yield ChatChunk(kind="error", error=f"gemini: {e}")
            return
        yield ChatChunk(
            kind="done",
            eval_count=output_tokens,
            prompt_eval_count=prompt_tokens,
        )

    async def complete_json(
        self,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        system, contents = _to_contents(messages)
        cfg = self._config(system, temperature, json_mode=True)
        res = await self._client.aio.models.generate_content(
            model=model or self.default_model,
            contents=contents,
            config=cfg,
        )
        return parse_json_lenient(res.text or "")

    async def complete_vision_json(
        self,
        system_prompt: str,
        user_prompt: str,
        image_bytes: bytes,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        from google.genai import types

        s = get_settings()
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    types.Part.from_text(text=user_prompt),
                ],
            )
        ]
        cfg = self._config(system_prompt, temperature, json_mode=True)
        res = await self._client.aio.models.generate_content(
            model=model or s.llm_vision_model,
            contents=contents,
            config=cfg,
        )
        return parse_json_lenient(res.text or "")

    async def complete_audio_json(
        self,
        system_prompt: str,
        user_prompt: str,
        audio_bytes: bytes,
        audio_mime: str = "audio/m4a",
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        from google.genai import types

        s = get_settings()
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime),
                    types.Part.from_text(text=user_prompt),
                ],
            )
        ]
        cfg = self._config(system_prompt, temperature, json_mode=True)
        res = await self._client.aio.models.generate_content(
            model=model or s.llm_parse_model,
            contents=contents,
            config=cfg,
        )
        return parse_json_lenient(res.text or "")
