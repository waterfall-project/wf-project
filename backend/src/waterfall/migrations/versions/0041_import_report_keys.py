# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An import goes with the structure it aims at and the revision it writes in (US-3060, #4139).

Each of ``import_report.structure_id`` and ``revision_id`` receives its key, with its project,
deleted with what it names (``CASCADE``): the structure, partitioned by project, and the revision.
The imports that pointed at nothing are deleted by the migration before.

The keys are posed and checked at once, not ``NOT VALID``: the table holds the imports of a few
days, deleted at their expiry. A project created after them has the keys of its partitions as one
that existed before.

The descent drops the keys.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "import_report"
# The tables the keys name, and the column of the import each names.
REFERRED = (("cost_structure", "structure_id"), ("revision", "revision_id"))


def upgrade() -> None:
    """Key the structure and the revision of an import, in cascade."""
    for referred, column in REFERRED:
        op.create_foreign_key(
            None,
            TABLE,
            referred,
            ["project_id", column],
            ["project_id", "id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Drop the keys."""
    for referred, _ in reversed(REFERRED):
        op.drop_constraint(op.f(f"fk_{TABLE}_project_id_{referred}"), TABLE, type_="foreignkey")
