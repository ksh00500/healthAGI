"""workouts + meals tables, seed canonical exercises

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11

"""
from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.models.exercise import SEED_EXERCISES

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("canonical_name", sa.String(120), nullable=False, unique=True),
        sa.Column("display_name_ko", sa.String(120), nullable=True),
        sa.Column("display_name_en", sa.String(120), nullable=True),
        sa.Column(
            "primary_muscle_group_id",
            sa.String(40),
            sa.ForeignKey("muscle_groups.id"),
            nullable=True,
        ),
        sa.Column("secondary_muscle_group_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("equipment", sa.String(40), nullable=True),
        sa.Column("is_compound", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_ai", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "exercise_aliases",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "exercise_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("exercise_id", "alias", name="uq_exercise_alias"),
    )

    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_started", "workout_sessions", ["user_id", "started_at"])
    op.create_index("ix_sessions_user_updated", "workout_sessions", ["user_id", "updated_at"])

    op.create_table(
        "workout_sets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workout_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("exercises.id"),
            nullable=False,
        ),
        sa.Column("set_index", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("rpe", sa.Numeric(3, 1), nullable=True),
        sa.Column("is_warmup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sets_session", "workout_sets", ["session_id"])
    op.create_index("ix_sets_exercise", "workout_sets", ["exercise_id"])

    op.create_table(
        "meals",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("total_kcal", sa.Numeric(6, 1), nullable=True),
        sa.Column("total_protein_g", sa.Numeric(5, 1), nullable=True),
        sa.Column("total_carbs_g", sa.Numeric(5, 1), nullable=True),
        sa.Column("total_fat_g", sa.Numeric(5, 1), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_meals_user_eaten", "meals", ["user_id", "eaten_at"])
    op.create_index("ix_meals_user_updated", "meals", ["user_id", "updated_at"])

    op.create_table(
        "meal_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("serving_g", sa.Numeric(6, 1), nullable=True),
        sa.Column("kcal", sa.Numeric(6, 1), nullable=True),
        sa.Column("protein_g", sa.Numeric(5, 1), nullable=True),
        sa.Column("carbs_g", sa.Numeric(5, 1), nullable=True),
        sa.Column("fat_g", sa.Numeric(5, 1), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_meal_items_meal", "meal_items", ["meal_id"])

    # --- Seed exercises ---
    exercises_t = sa.table(
        "exercises",
        sa.column("id", sa.Uuid),
        sa.column("canonical_name", sa.String),
        sa.column("display_name_ko", sa.String),
        sa.column("display_name_en", sa.String),
        sa.column("primary_muscle_group_id", sa.String),
        sa.column("secondary_muscle_group_ids", sa.JSON),
        sa.column("equipment", sa.String),
        sa.column("is_compound", sa.Boolean),
    )
    aliases_t = sa.table(
        "exercise_aliases",
        sa.column("id", sa.Uuid),
        sa.column("exercise_id", sa.Uuid),
        sa.column("alias", sa.String),
    )
    exercise_rows: list[dict] = []
    alias_rows: list[dict] = []
    for e in SEED_EXERCISES:
        ex_id = uuid4()
        exercise_rows.append({
            "id": ex_id,
            "canonical_name": e["c"],
            "display_name_ko": e["ko"],
            "display_name_en": e["en"],
            "primary_muscle_group_id": e["p"],
            "secondary_muscle_group_ids": e["s"],
            "equipment": e["eq"],
            "is_compound": e["co"],
        })
        for alias in e["aliases"]:
            alias_rows.append({
                "id": uuid4(),
                "exercise_id": ex_id,
                "alias": alias,
            })
    if exercise_rows:
        op.bulk_insert(exercises_t, exercise_rows)
    if alias_rows:
        op.bulk_insert(aliases_t, alias_rows)


def downgrade() -> None:
    op.drop_index("ix_meal_items_meal", table_name="meal_items")
    op.drop_table("meal_items")
    op.drop_index("ix_meals_user_updated", table_name="meals")
    op.drop_index("ix_meals_user_eaten", table_name="meals")
    op.drop_table("meals")
    op.drop_index("ix_sets_exercise", table_name="workout_sets")
    op.drop_index("ix_sets_session", table_name="workout_sets")
    op.drop_table("workout_sets")
    op.drop_index("ix_sessions_user_updated", table_name="workout_sessions")
    op.drop_index("ix_sessions_user_started", table_name="workout_sessions")
    op.drop_table("workout_sessions")
    op.drop_table("exercise_aliases")
    op.drop_table("exercises")
