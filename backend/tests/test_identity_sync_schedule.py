# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule of the readings of the accounts is read and written as the contract says.

``getIdentitySyncSchedule`` and ``setIdentitySyncSchedule`` (US-3040): the shipped schedule a new
installation reads, a writing judged whole (422), and written under its counter (412). Each person
is an account written around the service, with the roles a test gives it; every answer is checked
against the contract (``ContractClient``).
"""

from collections.abc import Callable
from datetime import time
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from realm import KEY, TestRealm
from sqlalchemy import select
from support import ContractClient, bearer

from waterfall.core.users.interface import (
    SyncScheduleWriting,
    judged_sync_schedule,
    read_sync_schedule,
    write_sync_schedule,
)
from waterfall.core.users.tables import IdentitySyncSchedule
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import UnprocessableError

pytestmark = pytest.mark.story("US-3040")

SCHEDULE = "/api/v1/identity-sync-schedule"
READ = "users.read"
WRITE = "users.write"
SHIPPED = {
    "is_enabled": True,
    "frequency": "daily",
    "at_time": "01:30",
    "weekday": None,
    "lock_version": 1,
}
WEEKLY = {
    "is_enabled": True,
    "frequency": "weekly",
    "at_time": "03:15",
    "weekday": 1,
    "lock_version": 1,
}

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


def written(**changes: Any) -> SyncScheduleWriting:
    """Give a writing of the shipped schedule, with the changes a test asks for."""
    values: dict[str, Any] = {
        "is_enabled": True,
        "frequency": "daily",
        "at_time": "01:30",
        "weekday": None,
    } | changes
    return SyncScheduleWriting(**values)


def schedule_row(database: Database) -> dict[str, Any]:
    """Read the row of the schedule as it is written."""
    with database.transaction() as session:
        row = session.get_one(IdentitySyncSchedule, 1)
        return {
            column.name: getattr(row, column.name)
            for column in IdentitySyncSchedule.__table__.columns
        }


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_new_installation_reads_the_shipped_schedule_without_any_entered(
    api: ContractClient, person: Person
) -> None:
    # Enabled, daily at 01:30 UTC; created at 1, by the platform.
    _, headers = person(READ)
    response = api.get(SCHEDULE, headers=headers)
    assert response.status_code == 200
    assert response.json() == SHIPPED


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_schedule_set_is_read_back_by_its_author_its_counter_advanced(
    api: ContractClient, database: Database, person: Person
) -> None:
    user_id, headers = person(READ, WRITE)
    response = api.put(SCHEDULE, headers=headers, json=WEEKLY)
    assert response.status_code == 200
    assert response.json() == WEEKLY | {"lock_version": 2}
    assert api.get(SCHEDULE, headers=headers).json() == WEEKLY | {"lock_version": 2}
    row = schedule_row(database)
    assert (row["at_time"], row["weekday"], row["updated_by"]) == (time(3, 15), 1, user_id)
    assert row["created_by"] is None
    # Back to a daily reading: the day goes.
    daily = api.put(SCHEDULE, headers=headers, json=SHIPPED | {"lock_version": 2})
    assert daily.json() == SHIPPED | {"lock_version": 3}
    assert schedule_row(database)["weekday"] is None


type Refused = list[tuple[str, str, dict[str, Any]]]

# A body in default, as changes to the shipped schedule, and the fields its refusal names.
REFUSALS: list[tuple[dict[str, Any], Refused]] = [
    ({"at_time": "25:00"}, [("/at_time", "VALIDATION_FAILED", {})]),
    ({"at_time": "1:30"}, [("/at_time", "VALIDATION_FAILED", {})]),
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
    (
        {"at_time": "24:00", "frequency": "weekly", "weekday": 9},
        [
            ("/at_time", "VALIDATION_FAILED", {}),
            ("/weekday", "VALUE_OUT_OF_RANGE", {"maximum": 7}),
        ],
    ),
    ({"frequency": "monthly"}, [("/frequency", "VALIDATION_FAILED", {})]),
]


@pytest.mark.requirement("WF-ADM-0070-A")
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
        "hour-and-day",
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


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_field_missing_is_required(api: ContractClient, person: Person) -> None:
    _, headers = person(WRITE)
    sent = {name: value for name, value in SHIPPED.items() if name != "weekday"}
    assert fields(api.put(SCHEDULE, headers=headers, json=sent)) == [
        ("/weekday", "VALUE_REQUIRED", {})
    ]


@pytest.mark.requirement("WF-ADM-0070-A")
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


@pytest.mark.requirement("WF-ADM-0100-A")
def test_the_schedule_is_read_under_users_read_and_written_under_users_write(
    api: ContractClient, database: Database, person: Person
) -> None:
    # Without the permission to read the accounts, the schedule does not exist (404); without the
    # one to change them, the writing is forbidden (403), the one that starts a reading on demand.
    _, nothing = person()
    _, reader = person(READ)
    assert api.get(SCHEDULE, headers=nothing).status_code == 404
    refused = api.put(SCHEDULE, headers=reader, json=WEEKLY)
    assert refused.status_code == 403
    assert refused.json()["params"] == {"missing_permission": WRITE}
    assert schedule_row(database)["lock_version"] == 1


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_schedule_read_is_the_row_the_migrations_wrote(database: Database) -> None:
    with database.transaction() as session:
        view = read_sync_schedule(session)
        authors = session.execute(
            select(IdentitySyncSchedule.created_by, IdentitySyncSchedule.updated_by)
        ).one()
    assert (view.schedule.frequency, view.schedule.at_time, view.lock_version) == (
        "daily",
        time(1, 30),
        1,
    )
    assert tuple(authors) == (None, None)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_writing_judged_is_the_schedule_with_its_time_to_the_minute() -> None:
    judged = judged_sync_schedule(
        written(is_enabled=False, frequency="weekly", at_time="23:59", weekday=7)
    )
    assert (judged.is_enabled, judged.at_time, judged.weekday) == (False, time(23, 59), 7)
    with pytest.raises(UnprocessableError) as raised:
        judged_sync_schedule(written(at_time="7:00", weekday=2))
    assert [(each.pointer, each.code) for each in raised.value.fields] == [
        ("/at_time", "VALIDATION_FAILED"),
        ("/weekday", "VALIDATION_FAILED"),
    ]


@pytest.mark.requirement("WF-DAT-0070-A")
def test_a_schedule_written_is_dated_and_signed(database: Database) -> None:
    author = account(database, "Durand", "Paul")
    at = utc_now()
    with database.transaction() as session:
        schedule = judged_sync_schedule(written(at_time="04:00"))
        write_sync_schedule(session, schedule, 1, Act(author, at))
    row = schedule_row(database)
    assert (row["updated_by"], row["updated_at"], row["lock_version"]) == (author, at, 2)
