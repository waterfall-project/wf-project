# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The two schedules at their shipped values, by the platform (EP-13, US-2910, US-3040).

A new installation backs itself up every day without any schedule having been entered — enabled,
daily, at ``01:00`` UTC, seven kept, without external copy (WF-ADM-0170, WF-EXP-0050) — and reads
the accounts of the identity provider every day at ``01:30`` UTC, half an hour after
(`IdentitySyncSchedule`). Each row is written once, its counter at 1, as a created object's
(`LockVersion`), its author the platform; a row already there is left as it is.

A restoration of a backup taken before ``0037`` applies it again on the restored database, and
then writes back the schedule of the backups it kept (#1743).
"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BACKUPS = """
INSERT INTO backup_schedule (
    id, is_enabled, frequency, at_time, weekday, retained_count,
    lock_version, created_at, created_by, updated_at, updated_by
) VALUES (1, true, 'daily', '01:00', NULL, 7, 1, now(), NULL, now(), NULL)
ON CONFLICT (id) DO NOTHING
"""
ACCOUNTS = """
INSERT INTO identity_sync_schedule (
    id, is_enabled, frequency, at_time, weekday,
    lock_version, created_at, created_by, updated_at, updated_by
) VALUES (1, true, 'daily', '01:30', NULL, 1, now(), NULL, now(), NULL)
ON CONFLICT (id) DO NOTHING
"""


def upgrade() -> None:
    """Write each schedule at its shipped values, where it has none."""
    op.execute(BACKUPS)
    op.execute(ACCOUNTS)


def downgrade() -> None:
    """Delete both rows: the schedules set are lost, and ``0037`` drops their tables after."""
    op.execute("DELETE FROM identity_sync_schedule")
    op.execute("DELETE FROM backup_schedule")
