from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, SessionDep
from app.models.exercise import Exercise
from app.models.muscle_group import MuscleGroup
from app.models.recovery_timer import RecoveryTimer
from app.models.workout import WorkoutSession, WorkoutSet
from app.schemas.recommendation import SuggestedTimer, SuggestRequest, SuggestResponse
from app.schemas.timer import TimerCreate, TimerRead, TimerUpdate
from app.services.recommendations import suggest_recovery_for_session

router = APIRouter(prefix="/timers", tags=["timers"])


async def _ensure_muscle_group(session: AsyncSession, muscle_group_id: str) -> MuscleGroup:
    mg = await session.get(MuscleGroup, muscle_group_id)
    if not mg:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"unknown muscle group: {muscle_group_id}"
        )
    return mg


@router.get("", response_model=list[TimerRead])
async def list_timers(
    user: CurrentUser,
    session: SessionDep,
    since: datetime | None = Query(default=None),
    include_deleted: bool = Query(default=False),
) -> list[RecoveryTimer]:
    stmt = select(RecoveryTimer).where(RecoveryTimer.user_id == user.id)
    if since is not None:
        stmt = stmt.where(RecoveryTimer.updated_at > since)
    if not include_deleted:
        stmt = stmt.where(RecoveryTimer.deleted_at.is_(None))
    stmt = stmt.order_by(RecoveryTimer.start_time.desc())
    rows = await session.scalars(stmt)
    return list(rows)


@router.get("/current", response_model=list[TimerRead])
async def list_current_timers(
    user: CurrentUser, session: SessionDep
) -> list[RecoveryTimer]:
    """One latest active timer per muscle group for this user."""
    stmt = (
        select(RecoveryTimer)
        .where(
            RecoveryTimer.user_id == user.id,
            RecoveryTimer.deleted_at.is_(None),
        )
        .order_by(
            RecoveryTimer.muscle_group_id,
            RecoveryTimer.start_time.desc(),
        )
    )
    rows = await session.scalars(stmt)
    latest: dict[str, RecoveryTimer] = {}
    for t in rows:
        latest.setdefault(t.muscle_group_id, t)
    return list(latest.values())


@router.post("", response_model=TimerRead, status_code=status.HTTP_201_CREATED)
async def create_timer(
    payload: TimerCreate, user: CurrentUser, session: SessionDep
) -> RecoveryTimer:
    if payload.client_op_id is not None:
        existing = await session.scalar(
            select(RecoveryTimer).where(RecoveryTimer.client_op_id == payload.client_op_id)
        )
        if existing:
            return existing  # idempotent retry

    mg = await _ensure_muscle_group(session, payload.muscle_group_id)
    duration = payload.duration_minutes or mg.default_recovery_hours * 60
    start = payload.start_time or datetime.now(UTC)

    timer = RecoveryTimer(
        user_id=user.id,
        muscle_group_id=mg.id,
        start_time=start,
        duration_minutes=duration,
        intensity_score=payload.intensity_score,
        source=payload.source,
        notes=payload.notes,
        client_op_id=payload.client_op_id,
    )
    session.add(timer)
    await session.commit()
    await session.refresh(timer)
    return timer


@router.patch("/{timer_id}", response_model=TimerRead)
async def update_timer(
    timer_id: UUID,
    payload: TimerUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> RecoveryTimer:
    timer = await session.scalar(
        select(RecoveryTimer).where(
            RecoveryTimer.id == timer_id,
            RecoveryTimer.user_id == user.id,
            RecoveryTimer.deleted_at.is_(None),
        )
    )
    if not timer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "timer not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(timer, field, value)
    await session.commit()
    await session.refresh(timer)
    return timer


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_recovery(
    payload: SuggestRequest, user: CurrentUser, session: SessionDep
) -> SuggestResponse:
    """Ask the LLM for per-muscle recovery durations after a workout.

    Provide either an existing `session_id` (recommended right after saving
    a session) or a transient `sets` list.
    """
    if payload.session_id:
        ws = await session.scalar(
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.sets).selectinload(WorkoutSet.exercise)
            )
            .where(
                WorkoutSession.id == payload.session_id,
                WorkoutSession.user_id == user.id,
                WorkoutSession.deleted_at.is_(None),
            )
        )
        if ws is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    elif payload.sets:
        # Build a transient (un-persisted) session with hydrated exercises.
        ws = WorkoutSession(user_id=user.id, started_at=datetime.now(UTC))
        ex_rows = await session.scalars(
            select(Exercise).where(Exercise.id.in_([s.exercise_id for s in payload.sets]))
        )
        ex_by_id = {ex.id: ex for ex in ex_rows}
        for s in payload.sets:
            if s.exercise_id not in ex_by_id:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"unknown exercise id: {s.exercise_id}",
                )
            ws.sets.append(
                WorkoutSet(
                    exercise_id=s.exercise_id,
                    set_index=s.set_index,
                    reps=s.reps,
                    weight_kg=s.weight_kg,
                    rpe=s.rpe,
                    is_warmup=s.is_warmup,
                )
            )
            ws.sets[-1].exercise = ex_by_id[s.exercise_id]
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "provide session_id or sets"
        )

    try:
        out = await suggest_recovery_for_session(session, user, ws)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"LLM suggestion failed: {e}"
        ) from e
    return SuggestResponse(
        suggestions=[SuggestedTimer(**s) for s in out]
    )


@router.delete("/{timer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timer(
    timer_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    timer = await session.scalar(
        select(RecoveryTimer).where(
            RecoveryTimer.id == timer_id,
            RecoveryTimer.user_id == user.id,
            RecoveryTimer.deleted_at.is_(None),
        )
    )
    if not timer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "timer not found")
    timer.deleted_at = datetime.now(UTC)
    await session.commit()
