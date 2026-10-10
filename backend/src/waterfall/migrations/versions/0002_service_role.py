# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The role of the service: what the API and the worker may do in the database, and no more.

The migrations run as the owner of the tables; the API and the worker connect as
``waterfall_service``, which owns nothing and holds only what each table grants it. A table
grants it ``SELECT``, ``INSERT``, ``UPDATE`` and ``DELETE`` in the migration that creates it;
the journal of audit, ``INSERT`` and ``SELECT`` alone (WF-SEC-0030, migration ``0003``). The role
is created without the right to sign in when the server does not have it yet — the deployment
gives it its password — and it is shared by the databases of the server, so no descent drops it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Two migrations of two databases of one server may race to create the role: the second finds it.
CREATE_ROLE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'waterfall_service') THEN
        BEGIN
            CREATE ROLE waterfall_service NOLOGIN;
        EXCEPTION WHEN duplicate_object OR unique_violation THEN
            NULL;
        END;
    END IF;
END
$$
"""


def upgrade() -> None:
    """Create the role if the server lacks it, and grant it the two tables that exist."""
    op.execute(CREATE_ROLE)
    op.execute("GRANT USAGE ON SCHEMA public TO waterfall_service")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON installation, user_account TO waterfall_service"
    )


def downgrade() -> None:
    """Take back what the role was granted; the role stays, other databases may grant it."""
    op.execute(
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON installation, user_account FROM waterfall_service"
    )
    op.execute("REVOKE USAGE ON SCHEMA public FROM waterfall_service")
