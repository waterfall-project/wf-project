# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time zone of the installation, in which the current day is taken (EP-25, US-2200).

``installation`` receives ``time_zone``: the name of a time zone of the IANA database, which the
bootstrap writes (WF-EXP-0020, WF-PLA-0130). The row of an installation already bootstrapped
receives ``UTC``, the day it took in fact; the column is then required, without a default: a row
is the bootstrap's, which always names its time zone. The name is checked by the bootstrap, not by
a constraint — the database does not know the time zones —, which refuses only an empty text. The
code before reads the row and does not see the column; the service already updates the row, and no
right is granted.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "installation"


def upgrade() -> None:
    """Add the time zone, ``UTC`` for a row already there, then required without a default."""
    op.add_column(
        TABLE, sa.Column("time_zone", sa.Text(), nullable=False, server_default=sa.text("'UTC'"))
    )
    op.alter_column(TABLE, "time_zone", server_default=None)
    op.create_check_constraint("time_zone_not_empty", TABLE, "time_zone <> ''")


def downgrade() -> None:
    """Drop the time zone, its constraint with it: the installation takes the day in UTC again."""
    op.drop_constraint(op.f("ck_installation_time_zone_not_empty"), TABLE, type_="check")
    op.drop_column(TABLE, "time_zone")
