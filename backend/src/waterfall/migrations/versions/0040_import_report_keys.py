# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An import goes with the structure it aims at and the revision it writes in (US-3060, #4139).

``import_report.structure_id`` and ``revision_id`` named their rows without a key since EP-06
(WF-DAT-0090): the abandonment of a differential (``deleteCostStructure``, US-2550) or of a
revision left the imports that named it pointing at nothing, which the application refused by a
404 alone. Each receives its key, with its project, deleted with what it names (``CASCADE``): the
structure, partitioned by project, and the revision.

The imports that name a structure or a revision gone already are deleted first, in the same
transaction as the keys, so that none comes between: an import aimed at what no longer exists is
never applied, and is no import any more. Their files go with the sweep of the purge, which deletes
an object of ``uploads/`` no row names once the life of a deposit is past (WF-DAT-0120-A). None is
an import of actual costs, which names neither — the only one a row of the costs names
(``cost_import``), which refuses: such a row would make the migration fail, not lose its log.

The keys are posed and checked at once, not ``NOT VALID``: the table holds the imports of a few
days, deleted at their expiry. A project created after them has the keys of its partitions as one
that existed before.

The descent drops the keys; the imports deleted are not given back.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "import_report"
# The imports whose structure or revision is gone, its project's or another's.
DEAD_POINTERS = sa.text(
    "DELETE FROM import_report AS imported WHERE (imported.structure_id IS NOT NULL "
    "AND NOT EXISTS (SELECT FROM cost_structure AS aimed WHERE aimed.project_id = "
    "imported.project_id AND aimed.id = imported.structure_id)) "
    "OR (imported.revision_id IS NOT NULL AND NOT EXISTS (SELECT FROM revision AS written "
    "WHERE written.project_id = imported.project_id AND written.id = imported.revision_id))"
)
# The tables the keys name, and the column of the import each names.
REFERRED = (("cost_structure", "structure_id"), ("revision", "revision_id"))


def upgrade() -> None:
    """Delete the imports of a structure or a revision gone, then key both, in cascade."""
    op.execute(DEAD_POINTERS)
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
    """Drop the keys; the imports the ascent deleted are lost."""
    for referred, _ in reversed(REFERRED):
        op.drop_constraint(op.f(f"fk_{TABLE}_project_id_{referred}"), TABLE, type_="foreignkey")
