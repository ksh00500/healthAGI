from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class DailyRecommendation(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A per-user/per-day AI recommendation card (pre-computed snapshot).

    `kind` is one of:
      - workout_split: which muscle group(s) to train today
      - nutrition_focus: protein/carb/fat targets and gaps vs the last 3 days
      - recovery_check: which muscles are still recovering
    """

    __tablename__ = "daily_recommendations"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    for_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "for_date", "kind", name="uq_recs_user_date_kind"),
        Index("ix_recs_user_date", "user_id", "for_date"),
    )
