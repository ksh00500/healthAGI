from __future__ import annotations

from datetime import date as _Date
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RecKind = Literal["workout_split", "nutrition_focus", "recovery_check"]


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    for_date: _Date
    kind: RecKind
    title: str
    body: str
    rationale: str | None
    source_context: dict[str, Any] | None
    model: str | None
    updated_at: datetime


class GenerateRequest(BaseModel):
    for_date: _Date | None = None
    force: bool = False


class SuggestSet(BaseModel):
    exercise_id: UUID
    set_index: int = Field(ge=1)
    reps: int | None = Field(default=None, ge=0, le=1000)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=1000)
    rpe: Decimal | None = Field(default=None, ge=0, le=10)
    is_warmup: bool = False


class SuggestRequest(BaseModel):
    """Used by /timers/suggest. Either pass an existing session_id OR a sets list."""

    session_id: UUID | None = None
    sets: list[SuggestSet] = Field(default_factory=list)
    notes: str | None = None


class SuggestedTimer(BaseModel):
    muscle_group_id: str
    hours: float
    intensity_score: float
    reason: str | None = None


class SuggestResponse(BaseModel):
    suggestions: list[SuggestedTimer]
