from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    assert _session_factory is not None
    return _engine, _session_factory


def get_engine() -> AsyncEngine:
    engine, _ = _ensure_engine()
    return engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _, factory = _ensure_engine()
    async with factory() as session:
        yield session
