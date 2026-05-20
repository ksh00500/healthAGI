from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    display_name_ko: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name_en: Mapped[str] = mapped_column(String(40), nullable=False)
    default_recovery_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# Seed data — also referenced from Alembic migration.
SEED_MUSCLE_GROUPS: list[dict[str, object]] = [
    {"id": "chest", "ko": "가슴", "en": "Chest", "hours": 48, "order": 10},
    {"id": "back", "ko": "등", "en": "Back", "hours": 48, "order": 20},
    {"id": "shoulders", "ko": "어깨", "en": "Shoulders", "hours": 48, "order": 30},
    {"id": "biceps", "ko": "이두", "en": "Biceps", "hours": 24, "order": 40},
    {"id": "triceps", "ko": "삼두", "en": "Triceps", "hours": 24, "order": 41},
    {"id": "forearms", "ko": "전완", "en": "Forearms", "hours": 24, "order": 42},
    {"id": "quads", "ko": "대퇴 사두", "en": "Quads", "hours": 72, "order": 50},
    {"id": "hamstrings", "ko": "햄스트링", "en": "Hamstrings", "hours": 72, "order": 51},
    {"id": "glutes", "ko": "둔근", "en": "Glutes", "hours": 72, "order": 52},
    {"id": "calves", "ko": "종아리", "en": "Calves", "hours": 48, "order": 53},
    {"id": "core", "ko": "코어", "en": "Core", "hours": 24, "order": 60},
]
