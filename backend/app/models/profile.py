from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)  # M/F/O
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Seoul", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="ko-KR", nullable=False)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")
