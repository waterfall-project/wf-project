# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration, as the platform of production sees it (WF-EXP-0060, US-2930).

An ephemeral platform restores the latest scheduled backup whose verification passed, starts, and
compares what it finds to what the manifest of the backup says; the platform of production gives it
that backup, then inscribes its outcome, one row per test, as the role of the service, which may
read the backups and add a test, nothing more (migration 0050). The status screen reads the latest
test here, which a test that did not take place lets age (#4643).
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select

from waterfall.core.backups.tables import RESTORE_TEST_FAILURE_LENGTH, Backup, RestoreTest
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

# How old the latest test may be before the monthly test is said missed: a month, and the days a
# test planned on a day of the month may come late (WF-EXP-0060, #4643).
RESTORE_TEST_PERIOD = timedelta(days=35)
# What holds back the test the schedule deposits: no backup to restore.
NO_BACKUP_TO_TEST = "scheduled_backup_verified"


@dataclass(frozen=True, slots=True)
class BackupToTest:
    """The backup a test restores: which, of when, and the key of its archive."""

    backup_id: UUID
    taken_at: datetime
    object_key: str


@dataclass(frozen=True, slots=True)
class RestoreCounts:
    """What a test counted in the platform it restored (WF-EXP-0060)."""

    projects: int
    marked_revisions: int
    cost_lines: int
    identity_accounts: int


@dataclass(frozen=True, slots=True)
class RestoreTestOutcome:
    """A test ended: when, on which backup, what it counted, and why it failed.

    ``counts`` is ``None`` when it did not get to count, ``failure`` when it succeeded.
    """

    started_at: datetime
    finished_at: datetime
    backup: BackupToTest
    counts: RestoreCounts | None
    failure: str | None


def backup_to_test(session: Session) -> BackupToTest | None:
    """Give the latest scheduled backup whose verification passed, or ``None`` if there is none.

    A manual backup is not the one the schedule keeps, and one that failed its verification cannot
    be restored (WF-ADM-0170, #4230).
    """
    latest = session.execute(
        select(Backup.id, Backup.taken_at, Backup.object_key)
        .where(Backup.origin == "scheduled", Backup.verification == "passed")
        .order_by(Backup.taken_at.desc(), Backup.id.desc())
        .limit(1)
    ).first()
    return None if latest is None else BackupToTest(latest.id, latest.taken_at, latest.object_key)


def record_restore_test(session: Session, outcome: RestoreTestOutcome) -> UUID:
    """Inscribe the outcome of a test; give its identifier.

    A reason longer than the column admits is cut, its end marked: the test has failed all the same.
    """
    test_id = new_id()
    failure = outcome.failure
    if failure is not None and len(failure) > RESTORE_TEST_FAILURE_LENGTH:
        failure = failure[: RESTORE_TEST_FAILURE_LENGTH - 1] + "…"
    counts = outcome.counts
    session.execute(
        insert(RestoreTest).values(
            id=test_id,
            started_at=outcome.started_at,
            finished_at=outcome.finished_at,
            backup_id=outcome.backup.backup_id,
            backup_taken_at=outcome.backup.taken_at,
            succeeded=failure is None,
            projects=None if counts is None else counts.projects,
            marked_revisions=None if counts is None else counts.marked_revisions,
            cost_lines=None if counts is None else counts.cost_lines,
            identity_accounts=None if counts is None else counts.identity_accounts,
            failure=failure,
        )
    )
    return test_id


def restore_test_lacks(session: Session) -> list[str]:
    """Say what holds back a test: a scheduled backup whose verification passed, if there is none.

    A test without a backup to restore would inscribe nothing (``waterfall.restore.trial``).
    """
    return [] if backup_to_test(session) is not None else [NO_BACKUP_TO_TEST]


@dataclass(frozen=True, slots=True)
class RestoreTestResult:
    """What the status screen says of the tests: when the latest ended, and whether it succeeded.

    The latest older than the period, ``at`` is the end of that period, by which the next test was
    due, and the result a failure: the test that was due did not take place.
    """

    at: datetime
    succeeded: bool


def latest_restore_test(session: Session, now: datetime) -> RestoreTestResult | None:
    """Give the result of the latest test at ``now``, or ``None`` if none was due yet.

    A test that did not take place — no backup to test, its Job never made or never started, the
    production out of reach — inscribes nothing: the latest one, older than ``RESTORE_TEST_PERIOD``,
    says the monthly test missed rather than a success of long ago (WF-EXP-0060, #4643). Before any
    test, the first was due a period after the oldest scheduled backup verified, which it could have
    restored: past that, it is said missed as well; before, or without such a backup, nothing is.
    """
    latest = session.execute(
        select(RestoreTest.finished_at, RestoreTest.succeeded)
        .order_by(RestoreTest.finished_at.desc(), RestoreTest.id.desc())
        .limit(1)
    ).first()
    if latest is None:
        return first_test_missed(session, now)
    due = latest.finished_at + RESTORE_TEST_PERIOD
    if now >= due:
        return RestoreTestResult(due, succeeded=False)
    return RestoreTestResult(latest.finished_at, succeeded=latest.succeeded)


def first_test_missed(session: Session, now: datetime) -> RestoreTestResult | None:
    """Say the first test missed once a period has passed since a backup could be tested, else none.

    No test inscribed, the first was due ``RESTORE_TEST_PERIOD`` after the oldest scheduled backup
    whose verification passed (#4643).
    """
    oldest = session.scalar(
        select(func.min(Backup.taken_at)).where(
            Backup.origin == "scheduled", Backup.verification == "passed"
        )
    )
    if oldest is None or now < oldest + RESTORE_TEST_PERIOD:
        return None
    return RestoreTestResult(oldest + RESTORE_TEST_PERIOD, succeeded=False)
