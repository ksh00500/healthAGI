from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.meal import Meal
from app.models.muscle_group import MuscleGroup
from app.models.recommendation import DailyRecommendation
from app.models.recovery_timer import RecoveryTimer
from app.models.user import User
from app.models.workout import WorkoutSession
from app.services.llm import get_llm_client
from app.services.llm.base import ChatTurn
from app.services.llm.prompts import as_utc, build_system_prompt

logger = logging.getLogger(__name__)

REC_KINDS = ("workout_split", "nutrition_focus", "recovery_check")

_REC_USER = (
    "오늘 사용자에게 보여줄 추천 카드 3개를 한국어 JSON으로 작성하세요.\n"
    "스키마: {\n"
    '  "workout_split": {\n'
    '    "title": "오늘은 풀 데이 추천",\n'
    '    "body": "1-2문장의 구체적 추천",\n'
    '    "rationale": "왜 이렇게 추천했는지 1-3문장"\n'
    "  },\n"
    '  "nutrition_focus": {\n'
    '    "title": "단백질 보충 필요",\n'
    '    "body": "오늘 추가로 챙길 영양 포인트 1-2문장",\n'
    '    "rationale": "최근 3일 데이터 근거"\n'
    "  },\n"
    '  "recovery_check": {\n'
    '    "title": "어깨 회복 중",\n'
    '    "body": "회복 중인 부위와 권장 행동",\n'
    '    "rationale": "어떤 타이머가 도는지"\n'
    "  }\n"
    "}\n"
    "규칙: 1) 시스템 프롬프트의 회복 상태/최근 운동/식단 데이터에 명시적으로 근거할 것.\n"
    "2) 데이터 부족 시 솔직히 그렇게 적기.\n"
    "3) body는 보통 1-2문장. 과도하게 길게 쓰지 말 것."
)


async def _build_source_context(session: AsyncSession, user: User) -> dict[str, Any]:
    """Snapshot used to ground the recommendations (also stored for audit)."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    three_days_ago = now - timedelta(days=3)

    timers = list(
        await session.scalars(
            select(RecoveryTimer).where(
                RecoveryTimer.user_id == user.id,
                RecoveryTimer.deleted_at.is_(None),
            )
        )
    )
    latest: dict[str, RecoveryTimer] = {}
    for t in sorted(timers, key=lambda x: x.start_time, reverse=True):
        latest.setdefault(t.muscle_group_id, t)

    groups = list(await session.scalars(select(MuscleGroup)))
    recovering: list[dict[str, Any]] = []
    ready: list[str] = []
    for g in groups:
        t = latest.get(g.id)
        if t is None:
            ready.append(g.id)
            continue
        end = as_utc(t.start_time) + timedelta(minutes=t.duration_minutes)
        remaining = (end - now).total_seconds()
        if remaining <= 0:
            ready.append(g.id)
        else:
            recovering.append(
                {"muscle_group_id": g.id, "remaining_hours": round(remaining / 3600, 1)}
            )

    sessions = list(
        (
            await session.scalars(
                select(WorkoutSession)
                .options(selectinload(WorkoutSession.sets))
                .where(
                    WorkoutSession.user_id == user.id,
                    WorkoutSession.deleted_at.is_(None),
                    WorkoutSession.started_at >= week_ago,
                )
                .order_by(WorkoutSession.started_at.desc())
                .limit(10)
            )
        ).unique()
    )
    recent_workouts = [
        {
            "date": s.started_at.strftime("%Y-%m-%d"),
            "sets": len([st for st in s.sets if not st.is_warmup]),
            "volume_kg": round(
                sum(((st.reps or 0) * float(st.weight_kg or 0)) for st in s.sets if not st.is_warmup),
                1,
            ),
        }
        for s in sessions
    ]

    meals = list(
        await session.scalars(
            select(Meal).where(
                Meal.user_id == user.id,
                Meal.deleted_at.is_(None),
                Meal.eaten_at >= three_days_ago,
            )
        )
    )

    def _avg(attr: str) -> float:
        vals = [float(getattr(m, attr) or 0) for m in meals]
        return round(sum(vals) / max(1, len({m.eaten_at.date() for m in meals})), 1) if vals else 0.0

    return {
        "as_of": now.isoformat(),
        "recovering": recovering,
        "ready": ready,
        "recent_workouts": recent_workouts,
        "nutrition_3d_avg": {
            "kcal": _avg("total_kcal"),
            "protein_g": _avg("total_protein_g"),
            "carbs_g": _avg("total_carbs_g"),
            "fat_g": _avg("total_fat_g"),
            "logged_meals": len(meals),
        },
    }


async def generate_recommendations(
    session: AsyncSession,
    user: User,
    for_date: date | None = None,
) -> list[DailyRecommendation]:
    """Build 3 recommendation cards via LLM and upsert them for the user/date."""
    settings = get_settings()
    if for_date is None:
        for_date = datetime.now(timezone.utc).date()

    system_prompt = await build_system_prompt(session, user)
    context = await _build_source_context(session, user)

    llm = get_llm_client()
    data = await llm.complete_json(
        [
            ChatTurn(role="system", content=system_prompt),
            ChatTurn(role="user", content=_REC_USER),
        ],
        model=settings.llm_text_model,
        temperature=0.4,
    )

    written_kinds: list[str] = []
    for kind in REC_KINDS:
        card = data.get(kind) or {}
        title = (card.get("title") or "").strip()
        body = (card.get("body") or "").strip()
        if not title or not body:
            logger.warning("recommendation kind %s missing title/body; skipping", kind)
            continue
        existing = await session.scalar(
            select(DailyRecommendation).where(
                DailyRecommendation.user_id == user.id,
                DailyRecommendation.for_date == for_date,
                DailyRecommendation.kind == kind,
                DailyRecommendation.deleted_at.is_(None),
            )
        )
        if existing is None:
            existing = DailyRecommendation(
                user_id=user.id,
                for_date=for_date,
                kind=kind,
                title=title,
                body=body,
                rationale=(card.get("rationale") or "").strip() or None,
                source_context=context,
                model=settings.llm_text_model,
            )
            session.add(existing)
        else:
            existing.title = title
            existing.body = body
            existing.rationale = (card.get("rationale") or "").strip() or None
            existing.source_context = context
            existing.model = settings.llm_text_model
        written_kinds.append(kind)

    await session.commit()

    # Re-fetch so server_default-populated columns (created_at/updated_at) are
    # materialised — async sessions can't lazy-load them after commit.
    rows = list(
        await session.scalars(
            select(DailyRecommendation)
            .where(
                DailyRecommendation.user_id == user.id,
                DailyRecommendation.for_date == for_date,
                DailyRecommendation.kind.in_(written_kinds),
                DailyRecommendation.deleted_at.is_(None),
            )
            .order_by(DailyRecommendation.kind)
        )
    )
    return rows


_TIMER_SUGGEST_USER = (
    "방금 완료한 운동 세션을 보고, 운동한 각 부위에 대해 다음 회복 타이머의 권장 시간(시간 단위)을 제안합니다.\n"
    "JSON 스키마:\n"
    "{\n"
    '  "suggestions": [\n'
    '    {"muscle_group_id": "chest", "hours": 48.0, "intensity_score": 0.8, "reason": "벤치프레스 4세트, 평균 RPE 8"}\n'
    "  ]\n"
    "}\n"
    "규칙:\n"
    "1) 강도가 높을수록 더 긴 회복 시간. RPE 9+ 또는 고볼륨이면 기본값보다 길게.\n"
    "2) 가벼운 운동(RPE 6 이하, 워밍업만)은 기본값보다 짧게.\n"
    "3) intensity_score는 0~1.\n"
    "4) muscle_group_id는 시스템 프롬프트에 나온 그대로 사용.\n"
    "5) 컨디션/수면 데이터가 있으면 반영."
)


async def suggest_recovery_for_session(
    session: AsyncSession,
    user: User,
    workout_session: WorkoutSession,
) -> list[dict[str, Any]]:
    """Given a freshly-saved WorkoutSession, ask the LLM for per-muscle timers."""
    # Build a compact set summary to put in the user message.
    # Caller is expected to pass a WorkoutSession with sets + sets.exercise eagerly loaded.
    parts: list[str] = ["방금 완료한 운동 세션:"]
    for st in sorted(workout_session.sets, key=lambda s: (str(s.exercise_id), s.set_index)):
        ex = st.exercise
        name = (ex.display_name_ko or ex.canonical_name) if ex else "?"
        primary = ex.primary_muscle_group_id if ex else "?"
        weight = f" {float(st.weight_kg)}kg" if st.weight_kg is not None else ""
        rpe = f" RPE{float(st.rpe)}" if st.rpe is not None else ""
        warm = " (워밍업)" if st.is_warmup else ""
        parts.append(
            f"- {name} [{primary}]: {st.reps or 0}회{weight}{rpe}{warm}"
        )

    system_prompt = await build_system_prompt(session, user)
    llm = get_llm_client()
    settings = get_settings()
    data = await llm.complete_json(
        [
            ChatTurn(role="system", content=system_prompt),
            ChatTurn(role="user", content="\n".join(parts) + "\n\n" + _TIMER_SUGGEST_USER),
        ],
        model=settings.llm_text_model,
        temperature=0.3,
    )

    suggestions = data.get("suggestions") or []
    out: list[dict[str, Any]] = []
    valid_ids = {
        g.id for g in (await session.scalars(select(MuscleGroup))).all()
    }
    for s in suggestions:
        mg = (s.get("muscle_group_id") or "").strip()
        if mg not in valid_ids:
            continue
        try:
            hours = float(s.get("hours") or 0)
        except (TypeError, ValueError):
            hours = 0.0
        hours = max(1.0, min(168.0, hours))
        try:
            intensity = float(s.get("intensity_score") or 0)
        except (TypeError, ValueError):
            intensity = 0.0
        intensity = max(0.0, min(1.0, intensity))
        out.append(
            {
                "muscle_group_id": mg,
                "hours": round(hours, 1),
                "intensity_score": round(intensity, 2),
                "reason": (s.get("reason") or "").strip() or None,
            }
        )
    return out
