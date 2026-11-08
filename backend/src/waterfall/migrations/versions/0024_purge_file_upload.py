# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge deletes the deposits expired (WF-DAT-0120-A; EP-06, "La purge").

``0017`` let the role of the service record a deposit, read it and complete it, but delete none.
``waterfall-worker purge`` deletes the rows of the deposits whose term has passed, those of EP-03
by parts included: the role of the service receives ``DELETE`` on ``file_upload``, and loses it
again at the downgrade. Only the right changes; no row is written.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANT = """
DO $$
BEGIN
    EXECUTE format('GRANT DELETE ON file_upload TO %I', current_database() || '_service');
END
$$
"""
REVOKE = """
DO $$
BEGIN
    EXECUTE format('REVOKE DELETE ON file_upload FROM %I', current_database() || '_service');
END
$$
"""


def upgrade() -> None:
    """Let the role of the service delete the deposits the purge finds expired."""
    op.execute(GRANT)


def downgrade() -> None:
    """Take the right back: the service deletes no deposit again."""
    op.execute(REVOKE)
