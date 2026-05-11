"""initial schema (users, profile, body metrics, muscle groups, recovery timers)

Revision ID: 0001
Revises:
Create Date: 2026-05-11

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models.muscle_group import SEED_MUSCLE_GROUPS

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "profiles",
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("display_name", sa.String(80), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("sex", sa.String(1), nullable=True),
        sa.Column("height_cm", sa.Numeric(5, 1), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Seoul"),
        sa.Column("locale", sa.String(16), nullable=False, server_default="ko-KR"),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "body_metrics_history",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("body_fat_pct", sa.Numeric(4, 1), nullable=True),
        sa.Column("resting_hr", sa.Integer(), nullable=True),
        sa.Column("sleep_hours", sa.Numeric(3, 1), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_body_metrics_user", "body_metrics_history", ["user_id"])
    op.create_index("ix_body_metrics_measured_at", "body_metrics_history", ["measured_at"])

    op.create_table(
        "muscle_groups",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("display_name_ko", sa.String(40), nullable=False),
        sa.Column("display_name_en", sa.String(40), nullable=False),
        sa.Column("default_recovery_hours", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "recovery_timers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("muscle_group_id", sa.String(40), sa.ForeignKey("muscle_groups.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("intensity_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_op_id", sa.Uuid(as_uuid=True), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_timers_user_muscle_active",
        "recovery_timers",
        ["user_id", "muscle_group_id", "deleted_at"],
    )
    op.create_index("ix_timers_user_updated_at", "recovery_timers", ["user_id", "updated_at"])

    # Seed muscle groups
    muscle_groups_table = sa.table(
        "muscle_groups",
        sa.column("id", sa.String),
        sa.column("display_name_ko", sa.String),
        sa.column("display_name_en", sa.String),
        sa.column("default_recovery_hours", sa.Integer),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(
        muscle_groups_table,
        [
            {
                "id": mg["id"],
                "display_name_ko": mg["ko"],
                "display_name_en": mg["en"],
                "default_recovery_hours": mg["hours"],
                "sort_order": mg["order"],
            }
            for mg in SEED_MUSCLE_GROUPS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_timers_user_updated_at", table_name="recovery_timers")
    op.drop_index("ix_timers_user_muscle_active", table_name="recovery_timers")
    op.drop_table("recovery_timers")
    op.drop_table("muscle_groups")
    op.drop_index("ix_body_metrics_measured_at", table_name="body_metrics_history")
    op.drop_index("ix_body_metrics_user", table_name="body_metrics_history")
    op.drop_table("body_metrics_history")
    op.drop_table("profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
