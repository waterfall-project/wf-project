# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The installation and the accounts: the first two tables.

Written by hand from ``waterfall.platform.installation`` and ``waterfall.core.users.tables``,
which a test compares with what this migration builds. No row is written: the installation
row is the installer's (US-0420). ``org_node_id`` is not here: EP-05 adds it with its foreign
key, once ``org_node`` exists.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the two tables."""
    op.create_table(
        "installation",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("default_language", sa.Text(), nullable=False),
        sa.Column("avatar_max_bytes", sa.Integer(), nullable=False),
        sa.Column("external_backup_max_bytes", sa.BigInteger(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
        sa.CheckConstraint("default_language IN ('fr', 'en')", name="default_language_known"),
        sa.CheckConstraint("avatar_max_bytes BETWEEN 1 AND 8388608", name="avatar_max_bytes_bound"),
        sa.CheckConstraint(
            "external_backup_max_bytes BETWEEN 1 AND 9007199254740991",
            name="external_backup_max_bytes_bound",
        ),
    )
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("idp_subject", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), server_default="active", nullable=False),
        sa.Column(
            "display_preferences",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("avatar", sa.LargeBinary(), nullable=True),
        sa.Column("avatar_media_type", sa.Text(), nullable=True),
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idp_subject"),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("char_length(last_name) BETWEEN 1 AND 100", name="last_name_length"),
        sa.CheckConstraint("char_length(first_name) BETWEEN 1 AND 100", name="first_name_length"),
        sa.CheckConstraint("char_length(email) >= 1", name="email_not_empty"),
        sa.CheckConstraint("char_length(idp_subject) >= 1", name="idp_subject_not_empty"),
        sa.CheckConstraint(
            "origin IN ('local', 'directory', 'identity_provider')", name="origin_known"
        ),
        sa.CheckConstraint("state IN ('active', 'deactivated')", name="state_known"),
        sa.CheckConstraint(
            "avatar_media_type IN ('image/png', 'image/jpeg')", name="avatar_media_type_known"
        ),
        sa.CheckConstraint("octet_length(avatar) BETWEEN 1 AND 8388608", name="avatar_size"),
        sa.CheckConstraint(
            "(avatar IS NULL) = (avatar_media_type IS NULL)", name="avatar_with_its_media_type"
        ),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    )
    op.create_index(
        "uq_user_account_email_lower", "user_account", [sa.text("lower(email)")], unique=True
    )


def downgrade() -> None:
    """Drop the two tables, and with them every account."""
    op.drop_table("user_account")
    op.drop_table("installation")
