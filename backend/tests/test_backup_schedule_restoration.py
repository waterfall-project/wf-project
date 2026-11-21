# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A restoration keeps the schedule of the backups, as it keeps the list it governs (#1743).

The installation of the test (``installations``) is backed up under one schedule, then given
another, then restored: the schedule read after is the one set before the restoration — its
retention and its external copy included —, not the backup's, so that a retention the backup held
smaller deletes nothing more of the list kept. The periodicity of the reading of the accounts is
not kept: the specification names it not among what a restoration keeps (WF-ADM-0160).
"""

from datetime import time
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from access_rows import account, role
from backup_rows import Row, days, listed, recorded
from installations import Installation, Take, restore
from realm import KEY, TestRealm
from sqlalchemy import select, update
from support import ContractClient, bearer

from waterfall.core.backups.interface import (
    ExternalCopy,
    ScheduleWriting,
    judged_schedule,
    read_backup_schedule,
    write_backup_schedule,
)
from waterfall.core.backups.tables import BackupSchedule
from waterfall.core.users.tables import IdentitySyncSchedule
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, create_database_engine, utc_now

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

LYON = "secours-lyon"


def set_schedule(
    database: Database, retained_count: int, copy: ExternalCopy | None, author: UUID | None
) -> None:
    """Write a daily schedule at 01:00, a retention and a copy, by an author, under its counter."""
    writing = ScheduleWriting(
        is_enabled=True,
        frequency="daily",
        at_time="01:00",
        weekday=None,
        retained_count=retained_count,
        external_copy=copy,
    )
    with database.transaction() as session:
        held = read_backup_schedule(session).lock_version
        schedule = judged_schedule(writing, {LYON})
        write_backup_schedule(session, schedule, held, Act(author, utc_now()))


@pytest.mark.story("US-2910")
def test_the_schedule_set_before_a_restoration_is_read_after_it_and_not_the_backups(
    installation: Installation,
    take: Take,
    installation_api: ContractClient,
    realm: TestRealm,
    tmp_path: Path,
) -> None:
    # The backup holds three kept and no copy; fourteen kept and a copy are set after it, by an
    # account the backup does not hold. The restoration writes back the fourteen and the copy, its
    # author named no more — his account is not in the restored database —, and the periodicity of
    # the reading of the accounts the backup held.
    subject = f"subject-{uuid4()}"
    reading = role(installation.database, "Sauvegardes", permissions=("backups.read",))
    account(installation.database, "Martin", "Claire", roles=(reading,), idp_subject=subject)
    set_schedule(installation.database, 3, None, None)
    backup_task = take()
    author = account(installation.database, "Durand", "Paul")
    copy = ExternalCopy(
        is_enabled=True, location=LYON, path="waterfall/sauvegardes", retained_count=30
    )
    set_schedule(installation.database, 14, copy, author)
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        connection.execute(update(IdentitySyncSchedule).values(at_time=time(4, 0)))
    restore(installation, backup_task, tmp_path)
    read = installation_api.get(
        "/api/v1/backup-schedule", headers=bearer(realm.token(subject, KEY))
    )
    assert read.status_code == 200
    assert read.json() == {
        "is_enabled": True,
        "frequency": "daily",
        "at_time": "01:00",
        "weekday": None,
        "retained_count": 14,
        "external_copy": {
            "is_enabled": True,
            "location": LYON,
            "path": "waterfall/sauvegardes",
            "retained_count": 30,
        },
        "lock_version": 3,
    }
    with owner.connect() as connection:
        authors = connection.execute(
            select(BackupSchedule.created_by, BackupSchedule.updated_by)
        ).one()
        reading_at = connection.scalar(select(IdentitySyncSchedule.at_time))
    owner.dispose()
    assert tuple(authors) == (None, None)
    assert reading_at == time(1, 30)


@pytest.mark.story("US-2910")
def test_the_rotation_after_a_restoration_deletes_nothing_more_than_without_it(
    installation: Installation, take: Take, tmp_path: Path
) -> None:
    # #1743: the backup holds a retention of two, the installation fourteen when it is restored;
    # the list kept holds five backups besides the one restored. The schedule written back is the
    # one of before the restoration, so that the rotation the next backup runs deletes nothing,
    # as it would not have without it; the retention of the backup, two, would delete four.
    set_schedule(installation.database, 2, None, None)
    backup_task = take()
    others = [recorded(installation.database, days(day), Row()) for day in range(1, 6)]
    set_schedule(installation.database, 14, None, None)
    restore(installation, backup_task, tmp_path)
    with installation.database.transaction() as session:
        assert read_backup_schedule(session).schedule.retained_count == 14
    assert len(listed(installation.database)) == 1 + len(others)
    take()
    assert len(listed(installation.database)) == 2 + len(others)
