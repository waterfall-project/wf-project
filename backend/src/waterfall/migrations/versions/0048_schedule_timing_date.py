# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The date of the last change of the timing of the schedule of the backups (EP-13, US-2910).

``updated_at`` is that of every writing of the schedule (WF-DAT-0070); what the platform owes of a
backup (WF-ADM-0170) is read from the date its timing — enabled, frequency, time, weekday — last
changed, which a writing of the retention or of the copy alone does not move. The column takes,
for the row there, the date of its last writing, which is what the timing was dated by until then.

In one step, by decided exception to "Migrations : deux temps" (``docs/dev/sql.md``, #4375): the
column is added, filled and required at once, where an update would else have the code of 0047 —
which writes the row without it, at a restoration (``replace_by_kept``) — fail beside the
migrated database. No installation runs that code: 0046 and 0047, which create the schedule, are
in no release, neither ``main`` nor a tag, and arrive with this one. A release that holds 0047
alone would ask for the two steps.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column, dated for the row there by its last writing, then require it."""
    op.add_column(
        "backup_schedule", sa.Column("timing_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE backup_schedule SET timing_changed_at = updated_at")
    op.alter_column("backup_schedule", "timing_changed_at", nullable=False)


def downgrade() -> None:
    """Drop the column."""
    op.drop_column("backup_schedule", "timing_changed_at")
