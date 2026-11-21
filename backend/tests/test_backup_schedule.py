# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule of the backups is read and written as the contract says, refusals included.

``getBackupSchedule`` and ``setBackupSchedule`` (US-2910): the shipped schedule a new installation
reads, a writing judged whole (422), refused while a restoration is queued or running (409,
``no_restore_running``, #1743), and written under its counter (412). Each person is an account
written around the service, with the roles a test gives it; every answer is checked against the
contract (``ContractClient``). The application of these tests declares no external location: a
copy that names one is refused as unknown, and the rule is tried apart with locations declared; the
copy set by the route on an installation that declares its locations is
``test_external_backup_locations.py``'s (US-2910/L3).
"""

import threading
from collections.abc import Callable
from datetime import time
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from advisory_locks import waits_for
from installations import written_task
from realm import KEY, TestRealm
from sqlalchemy import func, select, update
from support import ContractClient, bearer

from waterfall.core.backups.interface import (
    ExternalCopy,
    ScheduleWriting,
    judged_schedule,
    read_backup_schedule,
    write_backup_schedule,
)
from waterfall.core.backups.tables import BackupSchedule
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.locks import RESTORE_LOCK
from waterfall.platform.tasks import BackgroundTask

pytestmark = pytest.mark.story("US-2910")

SCHEDULE = "/api/v1/backup-schedule"
READ = "backups.read"
WRITE = "backups.write"
LYON = "secours-lyon"
SHIPPED = {
    "is_enabled": True,
    "frequency": "daily",
    "at_time": "01:00",
    "weekday": None,
    "retained_count": 7,
    "lock_version": 1,
}
WEEKLY = {
    "is_enabled": True,
    "frequency": "weekly",
    "at_time": "02:30",
    "weekday": 7,
    "retained_count": 4,
    "lock_version": 1,
}
QUEUED_WITHIN = 10.0
COPY = {"is_enabled": True, "location": LYON, "path": "waterfall/sauvegardes", "retained_count": 30}

type Person = Callable[..., tuple[UUID, dict[str, str]]]


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each holding a role of the permissions given, and its header."""

    def make(*permissions: str) -> tuple[UUID, dict[str, str]]:
        subject = f"subject-{uuid4()}"
        held = role(database, f"Rôle {uuid4().hex[:8]}", permissions=permissions)
        user_id = account(database, "Martin", uuid4().hex[:8], roles=(held,), idp_subject=subject)
        return user_id, bearer(realm.token(subject, KEY))

    return make


def fields(response: Any) -> list[tuple[str, str, dict[str, Any]]]:
    """Give, of a refusal, each field refused: where, why, and the parameters of the reason."""
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_FAILED"
    return [
        (each["pointer"], each["code"], each.get("params", {}))
        for each in response.json()["fields"]
    ]


def schedule_row(database: Database) -> dict[str, Any]:
    """Read the row of the schedule as it is written."""
    with database.transaction() as session:
        row = session.get_one(BackupSchedule, 1)
        return {
            column.name: getattr(row, column.name) for column in BackupSchedule.__table__.columns
        }


def written(**changes: Any) -> ScheduleWriting:
    """Give a writing of the shipped schedule, with the changes a test asks for."""
    values: dict[str, Any] = {
        "is_enabled": True,
        "frequency": "daily",
        "at_time": "01:00",
        "weekday": None,
        "retained_count": 7,
        "external_copy": None,
    } | changes
    return ScheduleWriting(**values)


def test_a_new_installation_reads_the_shipped_schedule_without_any_entered(
    api: ContractClient, person: Person
) -> None:
    # Enabled, daily at 01:00 UTC, seven kept, without external copy; created at 1, by the platform.
    _, headers = person(READ)
    response = api.get(SCHEDULE, headers=headers)
    assert response.status_code == 200
    assert response.json() == SHIPPED


def test_a_schedule_set_is_read_back_by_its_author_its_counter_advanced(
    api: ContractClient, database: Database, person: Person
) -> None:
    user_id, headers = person(READ, WRITE)
    response = api.put(SCHEDULE, headers=headers, json=WEEKLY)
    assert response.status_code == 200
    assert response.json() == WEEKLY | {"lock_version": 2}
    assert api.get(SCHEDULE, headers=headers).json() == WEEKLY | {"lock_version": 2}
    row = schedule_row(database)
    assert (row["at_time"], row["weekday"], row["updated_by"]) == (time(2, 30), 7, user_id)
    assert row["created_by"] is None


def test_a_schedule_saved_without_its_copy_removes_the_copy_set(
    api: ContractClient, database: Database, person: Person
) -> None:
    # The copy set by a writing that knew the location, read back whole; a writing without it then
    # removes it (`BackupSchedule.external_copy`).
    _, headers = person(READ, WRITE)
    copy = ExternalCopy(
        is_enabled=True, location=LYON, path="waterfall/sauvegardes", retained_count=30
    )
    with database.transaction() as session:
        schedule = judged_schedule(written(external_copy=copy), {LYON})
        write_backup_schedule(session, schedule, 1, Act(None, utc_now()))
    assert api.get(SCHEDULE, headers=headers).json() == SHIPPED | {
        "external_copy": COPY,
        "lock_version": 2,
    }
    response = api.put(SCHEDULE, headers=headers, json=SHIPPED | {"lock_version": 2})
    assert response.status_code == 200
    assert response.json() == SHIPPED | {"lock_version": 3}
    row = schedule_row(database)
    copied = ("is_enabled", "location", "path", "retained_count")
    assert all(row[f"external_copy_{name}"] is None for name in copied)


type Refused = list[tuple[str, str, dict[str, Any]]]

# A body in default, as changes to the shipped schedule, and the fields its refusal names.
REFUSALS: list[tuple[dict[str, Any], Refused]] = [
    ({"at_time": "25:00"}, [("/at_time", "VALIDATION_FAILED", {})]),
    ({"at_time": "1:00"}, [("/at_time", "VALIDATION_FAILED", {})]),
    ({"frequency": "weekly"}, [("/weekday", "VALUE_REQUIRED", {})]),
    (
        {"frequency": "weekly", "weekday": 0},
        [("/weekday", "VALUE_OUT_OF_RANGE", {"minimum": 1})],
    ),
    (
        {"frequency": "weekly", "weekday": 8},
        [("/weekday", "VALUE_OUT_OF_RANGE", {"maximum": 7})],
    ),
    ({"weekday": 3}, [("/weekday", "VALIDATION_FAILED", {})]),
    ({"retained_count": 366}, [("/retained_count", "VALUE_OUT_OF_RANGE", {"maximum": 365})]),
    (
        {"retained_count": 0, "external_copy": COPY | {"retained_count": 400}},
        [
            ("/retained_count", "VALUE_OUT_OF_RANGE", {"minimum": 1}),
            ("/external_copy/location", "UNKNOWN_EXTERNAL_BACKUP_LOCATION", {"location": LYON}),
            ("/external_copy/retained_count", "VALUE_OUT_OF_RANGE", {"maximum": 365}),
        ],
    ),
    (
        {"external_copy": COPY | {"location": "Secours", "path": "../sauvegardes"}},
        [
            ("/external_copy/location", "VALIDATION_FAILED", {}),
            ("/external_copy/path", "PATH_INVALID", {}),
        ],
    ),
    (
        {"external_copy": COPY | {"retained_count": 3, "path": ""}},
        [
            ("/external_copy/location", "UNKNOWN_EXTERNAL_BACKUP_LOCATION", {"location": LYON}),
            ("/external_copy/path", "VALUE_REQUIRED", {}),
            ("/external_copy/retained_count", "VALUE_OUT_OF_RANGE", {"minimum": 7}),
        ],
    ),
    ({"external_copy": None}, [("/external_copy", "VALIDATION_FAILED", {})]),
    ({"frequency": "monthly"}, [("/frequency", "VALIDATION_FAILED", {})]),
]


@pytest.mark.parametrize(
    ("sent", "refused"),
    REFUSALS,
    ids=[
        "hour",
        "hour-unpadded",
        "weekly-without-day",
        "day-below",
        "day-beyond",
        "daily-with-day",
        "retention-beyond",
        "retentions-out-of-range",
        "location-and-path-malformed",
        "copy-too-short",
        "copy-null",
        "frequency",
    ],
)
def test_a_schedule_in_default_is_refused_each_field_named_and_nothing_is_written(
    api: ContractClient,
    database: Database,
    person: Person,
    sent: dict[str, Any],
    refused: Refused,
) -> None:
    # Every field in default at once, in the order of the body; the counter as it was.
    _, headers = person(READ, WRITE)
    before = schedule_row(database)
    assert fields(api.put(SCHEDULE, headers=headers, json=SHIPPED | sent)) == refused
    assert schedule_row(database) == before


def test_a_field_missing_is_required(api: ContractClient, person: Person) -> None:
    _, headers = person(WRITE)
    sent = {name: value for name, value in SHIPPED.items() if name != "weekday"}
    assert fields(api.put(SCHEDULE, headers=headers, json=sent)) == [
        ("/weekday", "VALUE_REQUIRED", {})
    ]


@pytest.mark.parametrize("status", ["queued", "running"])
def test_a_schedule_set_while_a_restoration_runs_is_refused_and_nothing_is_written(
    api: ContractClient, database: Database, person: Person, status: str
) -> None:
    # #1743: the restoration reads the schedule back before it replaces the databases and writes
    # it after; a setting made meanwhile would be lost. Once it has ended, the setting is taken.
    _, headers = person(READ, WRITE)
    restoration = written_task(database, "restore", status)
    before = schedule_row(database)
    response = api.put(SCHEDULE, headers=headers, json=WEEKLY)
    assert response.status_code == 409
    assert response.json()["code"] == "STATE_FORBIDS_OPERATION"
    assert response.json()["params"] == {"missing_condition": "no_restore_running"}
    assert schedule_row(database) == before
    with database.transaction() as session:
        ended = {"status": "succeeded", "progress": 100, "finished_at": utc_now()}
        session.execute(
            update(BackgroundTask).where(BackgroundTask.id == restoration).values(**ended)
        )
    assert api.put(SCHEDULE, headers=headers, json=WEEKLY).status_code == 200


def test_a_schedule_set_waits_for_a_restoration_being_deposited_and_then_sees_it(
    api: ContractClient, database: Database, person: Person
) -> None:
    # startRestore deposits its task under the lock RESTORE_LOCK. A setting that arrives meanwhile
    # waits for it (shared lock), then sees the task committed and is refused; without the lock it
    # would read no restoration and write.
    _, headers = person(READ, WRITE)
    before = schedule_row(database)
    answers: list[Any] = []
    caller = threading.Thread(
        target=lambda: answers.append(api.put(SCHEDULE, headers=headers, json=WEEKLY))
    )
    with database.transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(RESTORE_LOCK)))
        caller.start()
        queued = waits_for(database, RESTORE_LOCK)
        written_task(database, "restore", "queued")
    caller.join(QUEUED_WITHIN)
    assert queued
    assert not caller.is_alive()
    (response,) = answers
    assert response.status_code == 409
    assert response.json()["params"] == {"missing_condition": "no_restore_running"}
    assert schedule_row(database) == before


def test_a_schedule_set_on_a_stale_counter_is_refused_and_nothing_is_written(
    api: ContractClient, database: Database, person: Person
) -> None:
    _, headers = person(READ, WRITE)
    assert api.put(SCHEDULE, headers=headers, json=WEEKLY).status_code == 200
    before = schedule_row(database)
    response = api.put(SCHEDULE, headers=headers, json=SHIPPED)
    assert response.status_code == 412
    assert response.json()["code"] == "STALE_LOCK_VERSION"
    assert response.json()["params"] == {"expected_lock_version": 2}
    assert schedule_row(database) == before


def test_the_schedule_is_read_and_written_only_under_the_permissions_of_the_backups(
    api: ContractClient, database: Database, person: Person
) -> None:
    # Without the permission to read the backups, the schedule does not exist (404); without the
    # one to change them, the writing is forbidden (403).
    _, nothing = person()
    _, reader = person(READ)
    assert api.get(SCHEDULE, headers=nothing).status_code == 404
    refused = api.put(SCHEDULE, headers=reader, json=WEEKLY)
    assert refused.status_code == 403
    assert refused.json()["params"] == {"missing_permission": WRITE}
    assert schedule_row(database)["lock_version"] == 1


def test_a_copy_to_a_location_declared_keeps_at_least_the_retention_of_the_platform() -> None:
    # WF-EXP-0050: as many copies as the platform keeps backups pass; one fewer is refused with the
    # platform's retention as its minimum.
    copy = ExternalCopy(is_enabled=False, location=LYON, path="waterfall", retained_count=14)
    judged = judged_schedule(written(retained_count=14, external_copy=copy), {LYON})
    assert (judged.external_copy, judged.at_time) == (copy, time(1, 0))
    short = ExternalCopy(is_enabled=True, location=LYON, path="waterfall", retained_count=13)
    with pytest.raises(UnprocessableError) as raised:
        judged_schedule(written(retained_count=14, external_copy=short), {LYON})
    assert [(each.pointer, each.params) for each in raised.value.fields] == [
        ("/external_copy/retained_count", {"minimum": 14})
    ]


def test_a_path_beyond_its_length_is_too_long() -> None:
    copy = ExternalCopy(is_enabled=True, location=LYON, path="a" * 256, retained_count=7)
    with pytest.raises(UnprocessableError) as raised:
        judged_schedule(written(external_copy=copy), {LYON})
    assert [(each.pointer, each.code, each.params) for each in raised.value.fields] == [
        ("/external_copy/path", "VALUE_TOO_LONG", {"max_length": 255})
    ]


def test_the_schedule_read_is_the_row_the_migrations_wrote(database: Database) -> None:
    with database.transaction() as session:
        view = read_backup_schedule(session)
        authors = session.execute(
            select(BackupSchedule.created_by, BackupSchedule.updated_by)
        ).one()
    assert (view.schedule.frequency, view.schedule.retained_count, view.lock_version) == (
        "daily",
        7,
        1,
    )
    assert tuple(authors) == (None, None)
