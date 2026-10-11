# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The background tasks, which the queue of Redis only orders (``waterfall.platform.tasks``).

The role of the service writes a task, reads it and changes its state, but never deletes one: the
retention of the tasks comes with its own rule (§4.4.1).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KINDS = (
    "'import_analysis', 'import_apply', 'revision_mark', 'structure_merge', 'risk_occurrence', "
    "'export', 'backup', 'restore', 'identity_sync'"
)

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE ON background_task TO %I', current_database() || '_service'
    );
END
$$
"""


def upgrade() -> None:
    """Create the table of the tasks, and grant the service what it needs."""
    op.create_table(
        "background_task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("progress", sa.SmallInteger(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("problem", postgresql.JSONB(), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["requested_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(f"kind IN ({KINDS})", name="kind_known"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name="status_known"
        ),
        sa.CheckConstraint("progress BETWEEN 0 AND 100", name="progress_bound"),
        sa.CheckConstraint("attempts >= 0", name="attempts_not_negative"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        sa.CheckConstraint(
            "(problem IS NOT NULL) = (status = 'failed')", name="problem_of_a_failure"
        ),
        sa.CheckConstraint(
            "(finished_at IS NOT NULL) = (status IN ('succeeded', 'failed'))",
            name="finished_at_end",
        ),
        sa.CheckConstraint("correlation_id ~ '^[A-Za-z0-9._-]{1,64}$'", name="correlation_id_form"),
    )
    op.create_index(None, "background_task", ["status"])
    op.create_index(None, "background_task", ["requested_by"])
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table: every task is lost with it."""
    op.drop_table("background_task")
