# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge deletes the tasks ended for longer than the retention of their result (US-2830).

``0008`` let the role of the service write a task, read it and update it, but delete none. The
task ``purge`` of the worker deletes the tasks ended for longer than the retention of their result,
``background_task_retention_days`` (§4.4.1, WF-DAT-0080), the report of a reading of the accounts
going with its task (``0048``): the role of the service receives ``DELETE`` on ``background_task``,
and loses it again at the downgrade. Only the right changes; no row is written.
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANT = """
DO $$
BEGIN
    EXECUTE format('GRANT DELETE ON background_task TO %I', current_database() || '_service');
END
$$
"""
REVOKE = """
DO $$
BEGIN
    EXECUTE format('REVOKE DELETE ON background_task FROM %I', current_database() || '_service');
END
$$
"""


def upgrade() -> None:
    """Let the role of the service delete the tasks the purge finds past their retention."""
    op.execute(GRANT)


def downgrade() -> None:
    """Take the right back: the service deletes no task again."""
    op.execute(REVOKE)
