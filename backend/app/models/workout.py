from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.exercise import Exercise


class WorkoutSession(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workout_sessions"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)

    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="WorkoutSet.set_index"
    )

    __table_args__ = (
        Index("ix_sessions_user_started", "user_id", "started_at"),
        Index("ix_sessions_user_updated", "user_id", "updated_at"),
    )


class WorkoutSet(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workout_sets"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exercises.id"),
        nullable=False,
        index=True,
    )
    set_index: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["WorkoutSession"] = relationship(back_populates="sets")
    exercise: Mapped["Exercise"] = relationship(back_populates="sets")
