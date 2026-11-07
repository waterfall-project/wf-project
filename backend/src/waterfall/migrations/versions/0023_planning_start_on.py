# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The date each structure starts its planning on, and the instant its dates were computed (#2170).

A data migration, apart from the schema (sql.md, rule 3): each structure receives the values the
code derived for it before ``0022`` gave them columns — the day, in universal time, of the creation
of the origin of its lineage, or of its own creation were that origin missing; the instant of its
own creation. Nothing a reader sees changes, a marked revision's structures included: the guard of
the cost structures, which refuses any write of a row of a marked revision, is turned off for the
statement alone, in the transaction of the migration, by the owner of the table.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GUARD = "cost_structure_refuse_marked_change"
FILL = """
UPDATE cost_structure AS structure
SET planning_start_on = (
        COALESCE(
            (
                SELECT origin.created_at FROM cost_structure AS origin
                WHERE origin.project_id = structure.project_id AND origin.id = structure.lineage_id
            ),
            structure.created_at
        ) AT TIME ZONE 'UTC'
    )::date,
    scheduled_at = structure.created_at
WHERE structure.planning_start_on IS NULL OR structure.scheduled_at IS NULL
"""
EMPTY = "UPDATE cost_structure SET planning_start_on = NULL, scheduled_at = NULL"


def _unguarded(statement: str) -> None:
    """Run a statement on the cost structures, their guard off for it alone."""
    op.execute(f"ALTER TABLE cost_structure DISABLE TRIGGER {GUARD}")
    op.execute(statement)
    op.execute(f"ALTER TABLE cost_structure ENABLE TRIGGER {GUARD}")


def upgrade() -> None:
    """Fill the two columns of every structure with the values the code derived."""
    _unguarded(FILL)


def downgrade() -> None:
    """Empty the two columns, which the code before ``0022`` derived: nothing it reads is lost."""
    _unguarded(EMPTY)
