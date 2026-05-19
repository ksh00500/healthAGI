"""meal_photos table for vision-based meal logging

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-11

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_photos",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meal_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meals.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vision_model", sa.String(80), nullable=True),
        sa.Column("vision_raw_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_meal_photos_meal", "meal_photos", ["meal_id"])
    op.create_index("ix_meal_photos_user", "meal_photos", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_meal_photos_user", table_name="meal_photos")
    op.drop_index("ix_meal_photos_meal", table_name="meal_photos")
    op.drop_table("meal_photos")
