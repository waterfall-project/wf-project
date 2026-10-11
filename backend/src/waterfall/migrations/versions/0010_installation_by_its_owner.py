# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The row of the installation is written by the bootstrap alone, as the owner of the tables (#701).

``0002`` granted the role of the service ``INSERT`` on ``installation``, supposing the bootstrap
would write its row as the service. It writes it as the owner, who applies the migrations
(``waterfall-api install``, US-0420): the API and the worker read the row and change its settings,
and never insert one. The code before this migration does not insert it either.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVOKE = """
DO $$
BEGIN
    EXECUTE format('REVOKE INSERT ON installation FROM %I', current_database() || '_service');
END
$$
"""

GRANT = """
DO $$
BEGIN
    EXECUTE format('GRANT INSERT ON installation TO %I', current_database() || '_service');
END
$$
"""


def upgrade() -> None:
    """Take back from the role of the service the right to insert the row of the installation."""
    op.execute(REVOKE)


def downgrade() -> None:
    """Give it back to the role of the service."""
    op.execute(GRANT)
