# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The index of the nodes by revision, which the key of the evaluations doubles (#3954).

``ix_node_revision_id`` (``0022``) is the prefix of ``uq_node_revision_id`` (``revision_id``,
``id``, ``project_id``; ``0035``), which serves the key of an evaluation to its provision line: the
nodes of a revision are read by its index as well, and the first was one more write of an index by
node, on a wide table partitioned by project. Dropped from the partitioned table, it leaves each
partition.

The descent gives it back, as ``0022`` created it.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "node"


def upgrade() -> None:
    """Drop the index of the nodes by revision, from the table and its partitions."""
    op.drop_index(op.f("ix_node_revision_id"), table_name=TABLE)


def downgrade() -> None:
    """Give the index of the nodes by revision back, to the table and its partitions."""
    op.create_index(None, TABLE, ["revision_id"])
