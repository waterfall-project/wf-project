# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time zone of the installation takes ``UTC`` again by default (US-2850/L5, #5090).

``0029`` made ``installation.time_zone`` required and removed its default. The code of the version
before, which inserts the row of the installation without that column — its bootstrap, its
reference installation —, then fails on the migrated schema (WF-DAT-0140-A: the code of the
version N runs on the schema migrated). The default is written back, as a migration after ``0029``
does, ``0029`` being published: the column stays required, and the bootstrap of the version that
knows it still writes the time zone it names.

The descent removes the default, as ``0029`` left the column.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0058"
down_revision: str | None = "0057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "installation"


def upgrade() -> None:
    """Give ``time_zone`` the default ``UTC``, the column staying required."""
    op.alter_column(TABLE, "time_zone", server_default=sa.text("'UTC'"))


def downgrade() -> None:
    """Remove the default of ``time_zone``."""
    op.alter_column(TABLE, "time_zone", server_default=None)
