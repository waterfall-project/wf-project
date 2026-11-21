# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the backups turns when a backup is verified, and spares the one that is marked.

The rotation (``waterfall.core.backups.interface.rotate``) deletes the oldest backups not marked
beyond the retention of the schedule, manual and scheduled counted together (WF-ADM-0170,
US-2910/L2); the worker runs it once a backup is verified, and removes the archives of those it
deleted once its transaction is committed. The rotation itself is tried on rows written around the
worker; the task, on an installation of its own, with real dumps.
"""

from typing import TYPE_CHECKING

import pytest
from backup_rows import Row, days, listed, recorded
from installations import Installation, Take, taker
from sqlalchemy import select, update

from waterfall.core.backups.interface import (
    ScheduleWriting,
    judged_schedule,
    read_backup_schedule,
    rotate,
    write_backup_schedule,
)
from waterfall.core.backups.tables import Backup
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import backup as backup_module
from waterfall.worker.backup import BackupTask

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.queue import TaskQueue

pytestmark = pytest.mark.story("US-2910")


def rotated(database: Database, retained_count: int) -> list[str]:
    """Run the rotation under a retention, in a transaction of its own; give the keys it deleted."""
    with database.transaction() as session:
        return rotate(session, retained_count)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_with_a_retention_of_seven_the_eighth_backup_deletes_the_oldest_one_not_marked(
    database: Database,
) -> None:
    # « Avec une rétention de sept, la huitième supprime la plus ancienne non marquée. » : manual
    # and scheduled backups are counted together, whichever kind the oldest is.
    kinds = ("manual", "scheduled", "scheduled", "manual", "scheduled", "scheduled", "manual")
    made = [
        recorded(database, days(1 + day), Row(origin=kind, key=f"day-{day}.tar"))
        for day, kind in enumerate(kinds)
    ]
    assert rotated(database, 7) == []
    assert listed(database) == made
    eighth = recorded(database, days(8), Row(origin="scheduled", key="day-7.tar"))
    assert rotated(database, 7) == ["day-0.tar"]
    assert listed(database) == [*made[1:], eighth]


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_marked_backup_survives_the_rotation_and_is_not_counted_in_the_retention(
    database: Database,
) -> None:
    # « Une sauvegarde marquée survit à la rotation. » : the oldest is marked, and neither deleted
    # nor counted: seven others are kept beside it, the eighth of them deleting the oldest of them.
    marked = recorded(database, days(1), Row(is_retained=True, key="marked.tar"))
    others = [recorded(database, days(2 + day), Row(key=f"day-{day}.tar")) for day in range(7)]
    assert rotated(database, 7) == []
    assert listed(database) == [marked, *others]
    ninth = recorded(database, days(9), Row(key="day-7.tar"))
    assert rotated(database, 7) == ["day-0.tar"]
    assert listed(database) == [marked, *others[1:], ninth]


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_marked_backup_is_never_deleted_even_when_the_retention_is_the_smallest(
    database: Database,
) -> None:
    marked = recorded(database, days(1), Row(is_retained=True, key="marked.tar"))
    recorded(database, days(2), Row(key="second.tar"))
    latest = recorded(database, days(3), Row(key="third.tar"))
    assert rotated(database, 1) == ["second.tar"]
    assert listed(database) == [marked, latest]


def set_retention(database: Database, retained_count: int) -> None:
    """Write the schedule of the backups with a retention, daily at 01:00, without a copy."""
    writing = ScheduleWriting(
        is_enabled=True,
        frequency="daily",
        at_time="01:00",
        weekday=None,
        retained_count=retained_count,
        external_copy=None,
    )
    with database.transaction() as session:
        held = read_backup_schedule(session).lock_version
        write_backup_schedule(session, judged_schedule(writing, set()), held, Act(None, utc_now()))


def archive_of(task_id: UUID) -> str:
    """Give the key the worker stores the archive of a backup under."""
    return f"backup-{task_id}.tar"


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_verified_turns_the_list_and_its_deleted_archive_leaves_the_bucket(
    installation: Installation, take: Take
) -> None:
    # The worker takes a backup, verifies it, then rotates under the retention of the schedule: with
    # one kept, the second backup deletes the first, its archive with it once the task is committed.
    set_retention(installation.database, 1)
    first = take()
    assert installation.bucket.size(archive_of(first)) is not None
    second = take()
    with installation.database.transaction() as session:
        assert list(session.scalars(select(Backup.task_id))) == [second]
    assert installation.bucket.size(archive_of(first)) is None
    assert installation.bucket.size(archive_of(second)) is not None


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_marked_to_keep_is_still_listed_after_the_backups_that_follow_it(
    installation: Installation, take: Take
) -> None:
    set_retention(installation.database, 1)
    marked = take()
    with installation.database.transaction() as session:
        session.execute(update(Backup).values(is_retained=True))
    take()
    last = take()
    with installation.database.transaction() as session:
        kept = set(session.scalars(select(Backup.task_id)))
    assert kept == {marked, last}
    assert installation.bucket.size(archive_of(marked)) is not None


class Corrupting(Bucket):
    """A bucket that gives back every object with bytes of its middle overwritten."""

    def download(self, key: str, path: Path) -> None:
        super().download(key, path)
        damaged = bytearray(path.read_bytes())
        middle = len(damaged) // 2
        damaged[middle : middle + 16] = b"\xff" * 16
        path.write_bytes(bytes(damaged))


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_that_failed_its_verification_does_not_turn_the_list(
    installation: Installation, queue: TaskQueue
) -> None:
    # « Vérifiée, une sauvegarde fait tourner la liste » : one that did not pass fails its task, is
    # listed and deletes nothing, so that a damaged archive never costs a good one.
    set_retention(installation.database, 1)
    first = taker(installation, queue)()
    corrupting = Corrupting(installation.bucket.client, installation.bucket.name)
    second = taker(installation, queue, BackupTask(installation.backup, corrupting))()
    with installation.database.transaction() as session:
        verifications = list(session.scalars(select(Backup.verification).order_by(Backup.taken_at)))
        assert session.get_one(BackgroundTask, second).status == "failed"
    assert verifications == ["passed", "failed"]
    assert installation.bucket.size(archive_of(first)) is not None
    assert installation.bucket.size(archive_of(second)) is not None


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_task_that_fails_after_the_rotation_keeps_the_list_and_the_archives(
    installation: Installation,
    queue: TaskQueue,
    take: Take,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The archives go once the transaction is committed, never before: a task that fails after it
    # has turned the list leaves the rows it deleted, and the archives they name.
    set_retention(installation.database, 1)
    first = take()

    def rotate_then_fail(session: Session, retained_count: int) -> list[str]:
        rotate(session, retained_count)
        message = "the task fails after the rotation"
        raise RuntimeError(message)

    monkeypatch.setattr(backup_module, "rotate", rotate_then_fail)
    failed = taker(installation, queue)()
    with installation.database.transaction() as session:
        assert list(session.scalars(select(Backup.task_id))) == [first]
        assert session.get_one(BackgroundTask, failed).status == "failed"
    assert installation.bucket.size(archive_of(first)) is not None
    assert installation.bucket.size(archive_of(failed)) is None


@pytest.mark.requirement("WF-ADM-0170-A")
def test_seven_failed_backups_newer_than_a_good_one_leave_it_with_a_retention_of_seven(
    database: Database,
) -> None:
    # [US-2910] (#4366): the failed ones are not counted, so that the last restorable backup
    # survives; they go, the oldest first, with no ceiling.
    good = recorded(database, days(1), Row(key="good.tar"))
    for day in range(7):
        recorded(database, days(2 + day), Row(verification="failed", key=f"bad-{day}.tar"))
    assert rotated(database, 7) == [f"bad-{day}.tar" for day in range(7)]
    assert listed(database) == [good]


@pytest.mark.requirement("WF-ADM-0170-A")
def test_the_failed_backups_go_before_any_verified_one_the_oldest_first(
    database: Database,
) -> None:
    # [US-2910]: the failed ones, not marked, are deleted before the verified ones beyond the
    # retention, each kind oldest first, and they do not take a place of the retention.
    oldest = recorded(database, days(1), Row(key="old.tar"))
    recorded(database, days(3), Row(verification="failed", key="bad-late.tar"))
    recorded(database, days(2), Row(verification="failed", key="bad-early.tar"))
    newer = recorded(database, days(4), Row(key="new.tar"))
    latest = recorded(database, days(5), Row(key="latest.tar"))
    assert rotated(database, 2) == ["bad-early.tar", "bad-late.tar", "old.tar"]
    assert listed(database) == [newer, latest]
    assert oldest not in listed(database)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_the_last_verified_backup_is_never_deleted_whatever_the_retention(
    database: Database,
) -> None:
    # [US-2910]: even a retention of zero keeps the latest verified backup, the failed ones going.
    recorded(database, days(1), Row(key="old.tar"))
    latest = recorded(database, days(2), Row(key="latest.tar"))
    recorded(database, days(3), Row(verification="failed", key="bad.tar"))
    assert rotated(database, 0) == ["bad.tar", "old.tar"]
    assert listed(database) == [latest]


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_marked_backup_whose_verification_failed_is_neither_counted_nor_deleted(
    database: Database,
) -> None:
    # [US-2910]: a marked backup is never counted nor deleted, whatever its verification says.
    marked = recorded(
        database, days(1), Row(verification="failed", is_retained=True, key="marked.tar")
    )
    good = recorded(database, days(2), Row(key="good.tar"))
    assert rotated(database, 1) == []
    assert listed(database) == [marked, good]
