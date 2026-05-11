from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MuscleGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name_ko: str
    display_name_en: str
    default_recovery_hours: int
    sort_order: int


class TimerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    muscle_group_id: str
    start_time: datetime
    duration_minutes: int
    intensity_score: Decimal | None
    source: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class TimerCreate(BaseModel):
    muscle_group_id: str
    start_time: datetime | None = None  # default = now()
    duration_minutes: int | None = Field(default=None, ge=1, le=60 * 24 * 14)
    intensity_score: Decimal | None = Field(default=None, ge=0, le=1)
    source: Literal["manual", "auto_from_workout", "ai"] = "manual"
    notes: str | None = None
    client_op_id: UUID | None = None


class TimerUpdate(BaseModel):
    start_time: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=60 * 24 * 14)
    intensity_score: Decimal | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
