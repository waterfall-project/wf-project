# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The role of the service: what the API and the worker may do in the database, and no more.

The migrations run as the owner of the tables; the API and the worker connect as the role of the
service, which owns nothing and holds only what each table grants it: ``SELECT``, ``INSERT``
and ``UPDATE`` on the two tables that exist, granted here — no ``DELETE``: the installation keeps
its row and an account is never deleted (WF-DAT-0080) —; on the journal of audit, ``INSERT`` and
``SELECT`` alone (WF-SEC-0030, migration ``0003``). A role is global to the
server, its rights are granted database by database: it is named after the database,
``<database>_service`` — ``waterfall_service`` for the database ``waterfall`` —, so that two
installations of one server share neither its password nor its rights. It is created without
the right to sign in when the server does not have it yet — the deployment gives it its
password —, and no descent drops it, so that a descent then an ascent keep that password.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The role of this database: an identifier too long for PostgreSQL, which would cut it, is refused
# rather than shared with another database whose name begins the same. Two runs that race to
# create it find it, the second one.
GRANT = """
DO $$
DECLARE
    service text := current_database() || '_service';
BEGIN
    IF octet_length(service) > 63 THEN
        RAISE EXCEPTION 'the role of the service, %, is longer than an identifier', service;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = service) THEN
        BEGIN
            EXECUTE format('CREATE ROLE %I NOLOGIN', service);
        EXCEPTION WHEN duplicate_object OR unique_violation THEN
            NULL;
        END;
    END IF;
    EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', service);
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE ON installation, user_account TO %I', service
    );
END
$$
"""

REVOKE = """
DO $$
DECLARE
    service text := current_database() || '_service';
BEGIN
    EXECUTE format(
        'REVOKE SELECT, INSERT, UPDATE ON installation, user_account FROM %I', service
    );
    EXECUTE format('REVOKE USAGE ON SCHEMA public FROM %I', service);
END
$$
"""


def upgrade() -> None:
    """Create the role of the database if the server lacks it, and grant it the two tables."""
    op.execute(GRANT)


def downgrade() -> None:
    """Take back what the role was granted; the role stays, with its password."""
    op.execute(REVOKE)
