from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, SessionDep
from app.models.exercise import Exercise, ExerciseAlias
from app.schemas.workout import ExerciseCreate, ExerciseRead

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("", response_model=list[ExerciseRead])
async def list_exercises(
    _user: CurrentUser,
    session: SessionDep,
    q: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Exercise]:
    stmt = select(Exercise).options(selectinload(Exercise.aliases))
    if q:
        like = f"%{q.lower()}%"
        stmt = (
            stmt.join(ExerciseAlias, isouter=True)
            .where(
                or_(
                    Exercise.canonical_name.ilike(like),
                    Exercise.display_name_ko.ilike(like),
                    Exercise.display_name_en.ilike(like),
                    ExerciseAlias.alias.ilike(like),
                )
            )
            .distinct()
        )
    stmt = stmt.order_by(Exercise.canonical_name).limit(limit)
    rows = await session.scalars(stmt)
    return list(rows.unique())


@router.post("", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
async def create_exercise(
    payload: ExerciseCreate, _user: CurrentUser, session: SessionDep
) -> Exercise:
    existing = await session.scalar(
        select(Exercise).where(Exercise.canonical_name == payload.canonical_name)
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "exercise already exists")
    ex = Exercise(
        canonical_name=payload.canonical_name,
        display_name_ko=payload.display_name_ko,
        display_name_en=payload.display_name_en,
        primary_muscle_group_id=payload.primary_muscle_group_id,
        secondary_muscle_group_ids=payload.secondary_muscle_group_ids,
        equipment=payload.equipment,
        is_compound=payload.is_compound,
    )
    for alias in payload.aliases:
        ex.aliases.append(ExerciseAlias(alias=alias))
    session.add(ex)
    await session.commit()
    # Refresh with aliases loaded.
    await session.refresh(ex, attribute_names=["aliases"])
    return ex
