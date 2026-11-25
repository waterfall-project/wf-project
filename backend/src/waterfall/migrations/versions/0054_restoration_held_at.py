# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Since when a restoration holds the maintenance: what its deadline counts from (EP-13, #1016).

``platform.restoration.held_at`` is the moment the maintenance was held for the restoration, at
its first attempt: one held longer than the deadline is given up, its task failed and the
maintenance lifted (``waterfall.restore.runner``). A row there — a restoration under way at the
migration — is dated by the migration, its deadline counted from then.

The schema ``platform`` is left in place by a restoration, which applies the migrations that follow
its backup again (0048): the column is added where it is missing, and a restoration of a backup
taken before this revision leaves it as it is, the maintenance it holds included.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "platform"
TABLE = "restoration"
COLUMN = "held_at"


def upgrade() -> None:
    """Add the column where it is missing, dated now for a row there."""
    op.add_column(
        TABLE,
        sa.Column(COLUMN, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the column."""
    op.drop_column(TABLE, COLUMN, schema=SCHEMA)
