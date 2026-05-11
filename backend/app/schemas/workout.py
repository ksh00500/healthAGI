from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    canonical_name: str
    display_name_ko: str | None
    display_name_en: str | None
    primary_muscle_group_id: str | None
    secondary_muscle_group_ids: list[str]
    equipment: str | None
    is_compound: bool


class ExerciseCreate(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=120)
    display_name_ko: str | None = None
    display_name_en: str | None = None
    primary_muscle_group_id: str | None = None
    secondary_muscle_group_ids: list[str] = Field(default_factory=list)
    equipment: str | None = None
    is_compound: bool = False
    aliases: list[str] = Field(default_factory=list)


class WorkoutSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exercise_id: UUID
    set_index: int
    reps: int | None
    weight_kg: Decimal | None
    rpe: Decimal | None
    is_warmup: bool
    notes: str | None


class WorkoutSetInput(BaseModel):
    exercise_id: UUID
    set_index: int = Field(ge=1)
    reps: int | None = Field(default=None, ge=0, le=1000)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=1000)
    rpe: Decimal | None = Field(default=None, ge=0, le=10)
    is_warmup: bool = False
    notes: str | None = None


class WorkoutSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    raw_input: str | None
    sets: list[WorkoutSetRead]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class WorkoutSessionCreate(BaseModel):
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None
    raw_input: str | None = None
    sets: list[WorkoutSetInput] = Field(default_factory=list)


class WorkoutSessionUpdate(BaseModel):
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None
    raw_input: str | None = None
    # Full replace of sets when present.
    sets: list[WorkoutSetInput] | None = None
