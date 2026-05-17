from app.services.llm.base import ChatChunk, ChatTurn, LLMClient
from app.services.llm.factory import get_llm_client

__all__ = ["ChatChunk", "ChatTurn", "LLMClient", "get_llm_client"]


def reset_llm_singleton() -> None:
    """Test helper — drop the cached backend so a new one is built next call."""
    from app.services.llm import factory

    factory._singleton = None
