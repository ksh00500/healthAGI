"""Consolidate three shoulder groups into one

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-20

"""
from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_OLD_IDS = ("shoulders_front", "shoulders_side", "shoulders_rear")
_NEW_ID = "shoulders"


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Ensure the consolidated row exists so FKs can repoint to it.
    bind.execute(
        sa.text(
            "INSERT INTO muscle_groups (id, display_name_ko, display_name_en, "
            "default_recovery_hours, sort_order) "
            "VALUES (:id, '어깨', 'Shoulders', 48, 30) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": _NEW_ID},
    )

    # 2) Repoint exercises.primary_muscle_group_id and recovery_timers.muscle_group_id.
    for old in _OLD_IDS:
        bind.execute(
            sa.text(
                "UPDATE exercises SET primary_muscle_group_id = :new "
                "WHERE primary_muscle_group_id = :old"
            ),
            {"new": _NEW_ID, "old": old},
        )
        bind.execute(
            sa.text(
                "UPDATE recovery_timers SET muscle_group_id = :new "
                "WHERE muscle_group_id = :old"
            ),
            {"new": _NEW_ID, "old": old},
        )

    # 3) Rewrite the JSON secondary list in Python (works across JSON/JSONB).
    rows = list(
        bind.execute(sa.text("SELECT id, secondary_muscle_group_ids FROM exercises"))
    )
    for row in rows:
        ex_id, raw = row
        if isinstance(raw, str):
            arr = json.loads(raw)
        else:
            arr = raw or []
        new_arr: list[str] = []
        for item in arr:
            mapped = _NEW_ID if item in _OLD_IDS else item
            if mapped not in new_arr:
                new_arr.append(mapped)
        if new_arr != arr:
            bind.execute(
                sa.text(
                    "UPDATE exercises SET secondary_muscle_group_ids = "
                    "CAST(:val AS JSON) WHERE id = :id"
                ),
                {"val": json.dumps(new_arr), "id": ex_id},
            )

    # 4) Drop the obsolete rows.
    for old in _OLD_IDS:
        bind.execute(
            sa.text("DELETE FROM muscle_groups WHERE id = :id"),
            {"id": old},
        )


def downgrade() -> None:
    bind = op.get_bind()
    # Re-insert the old rows; we cannot perfectly attribute which exercises /
    # timers used to be front/side/rear, so leave them on "shoulders".
    bind.execute(
        sa.text(
            "INSERT INTO muscle_groups (id, display_name_ko, display_name_en, "
            "default_recovery_hours, sort_order) VALUES "
            "('shoulders_front', '어깨 전면', 'Front Delts', 48, 30), "
            "('shoulders_side',  '어깨 측면', 'Side Delts',  48, 31), "
            "('shoulders_rear',  '어깨 후면', 'Rear Delts',  48, 32) "
            "ON CONFLICT (id) DO NOTHING"
        )
    )
