# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The counter of a line of cost the key of the cache of the indicators reads (EP-10, US-1720/L3).

``cost_line.lock_version``, a non-null integer, zero for a line that exists: every write of a value
the indicators read — a line an import creates or changes, an exclusion or a reinstatement, an
imputation to a subproject created — advances it under the lock of the project; a line an import
finds unchanged only names that import, and the key moves by the number of the imports.
``costs_stamp`` reads the sum (author's decision of 2026-11-16, #3629). The instant ``updated_at``
is that of the start of an act, not of its commit, and a write that started first and commits last
leaves its maximum where it was. The table is not partitioned: the column is added to it as it is.
The descent drops the column.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the counter to the lines of cost, zero for each that exists."""
    op.add_column(
        "cost_line",
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    """Drop the counter."""
    op.drop_column("cost_line", "lock_version")
