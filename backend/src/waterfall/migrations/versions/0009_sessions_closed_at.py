# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An account notes when its sessions were last closed by its holder (#668).

``closeMySessions`` writes the moment in ``sessions_closed_at``, null until the account first
signs out; the API refuses any access token issued before it, an application next to Waterfall's
included, without waiting for its expiry (WF-SEC-0020). Null, the column asks nothing of the code
before it, which neither reads nor writes it; the service already updates the table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "user_account"
COLUMN = "sessions_closed_at"


def upgrade() -> None:
    """Add the moment of the last sign-out, null for every account that exists."""
    op.add_column(TABLE, sa.Column(COLUMN, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Remove the moment of the last sign-out."""
    op.drop_column(TABLE, COLUMN)
