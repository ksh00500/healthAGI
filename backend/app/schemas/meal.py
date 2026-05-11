from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MealType = Literal["breakfast", "lunch", "dinner", "snack"]


class MealItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    serving_g: Decimal | None
    kcal: Decimal | None
    protein_g: Decimal | None
    carbs_g: Decimal | None
    fat_g: Decimal | None
    ai_confidence: Decimal | None
    user_confirmed: bool


class MealItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    serving_g: Decimal | None = Field(default=None, ge=0, le=10000)
    kcal: Decimal | None = Field(default=None, ge=0, le=10000)
    protein_g: Decimal | None = Field(default=None, ge=0, le=1000)
    carbs_g: Decimal | None = Field(default=None, ge=0, le=1000)
    fat_g: Decimal | None = Field(default=None, ge=0, le=1000)
    ai_confidence: Decimal | None = Field(default=None, ge=0, le=1)
    user_confirmed: bool = True


class MealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    eaten_at: datetime
    meal_type: MealType | None
    raw_input: str | None
    total_kcal: Decimal | None
    total_protein_g: Decimal | None
    total_carbs_g: Decimal | None
    total_fat_g: Decimal | None
    source: str
    notes: str | None
    items: list[MealItemRead]
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MealCreate(BaseModel):
    eaten_at: datetime | None = None
    meal_type: MealType | None = None
    raw_input: str | None = None
    source: str = "manual"
    notes: str | None = None
    items: list[MealItemInput] = Field(default_factory=list)
    photo_storage_key: str | None = None  # links an existing MealPhoto row


class MealUpdate(BaseModel):
    eaten_at: datetime | None = None
    meal_type: MealType | None = None
    raw_input: str | None = None
    notes: str | None = None
    items: list[MealItemInput] | None = None
