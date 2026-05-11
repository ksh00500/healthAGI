from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, SessionDep
from app.models.exercise import Exercise
from app.models.workout import WorkoutSession, WorkoutSet
from app.schemas.workout import (
    WorkoutSessionCreate,
    WorkoutSessionRead,
    WorkoutSessionUpdate,
    WorkoutSetInput,
)

router = APIRouter(prefix="/workouts", tags=["workouts"])


async def _verify_exercises(session, set_inputs: list[WorkoutSetInput]) -> None:
    ids = {s.exercise_id for s in set_inputs}
    if not ids:
        return
    rows = await session.scalars(select(Exercise.id).where(Exercise.id.in_(ids)))
    found = set(rows)
    missing = ids - found
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"unknown exercise ids: {sorted(str(m) for m in missing)}",
        )


def _load_session_stmt(user_id: UUID, session_id: UUID | None = None):
    stmt = (
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.deleted_at.is_(None),
        )
    )
    if session_id is not None:
        stmt = stmt.where(WorkoutSession.id == session_id)
    return stmt


@router.get("/sessions", response_model=list[WorkoutSessionRead])
async def list_sessions(
    user: CurrentUser,
    session: SessionDep,
    since: datetime | None = Query(default=None),
    day: date | None = Query(default=None, description="filter to a single calendar day (UTC)"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WorkoutSession]:
    stmt = _load_session_stmt(user.id)
    if since is not None:
        stmt = stmt.where(WorkoutSession.updated_at > since)
    if day is not None:
        start = datetime.combine(day, time.min, tzinfo=timezone.utc)
        end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        stmt = stmt.where(WorkoutSession.started_at >= start, WorkoutSession.started_at <= end)
    stmt = stmt.order_by(WorkoutSession.started_at.desc()).limit(limit)
    rows = await session.scalars(stmt)
    return list(rows.unique())


@router.get("/sessions/{session_id}", response_model=WorkoutSessionRead)
async def get_session(
    session_id: UUID, user: CurrentUser, session: SessionDep
) -> WorkoutSession:
    ws = await session.scalar(_load_session_stmt(user.id, session_id))
    if not ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    return ws


@router.post(
    "/sessions", response_model=WorkoutSessionRead, status_code=status.HTTP_201_CREATED
)
async def create_session(
    payload: WorkoutSessionCreate, user: CurrentUser, session: SessionDep
) -> WorkoutSession:
    await _verify_exercises(session, payload.sets)
    ws = WorkoutSession(
        user_id=user.id,
        started_at=payload.started_at or datetime.now(timezone.utc),
        ended_at=payload.ended_at,
        notes=payload.notes,
        raw_input=payload.raw_input,
    )
    for s in payload.sets:
        ws.sets.append(
            WorkoutSet(
                exercise_id=s.exercise_id,
                set_index=s.set_index,
                reps=s.reps,
                weight_kg=s.weight_kg,
                rpe=s.rpe,
                is_warmup=s.is_warmup,
                notes=s.notes,
            )
        )
    session.add(ws)
    await session.commit()
    return await session.scalar(_load_session_stmt(user.id, ws.id))


@router.patch("/sessions/{session_id}", response_model=WorkoutSessionRead)
async def update_session(
    session_id: UUID,
    payload: WorkoutSessionUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> WorkoutSession:
    ws = await session.scalar(_load_session_stmt(user.id, session_id))
    if not ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")

    data = payload.model_dump(exclude_unset=True)
    if "sets" in data and data["sets"] is not None:
        await _verify_exercises(session, payload.sets or [])
        ws.sets.clear()
        for s in payload.sets or []:
            ws.sets.append(
                WorkoutSet(
                    exercise_id=s.exercise_id,
                    set_index=s.set_index,
                    reps=s.reps,
                    weight_kg=s.weight_kg,
                    rpe=s.rpe,
                    is_warmup=s.is_warmup,
                    notes=s.notes,
                )
            )

    for field in ("started_at", "ended_at", "notes", "raw_input"):
        if field in data:
            setattr(ws, field, data[field])

    await session.commit()
    return await session.scalar(_load_session_stmt(user.id, session_id))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    ws = await session.scalar(_load_session_stmt(user.id, session_id))
    if not ws:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    ws.deleted_at = datetime.now(timezone.utc)
    await session.commit()
