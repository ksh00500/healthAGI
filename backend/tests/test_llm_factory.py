from __future__ import annotations

import importlib
import os
from contextlib import contextmanager

import pytest

import app.services.llm.factory as factory_mod
from app.services.llm import factory, reset_llm_singleton
from app.services.llm.mock_client import MockLLMClient
from app.services.llm.ollama_client import OllamaClient


@contextmanager
def env(**overrides: str | None):
    """Patch env vars + clear settings + factory caches around the block."""
    sentinel = object()
    previous: dict[str, object] = {}
    for k, v in overrides.items():
        previous[k] = os.environ.get(k, sentinel)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    # Drop cached Settings + factory singleton.
    from app.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    reset_llm_singleton()
    try:
        yield
    finally:
        for k, v in previous.items():
            if v is sentinel:
                os.environ.pop(k, None)
            else:
                assert isinstance(v, str)
                os.environ[k] = v
        get_settings.cache_clear()  # type: ignore[attr-defined]
        reset_llm_singleton()


def test_factory_mock_when_backend_mock() -> None:
    with env(HEALTHAGI_LLM_BACKEND="mock"):
        assert isinstance(factory.get_llm_client(), MockLLMClient)


def test_factory_gemini_when_key_present() -> None:
    with env(HEALTHAGI_LLM_BACKEND=None, GEMINI_API_KEY="fake-key-for-test"):
        from app.services.llm.gemini_client import GeminiClient

        client = factory.get_llm_client()
        assert isinstance(client, GeminiClient)
        assert client.default_model.startswith("gemini")


def test_factory_explicit_ollama() -> None:
    with env(HEALTHAGI_LLM_BACKEND="ollama", GEMINI_API_KEY=None):
        assert isinstance(factory.get_llm_client(), OllamaClient)


def test_factory_falls_back_to_ollama_without_key() -> None:
    with env(HEALTHAGI_LLM_BACKEND=None, GEMINI_API_KEY=None, GOOGLE_API_KEY=None):
        assert isinstance(factory.get_llm_client(), OllamaClient)


def test_factory_unknown_backend_raises() -> None:
    with env(HEALTHAGI_LLM_BACKEND="banana"):
        with pytest.raises(RuntimeError):
            factory.get_llm_client()


def test_gemini_client_requires_key() -> None:
    with env(GEMINI_API_KEY=None, GOOGLE_API_KEY=None):
        from app.services.llm.gemini_client import GeminiClient

        with pytest.raises(RuntimeError) as exc:
            GeminiClient()
        assert "GEMINI_API_KEY" in str(exc.value)


def test_reset_llm_singleton_clears_cache() -> None:
    with env(HEALTHAGI_LLM_BACKEND="ollama", GEMINI_API_KEY=None):
        first = factory.get_llm_client()
        assert factory.get_llm_client() is first
        reset_llm_singleton()
        second = factory.get_llm_client()
        assert second is not first


# Ensure imports always reflect the current module state (no stale references
# from earlier tests in the same session).
def teardown_module(_module: object) -> None:
    importlib.reload(factory_mod)
