# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An import keeps the counter of the structure its analysis read (US-3210, #4420).

``import_report.structure_lock_version``, an integer, null, never negative: the counter of the
structure the last analysis of an import read, which the application compares to refuse a report
the structure has outgrown (``import_structure_unchanged``, WF-ARC-0100). Null for an extraction of
actual costs, which reads no structure, for an import analysed without a structure, and for the
reports analysed before this column, which apply without comparison during the twenty-four hours
they live: the code before it writes none, and the code after it reads null as "not compared".

The check is created validated at once, not ``NOT VALID``: every row is null, and the purge keeps
the table small (US-3250).

The descent drops the check and the column: the counters kept are lost, the reports awaiting their
decision then applying without comparison.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "import_report"
COLUMN = "structure_lock_version"
CHECK = "structure_lock_version_not_negative"


def upgrade() -> None:
    """Add the counter of the structure read, null, never negative."""
    op.add_column(TABLE, sa.Column(COLUMN, sa.Integer(), nullable=True))
    op.create_check_constraint(CHECK, TABLE, f"{COLUMN} >= 0")


def downgrade() -> None:
    """Drop the check and the counter; the counters kept are lost."""
    op.drop_constraint(op.f(f"ck_{TABLE}_{CHECK}"), TABLE, type_="check")
    op.drop_column(TABLE, COLUMN)
