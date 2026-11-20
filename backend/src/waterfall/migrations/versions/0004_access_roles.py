# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles: the catalogue of permissions, the roles, what they grant and who holds them.

Written by hand from ``waterfall.core.access_roles.tables``, which a test compares with what this
migration builds. The catalogue is filled by the next migration, a migration of data. The role of
the service reads the catalogue and writes nothing in it (WF-ADM-0100); it creates and changes a
role but never deletes one, which is marked deleted (WF-DAT-0080); it adds and removes the rows of
the two associations, which hold nothing but their keys. The extension ``unaccent`` serves the
search of a label, which ignores the accents (contract, README).

The search also lowers a text in the collation ``und-x-icu``, which only a PostgreSQL built with ICU
has. A server without it would let this migration pass, then answer 500 to every search: the
migration refuses it first, saying what the server lacks (docs/exploitation/postgresql-fourni.md,
#742).
"""

from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.engine import Connection

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The collation the search lowers a text in (``waterfall.platform.database.EVERY_LETTER``, copied:
# a migration never follows the code).
COLLATION = "und-x-icu"


class CollationMissingError(RuntimeError):
    """The server has no ICU collation the search needs."""


def require_collation(connection: Connection, name: str = COLLATION) -> None:
    """Fail, saying what to install, when the server does not know the collation ``name``."""
    found = connection.execute(
        sa.text("SELECT 1 FROM pg_collation WHERE collname = :name"), {"name": name}
    ).first()
    if found is None:
        message = (
            f"the collation {name!r} is not in pg_collation: this PostgreSQL was built without ICU. "
            "The search of Waterfall lowers a text in it, and would answer 500 to every request. "
            "Use a PostgreSQL built with ICU, as the official image is "
            "(docs/exploitation/postgresql-fourni.md)."
        )
        raise CollationMissingError(message)

GRANT = """
DO $$
DECLARE
    service text := current_database() || '_service';
BEGIN
    EXECUTE format('GRANT SELECT ON permission TO %I', service);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE ON access_role TO %I', service);
    EXECUTE format(
        'GRANT SELECT, INSERT, DELETE ON access_role_permission, user_access_role TO %I', service
    );
END
$$
"""


def _audited() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    ]


def upgrade() -> None:
    """Create the four tables and the extension, and grant the service what it needs."""
    require_collation(op.get_bind())
    op.execute("CREATE EXTENSION unaccent")
    op.create_table(
        "permission",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("fbs_code", sa.Text(), nullable=True),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("position"),
        sa.CheckConstraint(
            "kind IN ('function_read', 'function_write', 'irreversible', 'structuring')",
            name="kind_known",
        ),
        sa.CheckConstraint(
            "(fbs_code IS NULL) = (kind IN ('irreversible', 'structuring'))",
            name="fbs_code_of_a_function",
        ),
        sa.CheckConstraint("fbs_code ~ '^FBS-[0-9]+\\.[0-9]+$'", name="fbs_code_form"),
        sa.CheckConstraint("position >= 0", name="position_not_negative"),
    )
    op.create_table(
        "access_role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(collation="C"), nullable=False),
        sa.Column("is_predefined", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_version", sa.Integer(), server_default="0", nullable=False),
        *_audited(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("char_length(label) BETWEEN 1 AND 100", name="label_length"),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    )
    op.create_table(
        "access_role_permission",
        sa.Column("access_role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("access_role_id", "permission_id"),
        sa.ForeignKeyConstraint(["access_role_id"], ["access_role.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"], ondelete="RESTRICT"),
    )
    op.create_table(
        "user_access_role",
        sa.Column("user_account_id", sa.Uuid(), nullable=False),
        sa.Column("access_role_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("user_account_id", "access_role_id"),
        sa.ForeignKeyConstraint(["user_account_id"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["access_role_id"], ["access_role.id"], ondelete="RESTRICT"),
    )
    op.create_index(None, "user_access_role", ["access_role_id"])
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the four tables and the extension: every role is lost with them."""
    op.drop_table("user_access_role")
    op.drop_table("access_role_permission")
    op.drop_table("access_role")
    op.drop_table("permission")
    op.execute("DROP EXTENSION unaccent")
