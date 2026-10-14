# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The files deposited on the object storage, by parts (``waterfall.platform.uploads``, #350).

The role of the service records a deposit, reads it and completes it, but deletes none.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE ON file_upload TO %I', current_database() || '_service'
    );
END
$$
"""


def upgrade() -> None:
    """Create the table of the deposits, and grant the service what it needs."""
    op.create_table(
        "file_upload",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("part_size_bytes", sa.Integer(), nullable=False),
        sa.Column("part_count", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("deposit", sa.Text(), nullable=True),
        sa.Column("backup_taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("purpose IN ('import', 'external_backup')", name="purpose_known"),
        sa.CheckConstraint("char_length(filename) BETWEEN 1 AND 255", name="filename_length"),
        sa.CheckConstraint("size_bytes >= 1", name="size_bytes_positive"),
        sa.CheckConstraint("part_size_bytes BETWEEN 5242880 AND 10485760", name="part_size_bound"),
        sa.CheckConstraint("part_count BETWEEN 1 AND 10000", name="part_count_bound"),
        sa.CheckConstraint(
            "(deposit IS NULL) = (completed_at IS NOT NULL)", name="open_or_completed"
        ),
    )
    op.create_index(None, "file_upload", ["uploaded_by"])
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table: the deposits are lost with it, not their objects on the storage."""
    op.drop_table("file_upload")
