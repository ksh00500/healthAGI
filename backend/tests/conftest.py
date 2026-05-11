from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Use SQLite in-memory for tests (model is portable enough for our types).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["HEALTHAGI_LLM_BACKEND"] = "mock"

from app.core.db import Base, get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.exercise import SEED_EXERCISES, Exercise, ExerciseAlias  # noqa: E402
from app.models.muscle_group import SEED_MUSCLE_GROUPS, MuscleGroup  # noqa: E402
from app.services.llm.mock_client import reset_mock_client  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> Any:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker]:
    reset_mock_client()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    # Seed muscle groups + canonical exercises.
    async with factory() as s:
        for mg in SEED_MUSCLE_GROUPS:
            s.add(
                MuscleGroup(
                    id=mg["id"],
                    display_name_ko=mg["ko"],
                    display_name_en=mg["en"],
                    default_recovery_hours=mg["hours"],
                    sort_order=mg["order"],
                )
            )
        for e in SEED_EXERCISES:
            ex = Exercise(
                canonical_name=e["c"],
                display_name_ko=e["ko"],
                display_name_en=e["en"],
                primary_muscle_group_id=e["p"],
                secondary_muscle_group_ids=e["s"],
                equipment=e["eq"],
                is_compound=e["co"],
            )
            for a in e["aliases"]:
                ex.aliases.append(ExerciseAlias(alias=a))
            s.add(ex)
        await s.commit()
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_get_session() -> AsyncIterator[Any]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
