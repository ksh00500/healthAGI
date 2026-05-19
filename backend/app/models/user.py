from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.body_metric import BodyMetric
    from app.models.profile import Profile
    from app.models.recovery_timer import RecoveryTimer


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped[Profile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    body_metrics: Mapped[list[BodyMetric]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recovery_timers: Mapped[list[RecoveryTimer]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
