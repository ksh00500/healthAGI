from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Meal(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "meals"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meal_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_kcal: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    total_protein_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    total_carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    total_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[MealItem]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )
    photos: Mapped[list[MealPhoto]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_meals_user_eaten", "user_id", "eaten_at"),
        Index("ix_meals_user_updated", "user_id", "updated_at"),
    )


class MealItem(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "meal_items"

    meal_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    serving_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    kcal: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    meal: Mapped[Meal] = relationship(back_populates="items")


class MealPhoto(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "meal_photos"

    meal_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("meals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    vision_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vision_raw_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    meal: Mapped[Meal | None] = relationship(back_populates="photos")
