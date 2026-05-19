from __future__ import annotations

import logging
import os

from app.config import get_settings
from app.services.llm.base import LLMClient
from app.services.llm.mock_client import get_mock_client
from app.services.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_singleton: LLMClient | None = None


def _build_client() -> LLMClient:
    """Pick an LLM backend.

    Selection order:
      1. HEALTHAGI_LLM_BACKEND env var (mock | gemini | ollama) — explicit wins.
      2. If GEMINI_API_KEY / GOOGLE_API_KEY is set, default to Gemini.
      3. Otherwise fall back to local Ollama.
    """
    backend = os.getenv("HEALTHAGI_LLM_BACKEND")
    settings = get_settings()

    if backend == "mock":
        return get_mock_client()
    if backend == "gemini" or (backend is None and settings.effective_gemini_key):
        from app.services.llm.gemini_client import GeminiClient

        logger.info(
            "LLM backend: gemini (chat=%s voice=%s parse=%s rec=%s vision=%s)",
            settings.effective_chat_model,
            settings.llm_voice_model,
            settings.llm_parse_model,
            settings.llm_recommendation_model,
            settings.llm_vision_model,
        )
        return GeminiClient(default_model=settings.effective_chat_model)
    if backend == "ollama" or backend is None:
        logger.info("LLM backend: ollama (model=%s)", settings.effective_chat_model)
        return OllamaClient(
            base_url=settings.ollama_base_url,
            default_model=settings.effective_chat_model,
        )
    raise RuntimeError(f"unknown HEALTHAGI_LLM_BACKEND: {backend!r}")


def get_llm_client() -> LLMClient:
    """Process-singleton accessor.

    The mock backend is intentionally NOT cached — tests reset it between
    runs via reset_mock_client().
    """
    global _singleton
    backend = os.getenv("HEALTHAGI_LLM_BACKEND")
    if backend == "mock":
        return get_mock_client()
    if _singleton is None:
        _singleton = _build_client()
    return _singleton
