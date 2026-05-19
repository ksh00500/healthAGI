from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, SessionDep
from app.models.meal import Meal, MealItem, MealPhoto
from app.schemas.meal import MealCreate, MealItemInput, MealRead, MealUpdate

router = APIRouter(prefix="/meals", tags=["meals"])


def _recompute_totals(meal: Meal) -> None:
    zero = Decimal("0")

    def s(attr: str) -> Decimal | None:
        vals = [getattr(i, attr) for i in meal.items if getattr(i, attr) is not None]
        return sum(vals, zero) if vals else None

    meal.total_kcal = s("kcal")
    meal.total_protein_g = s("protein_g")
    meal.total_carbs_g = s("carbs_g")
    meal.total_fat_g = s("fat_g")


def _load_meal_stmt(user_id: UUID, meal_id: UUID | None = None) -> Select[tuple[Meal]]:
    stmt = (
        select(Meal)
        .options(selectinload(Meal.items))
        .where(Meal.user_id == user_id, Meal.deleted_at.is_(None))
    )
    if meal_id is not None:
        stmt = stmt.where(Meal.id == meal_id)
    return stmt


@router.get("", response_model=list[MealRead])
async def list_meals(
    user: CurrentUser,
    session: SessionDep,
    since: datetime | None = Query(default=None),
    day: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Meal]:
    stmt = _load_meal_stmt(user.id)
    if since is not None:
        stmt = stmt.where(Meal.updated_at > since)
    if day is not None:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        end = datetime.combine(day, time.max, tzinfo=UTC)
        stmt = stmt.where(Meal.eaten_at >= start, Meal.eaten_at <= end)
    stmt = stmt.order_by(Meal.eaten_at.desc()).limit(limit)
    rows = await session.scalars(stmt)
    return list(rows.unique())


def _build_items(items: list[MealItemInput]) -> list[MealItem]:
    return [
        MealItem(
            name=i.name,
            serving_g=i.serving_g,
            kcal=i.kcal,
            protein_g=i.protein_g,
            carbs_g=i.carbs_g,
            fat_g=i.fat_g,
            ai_confidence=i.ai_confidence,
            user_confirmed=i.user_confirmed,
        )
        for i in items
    ]


@router.post("", response_model=MealRead, status_code=status.HTTP_201_CREATED)
async def create_meal(
    payload: MealCreate, user: CurrentUser, session: SessionDep
) -> Meal:
    photo: MealPhoto | None = None
    if payload.photo_storage_key:
        photo = await session.scalar(
            select(MealPhoto).where(
                MealPhoto.storage_key == payload.photo_storage_key,
                MealPhoto.user_id == user.id,
            )
        )
        if photo is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"unknown photo storage_key: {payload.photo_storage_key}",
            )
        if photo.meal_id is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "photo is already attached to another meal",
            )

    meal = Meal(
        user_id=user.id,
        eaten_at=payload.eaten_at or datetime.now(UTC),
        meal_type=payload.meal_type,
        raw_input=payload.raw_input,
        source="photo" if photo is not None else payload.source,
        notes=payload.notes,
    )
    meal.items = _build_items(payload.items)
    _recompute_totals(meal)
    session.add(meal)
    await session.flush()
    if photo is not None:
        photo.meal_id = meal.id
    await session.commit()
    reloaded = await session.scalar(_load_meal_stmt(user.id, meal.id))
    assert reloaded is not None
    return reloaded


@router.patch("/{meal_id}", response_model=MealRead)
async def update_meal(
    meal_id: UUID,
    payload: MealUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> Meal:
    meal = await session.scalar(_load_meal_stmt(user.id, meal_id))
    if not meal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "meal not found")
    data = payload.model_dump(exclude_unset=True)
    for field in ("eaten_at", "meal_type", "raw_input", "notes"):
        if field in data:
            setattr(meal, field, data[field])
    if "items" in data and data["items"] is not None:
        meal.items.clear()
        for it in _build_items(payload.items or []):
            meal.items.append(it)
        _recompute_totals(meal)
    await session.commit()
    reloaded = await session.scalar(_load_meal_stmt(user.id, meal_id))
    assert reloaded is not None
    return reloaded


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(
    meal_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    meal = await session.scalar(_load_meal_stmt(user.id, meal_id))
    if not meal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "meal not found")
    meal.deleted_at = datetime.now(UTC)
    await session.commit()
