from __future__ import annotations

import os

from app.config import get_settings
from app.services.llm.base import LLMClient
from app.services.llm.mock_client import get_mock_client
from app.services.llm.ollama_client import OllamaClient


def get_llm_client() -> LLMClient:
    """Returns the configured LLM backend.

    Set HEALTHAGI_LLM_BACKEND=mock to force the mock client (used by tests).
    Otherwise, the Ollama client is returned with settings-based config.
    """
    backend = os.getenv("HEALTHAGI_LLM_BACKEND")
    if backend == "mock":
        return get_mock_client()
    settings = get_settings()
    return OllamaClient(base_url=settings.ollama_base_url, default_model=settings.llm_text_model)
