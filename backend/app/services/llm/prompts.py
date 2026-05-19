from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.body_metric import BodyMetric
from app.models.meal import Meal
from app.models.muscle_group import MuscleGroup
from app.models.profile import Profile
from app.models.recovery_timer import RecoveryTimer
from app.models.user import User
from app.models.workout import WorkoutSession
from app.services.llm.base import ChatTurn

PERSONA = (
    "당신은 'healthAGI', 사용자 개인 헬스 코치입니다. "
    "한국어로 답하고, 간결하게 답변합니다. 측정 단위는 미터법(kg, cm)을 사용합니다. "
    "운동/회복/영양 조언은 사용자의 실제 데이터에 근거해서 합니다. "
    "데이터가 부족할 때는 '아직 데이터가 부족해 일반 가이드 기반으로 답합니다'라고 명시합니다."
)


def _decimal(v: Decimal | None) -> str:
    return "?" if v is None else f"{float(v):g}"


def as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; coerce to UTC so arithmetic with now() works."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# Keep the private alias for legacy imports.
_as_utc = as_utc


async def build_system_prompt(session: AsyncSession, user: User) -> str:
    """Compose the per-request system prompt from the user's state.

    Layered: persona + profile + recovery state + recent workouts + nutrition snapshot.
    """
    parts: list[str] = [PERSONA]

    # Profile
    profile = await session.scalar(select(Profile).where(Profile.user_id == user.id))
    parts.append(await _profile_section(session, user, profile))

    # Recovery state
    parts.append(await _recovery_section(session, user))

    # Recent workouts
    parts.append(await _workout_section(session, user))

    # Nutrition snapshot
    parts.append(await _meal_section(session, user))

    parts.append(
        "응답 규칙: 1) 사용자의 회복 상태를 반드시 고려해 추천하라. "
        "2) 수치가 없는 부분은 추측하지 말고 사용자에게 묻거나 데이터가 없다고 답하라. "
        "3) 답변은 보통 5문장 이내로 짧게."
    )
    return "\n\n".join(parts)


async def _profile_section(session: AsyncSession, user: User, profile: Profile | None) -> str:
    latest_metric = await session.scalar(
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id, BodyMetric.deleted_at.is_(None))
        .order_by(BodyMetric.measured_at.desc())
        .limit(1)
    )
    week_ago = datetime.now(UTC) - timedelta(days=7)
    older = await session.scalar(
        select(BodyMetric)
        .where(
            BodyMetric.user_id == user.id,
            BodyMetric.deleted_at.is_(None),
            BodyMetric.measured_at <= week_ago,
        )
        .order_by(BodyMetric.measured_at.desc())
        .limit(1)
    )
    trend = ""
    if latest_metric and older and latest_metric.weight_kg and older.weight_kg:
        delta = float(latest_metric.weight_kg) - float(older.weight_kg)
        trend = f" (7일 추이 {delta:+.1f}kg)"

    height = _decimal(profile.height_cm) if profile else "?"
    weight = _decimal(latest_metric.weight_kg) if latest_metric else "?"
    sex = profile.sex if profile and profile.sex else "?"
    goals = profile.goals if profile and profile.goals else "(목표 미설정)"

    return (
        "[프로필]\n"
        f"- 성별: {sex}, 키: {height}cm, 현재 체중: {weight}kg{trend}\n"
        f"- 목표: {goals}\n"
        f"- 이메일: {user.email}"
    )


async def _recovery_section(session: AsyncSession, user: User) -> str:
    groups = await session.scalars(select(MuscleGroup).order_by(MuscleGroup.sort_order))
    groups_list = list(groups)
    timers = await session.scalars(
        select(RecoveryTimer)
        .where(RecoveryTimer.user_id == user.id, RecoveryTimer.deleted_at.is_(None))
        .order_by(RecoveryTimer.start_time.desc())
    )
    latest: dict[str, RecoveryTimer] = {}
    for timer in timers:
        latest.setdefault(timer.muscle_group_id, timer)

    now = datetime.now(UTC)
    lines: list[str] = ["[회복 상태]"]
    for g in groups_list:
        t = latest.get(g.id)
        if t is None:
            lines.append(f"- {g.display_name_ko}: 준비됨 (기본 {g.default_recovery_hours}h)")
            continue
        end = _as_utc(t.start_time) + timedelta(minutes=t.duration_minutes)
        remaining = end - now
        if remaining.total_seconds() <= 0:
            lines.append(f"- {g.display_name_ko}: 준비됨")
        else:
            hrs = remaining.total_seconds() / 3600
            lines.append(f"- {g.display_name_ko}: 회복 중 ({hrs:.1f}h 남음)")
    return "\n".join(lines)


async def _workout_section(session: AsyncSession, user: User) -> str:
    week_ago = datetime.now(UTC) - timedelta(days=7)
    stmt = (
        select(WorkoutSession)
        .options(selectinload(WorkoutSession.sets))
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.deleted_at.is_(None),
            WorkoutSession.started_at >= week_ago,
        )
        .order_by(WorkoutSession.started_at.desc())
        .limit(7)
    )
    sessions = list((await session.scalars(stmt)).unique())
    if not sessions:
        return "[최근 7일 운동]\n- 기록 없음"
    lines = ["[최근 7일 운동]"]
    for s in sessions:
        date = s.started_at.strftime("%m-%d")
        non_warmup = [st for st in s.sets if not st.is_warmup]
        volume = sum(((st.reps or 0) * float(st.weight_kg or 0)) for st in non_warmup)
        lines.append(f"- {date}: {len(non_warmup)}세트, 볼륨 {volume:.0f}kg")
    return "\n".join(lines)


async def _meal_section(session: AsyncSession, user: User) -> str:
    three_days_ago = datetime.now(UTC) - timedelta(days=3)
    stmt = (
        select(Meal)
        .where(
            Meal.user_id == user.id,
            Meal.deleted_at.is_(None),
            Meal.eaten_at >= three_days_ago,
        )
        .order_by(Meal.eaten_at.desc())
    )
    meals = list(await session.scalars(stmt))
    if not meals:
        return "[최근 3일 식단]\n- 기록 없음"

    def s(attr: str) -> float:
        return sum(float(getattr(m, attr) or 0) for m in meals)

    days = max(1, len({m.eaten_at.date() for m in meals}))
    kcal = s("total_kcal") / days
    protein = s("total_protein_g") / days
    carbs = s("total_carbs_g") / days
    fat = s("total_fat_g") / days
    return (
        "[최근 3일 식단 (일평균)]\n"
        f"- 칼로리: {kcal:.0f} kcal, 단백질: {protein:.0f}g, 탄수: {carbs:.0f}g, 지방: {fat:.0f}g\n"
        f"- 기록된 식사 수: {len(meals)}"
    )


def turns_from_history(messages: list[dict[str, Any]]) -> list[ChatTurn]:
    """Convert stored chat messages to ChatTurn objects, skipping tool noise."""
    turns: list[ChatTurn] = []
    for m in messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        content = m.get("content")
        if not content:
            continue
        turns.append(ChatTurn(role=role, content=content))
    return turns
