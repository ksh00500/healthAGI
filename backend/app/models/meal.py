from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    pass


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

    items: Mapped[list["MealItem"]] = relationship(
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

    meal: Mapped["Meal"] = relationship(back_populates="items")
