from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.user import User


class BodyMetric(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "body_metrics_history"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="body_metrics")
