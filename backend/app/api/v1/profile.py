from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import CurrentUser, SessionDep
from app.models.body_metric import BodyMetric
from app.models.profile import Profile
from app.schemas.profile import (
    BodyMetricCreate,
    BodyMetricRead,
    BodyMetricUpdate,
    ProfileRead,
    ProfileUpdate,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
async def get_profile(user: CurrentUser, session: SessionDep) -> Profile:
    profile = await session.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.put("", response_model=ProfileRead)
async def update_profile(
    payload: ProfileUpdate, user: CurrentUser, session: SessionDep
) -> Profile:
    profile = await session.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
        session.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await session.commit()
    await session.refresh(profile)
    return profile


@router.get("/body-metrics", response_model=list[BodyMetricRead])
async def list_body_metrics(
    user: CurrentUser,
    session: SessionDep,
    since: datetime | None = Query(default=None),
) -> list[BodyMetric]:
    stmt = select(BodyMetric).where(BodyMetric.user_id == user.id)
    if since is not None:
        stmt = stmt.where(BodyMetric.updated_at > since)
    stmt = stmt.order_by(BodyMetric.measured_at.desc())
    rows = await session.scalars(stmt)
    return list(rows)


@router.post(
    "/body-metrics",
    response_model=BodyMetricRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_body_metric(
    payload: BodyMetricCreate, user: CurrentUser, session: SessionDep
) -> BodyMetric:
    metric = BodyMetric(user_id=user.id, **payload.model_dump())
    session.add(metric)
    await session.commit()
    await session.refresh(metric)
    return metric


@router.patch("/body-metrics/{metric_id}", response_model=BodyMetricRead)
async def update_body_metric(
    metric_id: UUID,
    payload: BodyMetricUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> BodyMetric:
    metric = await session.scalar(
        select(BodyMetric).where(
            BodyMetric.id == metric_id,
            BodyMetric.user_id == user.id,
            BodyMetric.deleted_at.is_(None),
        )
    )
    if not metric:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "metric not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)
    await session.commit()
    await session.refresh(metric)
    return metric


@router.delete("/body-metrics/{metric_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_body_metric(
    metric_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    metric = await session.scalar(
        select(BodyMetric).where(
            BodyMetric.id == metric_id,
            BodyMetric.user_id == user.id,
            BodyMetric.deleted_at.is_(None),
        )
    )
    if not metric:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "metric not found")
    from datetime import timezone as _tz

    metric.deleted_at = datetime.now(_tz.utc)
    await session.commit()
