from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.workout import WorkoutSet


class Exercise(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "exercises"

    canonical_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    display_name_ko: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_muscle_group_id: Mapped[str | None] = mapped_column(
        String(40), ForeignKey("muscle_groups.id"), nullable=True
    )
    # JSON array of muscle group ids — JSON column works in both Postgres and SQLite.
    secondary_muscle_group_ids: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    equipment: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_compound: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    aliases: Mapped[list["ExerciseAlias"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )
    sets: Mapped[list["WorkoutSet"]] = relationship(back_populates="exercise")


class ExerciseAlias(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "exercise_aliases"

    exercise_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(120), nullable=False)

    exercise: Mapped["Exercise"] = relationship(back_populates="aliases")

    __table_args__ = (UniqueConstraint("exercise_id", "alias", name="uq_exercise_alias"),)


SEED_EXERCISES: list[dict[str, object]] = [
    # canonical, ko, en, primary, secondary[], equipment, compound, aliases[]
    {"c": "barbell_bench_press", "ko": "바벨 벤치프레스", "en": "Barbell Bench Press",
     "p": "chest", "s": ["triceps", "shoulders_front"], "eq": "barbell", "co": True,
     "aliases": ["벤치프레스", "bench press", "bb bench"]},
    {"c": "incline_dumbbell_press", "ko": "인클라인 덤벨 프레스", "en": "Incline DB Press",
     "p": "chest", "s": ["shoulders_front", "triceps"], "eq": "dumbbell", "co": True,
     "aliases": ["인클라인 덤벨", "incline db"]},
    {"c": "barbell_squat", "ko": "바벨 스쿼트", "en": "Barbell Squat",
     "p": "quads", "s": ["glutes", "hamstrings"], "eq": "barbell", "co": True,
     "aliases": ["스쿼트", "squat", "back squat"]},
    {"c": "deadlift", "ko": "데드리프트", "en": "Deadlift",
     "p": "back", "s": ["hamstrings", "glutes"], "eq": "barbell", "co": True,
     "aliases": ["데드", "dl"]},
    {"c": "romanian_deadlift", "ko": "루마니안 데드리프트", "en": "Romanian Deadlift",
     "p": "hamstrings", "s": ["glutes", "back"], "eq": "barbell", "co": True,
     "aliases": ["루데", "rdl"]},
    {"c": "barbell_row", "ko": "바벨 로우", "en": "Barbell Row",
     "p": "back", "s": ["biceps"], "eq": "barbell", "co": True,
     "aliases": ["로우", "bb row"]},
    {"c": "pull_up", "ko": "풀업", "en": "Pull Up",
     "p": "back", "s": ["biceps"], "eq": "bodyweight", "co": True,
     "aliases": ["턱걸이", "pullup"]},
    {"c": "lat_pulldown", "ko": "랫 풀다운", "en": "Lat Pulldown",
     "p": "back", "s": ["biceps"], "eq": "cable", "co": True,
     "aliases": ["풀다운"]},
    {"c": "overhead_press", "ko": "오버헤드 프레스", "en": "Overhead Press",
     "p": "shoulders_front", "s": ["triceps", "shoulders_side"], "eq": "barbell", "co": True,
     "aliases": ["ohp", "밀리터리 프레스", "military press"]},
    {"c": "dumbbell_lateral_raise", "ko": "덤벨 사이드 레터럴", "en": "Lateral Raise",
     "p": "shoulders_side", "s": [], "eq": "dumbbell", "co": False,
     "aliases": ["사레레", "lateral raise"]},
    {"c": "barbell_curl", "ko": "바벨 컬", "en": "Barbell Curl",
     "p": "biceps", "s": [], "eq": "barbell", "co": False,
     "aliases": ["바컬"]},
    {"c": "dumbbell_curl", "ko": "덤벨 컬", "en": "Dumbbell Curl",
     "p": "biceps", "s": [], "eq": "dumbbell", "co": False,
     "aliases": ["덤컬", "db curl"]},
    {"c": "hammer_curl", "ko": "해머 컬", "en": "Hammer Curl",
     "p": "biceps", "s": ["forearms"], "eq": "dumbbell", "co": False,
     "aliases": []},
    {"c": "tricep_pushdown", "ko": "삼두 푸시다운", "en": "Tricep Pushdown",
     "p": "triceps", "s": [], "eq": "cable", "co": False,
     "aliases": ["푸시다운"]},
    {"c": "skull_crusher", "ko": "스컬 크러셔", "en": "Skull Crusher",
     "p": "triceps", "s": [], "eq": "barbell", "co": False,
     "aliases": ["라잉 트라이셉 익스텐션"]},
    {"c": "leg_press", "ko": "레그 프레스", "en": "Leg Press",
     "p": "quads", "s": ["glutes"], "eq": "machine", "co": True,
     "aliases": []},
    {"c": "leg_extension", "ko": "레그 익스텐션", "en": "Leg Extension",
     "p": "quads", "s": [], "eq": "machine", "co": False,
     "aliases": []},
    {"c": "leg_curl", "ko": "레그 컬", "en": "Leg Curl",
     "p": "hamstrings", "s": [], "eq": "machine", "co": False,
     "aliases": []},
    {"c": "hip_thrust", "ko": "힙 쓰러스트", "en": "Hip Thrust",
     "p": "glutes", "s": ["hamstrings"], "eq": "barbell", "co": True,
     "aliases": []},
    {"c": "calf_raise", "ko": "카프 레이즈", "en": "Calf Raise",
     "p": "calves", "s": [], "eq": "machine", "co": False,
     "aliases": []},
    {"c": "plank", "ko": "플랭크", "en": "Plank",
     "p": "core", "s": [], "eq": "bodyweight", "co": False,
     "aliases": []},
    {"c": "hanging_leg_raise", "ko": "행잉 레그 레이즈", "en": "Hanging Leg Raise",
     "p": "core", "s": [], "eq": "bodyweight", "co": False,
     "aliases": ["레그레이즈"]},
]
