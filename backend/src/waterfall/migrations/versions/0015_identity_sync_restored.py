# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report of a reading of the accounts counts the local accounts given back their identity.

The reading gives the provider back the identity Waterfall holds of a local account, when the
provider holds another (WF-ADM-0050, #919); its report counts them. A report kept before says none:
the column has a default, which the code before this one, writing no count, leaves to the base.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "identity_sync_report"


def upgrade() -> None:
    """Add the count of the identities given back, none by default, never negative."""
    op.add_column(TABLE, sa.Column("restored", sa.Integer(), server_default="0", nullable=False))
    op.create_check_constraint("restored_not_negative", TABLE, "restored >= 0")


def downgrade() -> None:
    """Drop the count; the identities given back are no longer told."""
    op.drop_constraint(op.f("ck_identity_sync_report_restored_not_negative"), TABLE, type_="check")
    op.drop_column(TABLE, "restored")
