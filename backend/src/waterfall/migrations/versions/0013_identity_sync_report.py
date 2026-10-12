# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reports of the readings of the accounts of the provider (``waterfall.core.users``).

The role of the service records a report and reads it, but neither changes nor deletes one.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT ON identity_sync_report TO %I', current_database() || '_service'
    );
END
$$
"""


def upgrade() -> None:
    """Create the table of the reports, and grant the service what it needs."""
    op.create_table(
        "identity_sync_report",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("deactivated", sa.Integer(), nullable=False),
        sa.Column("skipped", postgresql.JSONB(), nullable=False),
        sa.Column("removed", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("task_id"),
        sa.ForeignKeyConstraint(["task_id"], ["background_task.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "created >= 0 AND updated >= 0 AND deactivated >= 0", name="counts_not_negative"
        ),
        sa.CheckConstraint("jsonb_typeof(skipped) = 'array'", name="skipped_array"),
        sa.CheckConstraint("jsonb_typeof(removed) = 'array'", name="removed_array"),
    )
    op.create_index(None, "identity_sync_report", ["finished_at"])
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table: the reports are lost with it."""
    op.drop_table("identity_sync_report")
