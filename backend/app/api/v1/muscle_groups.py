from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.deps import SessionDep
from app.models.muscle_group import MuscleGroup
from app.schemas.timer import MuscleGroupRead

router = APIRouter(prefix="/muscle-groups", tags=["muscle-groups"])


@router.get("", response_model=list[MuscleGroupRead])
async def list_muscle_groups(session: SessionDep) -> list[MuscleGroup]:
    rows = await session.scalars(select(MuscleGroup).order_by(MuscleGroup.sort_order))
    return list(rows)
