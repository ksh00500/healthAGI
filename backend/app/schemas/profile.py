from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str | None = None
    birth_date: date | None = None
    sex: Literal["M", "F", "O"] | None = None
    height_cm: Decimal | None = None
    timezone: str
    locale: str
    goals: str | None = None
    notes: str | None = None
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    birth_date: date | None = None
    sex: Literal["M", "F", "O"] | None = None
    height_cm: Decimal | None = Field(default=None, ge=0, le=300)
    timezone: str | None = None
    locale: str | None = None
    goals: str | None = None
    notes: str | None = None


class BodyMetricRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    measured_at: datetime
    weight_kg: Decimal | None
    body_fat_pct: Decimal | None
    resting_hr: int | None
    sleep_hours: Decimal | None
    notes: str | None
    updated_at: datetime
    deleted_at: datetime | None


class BodyMetricCreate(BaseModel):
    measured_at: datetime
    weight_kg: Decimal | None = Field(default=None, ge=0, le=500)
    body_fat_pct: Decimal | None = Field(default=None, ge=0, le=100)
    resting_hr: int | None = Field(default=None, ge=20, le=250)
    sleep_hours: Decimal | None = Field(default=None, ge=0, le=24)
    notes: str | None = None


class BodyMetricUpdate(BaseModel):
    measured_at: datetime | None = None
    weight_kg: Decimal | None = Field(default=None, ge=0, le=500)
    body_fat_pct: Decimal | None = Field(default=None, ge=0, le=100)
    resting_hr: int | None = Field(default=None, ge=20, le=250)
    sleep_hours: Decimal | None = Field(default=None, ge=0, le=24)
    notes: str | None = None
