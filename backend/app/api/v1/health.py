from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import text

from app.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", status_code=status.HTTP_200_OK)
async def readyz(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "db": "ok"}
