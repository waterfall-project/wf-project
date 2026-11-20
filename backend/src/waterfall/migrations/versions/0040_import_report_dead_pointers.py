# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Delete the imports that name a structure or a revision gone (US-3060, #4139).

``import_report.structure_id`` and ``revision_id`` named their rows without a key since EP-06
(WF-DAT-0090): the abandonment of a differential (``deleteCostStructure``, US-2550) or of a
revision left the imports that named it pointing at nothing, which the application refused by a
404 alone. The keys of the next migration would fail on them, so they go first, in a migration of
their own, as data: an import aimed at what no longer exists is never applied, and is no import
any more. Their files go with the sweep of the purge, which deletes an object of ``uploads/`` no
row names once the life of a deposit is past (WF-DAT-0120-A). None is an import of actual costs,
which names neither: the only one a row of the costs names (``cost_import``) refuses, and such a
row would make the migration fail, not lose its log.

The descent does nothing: the imports deleted are not given back.
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

# The imports whose structure or revision is gone, its project's or another's.
DEAD_POINTERS = sa.text(
    "DELETE FROM import_report AS imported WHERE (imported.structure_id IS NOT NULL "
    "AND NOT EXISTS (SELECT FROM cost_structure AS aimed WHERE aimed.project_id = "
    "imported.project_id AND aimed.id = imported.structure_id)) "
    "OR (imported.revision_id IS NOT NULL AND NOT EXISTS (SELECT FROM revision AS written "
    "WHERE written.project_id = imported.project_id AND written.id = imported.revision_id))"
)


def upgrade() -> None:
    """Delete the imports of a structure or a revision gone."""
    op.execute(DEAD_POINTERS)


def downgrade() -> None:
    """Do nothing: the imports the ascent deleted are lost."""
