from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, SessionDep
from app.models.recommendation import DailyRecommendation
from app.schemas.recommendation import GenerateRequest, RecommendationRead
from app.services.recommendations import generate_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/today", response_model=list[RecommendationRead])
async def list_today(
    user: CurrentUser, session: SessionDep
) -> list[DailyRecommendation]:
    today = datetime.now(UTC).date()
    rows = await session.scalars(
        select(DailyRecommendation)
        .where(
            DailyRecommendation.user_id == user.id,
            DailyRecommendation.for_date == today,
            DailyRecommendation.deleted_at.is_(None),
        )
        .order_by(DailyRecommendation.kind)
    )
    return list(rows)


@router.post(
    "/generate",
    response_model=list[RecommendationRead],
    status_code=status.HTTP_201_CREATED,
)
async def generate(
    payload: GenerateRequest, user: CurrentUser, session: SessionDep
) -> list[DailyRecommendation]:
    target = payload.for_date or datetime.now(UTC).date()
    if not payload.force:
        existing = list(
            await session.scalars(
                select(DailyRecommendation).where(
                    DailyRecommendation.user_id == user.id,
                    DailyRecommendation.for_date == target,
                    DailyRecommendation.deleted_at.is_(None),
                )
            )
        )
        if existing:
            return existing
    try:
        return await generate_recommendations(session, user, target)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"recommendation generation failed: {e}"
        ) from e
