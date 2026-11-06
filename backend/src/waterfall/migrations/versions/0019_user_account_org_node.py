# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The node of the organisation an account is attached to (WF-DAT-0090; EP-03, "Tables").

``user_account`` had no such column in EP-03: it comes now that ``org_node`` exists, nullable — an
account without an attachment, as every account is until one is given —, its key refusing the
deletion of a node, which the service never does. The code before reads and writes the accounts
without knowing it.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column, its key and its index."""
    op.add_column("user_account", sa.Column("org_node_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        None, "user_account", "org_node", ["org_node_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index(None, "user_account", ["org_node_id"])


def downgrade() -> None:
    """Drop the column, with its key and its index: the attachments are lost."""
    op.drop_column("user_account", "org_node_id")
