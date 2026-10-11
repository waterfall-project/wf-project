# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The backups of the platform, each taken by a task of the worker (``waterfall.core.backups``).

The role of the service records a backup and reads it, but neither changes nor deletes one: the
mark that keeps a backup and the rotation that deletes the others are EP-13's (WF-ADM-0170).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANT = """
DO $$
BEGIN
    EXECUTE format('GRANT SELECT, INSERT ON backup TO %I', current_database() || '_service');
END
$$
"""


def upgrade() -> None:
    """Create the table of the backups, and grant the service what it needs."""
    op.create_table(
        "backup",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("verification", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("is_retained", sa.Boolean(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("application_version", sa.Text(), nullable=False),
        sa.Column("schema_revision", sa.Text(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["background_task.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint("task_id"),
        sa.CheckConstraint(
            "verification IN ('pending', 'passed', 'failed')", name="verification_known"
        ),
        sa.CheckConstraint("origin IN ('manual', 'scheduled')", name="origin_known"),
        sa.CheckConstraint("size_bytes >= 0", name="size_bytes_not_negative"),
    )
    op.create_index(None, "backup", ["taken_at"])
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table: the archives stay in their bucket, no longer listed."""
    op.drop_table("backup")
