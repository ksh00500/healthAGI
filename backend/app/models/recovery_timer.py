from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.user import User


class RecoveryTimer(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "recovery_timers"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    muscle_group_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("muscle_groups.id"),
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    intensity_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_op_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True, unique=True
    )

    user: Mapped["User"] = relationship(back_populates="recovery_timers")

    __table_args__ = (
        Index(
            "ix_timers_user_muscle_active",
            "user_id",
            "muscle_group_id",
            "deleted_at",
        ),
        Index("ix_timers_user_updated_at", "user_id", "updated_at"),
    )
