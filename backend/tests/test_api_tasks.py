# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A caller follows the background tasks it asked for, and those alone.

Each person is an account written around the service, with a token of the realm of test; every
answer is checked against the contract (``ContractClient``).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

import pytest
from realm import KEY, TestRealm
from sqlalchemy import insert, update
from sqlalchemy.orm import Session
from support import ContractClient, bearer, raw_account
from task_handlers import REQUEST, deposit

from waterfall.api.contract.models import BackgroundTaskStatus, Kind
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database
from waterfall.platform.errors import ConflictError, FieldError, UnprocessableError
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import KINDS, STATUSES, BackgroundTask, Task
from waterfall.worker.runner import Timing, Worker

TASKS = "/api/v1/tasks"


type Person = Callable[[], tuple[UUID, dict[str, str]]]


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each with the header of its token; no role is needed."""

    def make() -> tuple[UUID, dict[str, str]]:
        subject = f"subject-{uuid4()}"
        row = raw_account(idp_subject=subject, email=f"{uuid4().hex}@example.org")
        with database.transaction() as session:
            session.execute(insert(UserAccount).values(**row))
        user_id = row["id"]
        assert isinstance(user_id, UUID)
        return user_id, bearer(realm.token(subject, KEY))

    return make


def refused(_session: Session, _task: Task) -> None:
    """Refuse the work, as a task refuses what its state forbids."""
    code = "STATE_FORBIDS_OPERATION"
    raise ConflictError(code)


def finish(database: Database, task_id: UUID, status: str, at: datetime) -> None:
    """End a task by hand, at a moment the test chooses."""
    problem = None if status == "succeeded" else {"code": "INTERNAL_ERROR", "status": 500}
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == task_id)
            .values(status=status, problem=problem, finished_at=at, progress=100)
        )


def test_the_kinds_and_the_states_of_a_task_are_those_of_the_contract() -> None:
    assert tuple(kind.value for kind in Kind) == KINDS
    assert tuple(status.value for status in BackgroundTaskStatus) == STATUSES


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_caller_follows_its_task_from_its_queue_to_its_failure_and_why(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # « … et l'utilisateur en voit l'aboutissement. » : queued, then ended — here refused, with the
    # code, the status and the correlation of the request that deposited it.
    user_id, headers = person()
    task_id = deposit(database, queue, requested_by=user_id)
    queued = api.get(f"{TASKS}/{task_id}", headers=headers)
    assert queued.status_code == 200
    assert queued.json() == {
        "task_id": str(task_id),
        "kind": "identity_sync",
        "status": "queued",
        "progress": 0,
        "submitted_at": queued.json()["submitted_at"],
        "finished_at": None,
        "problem": None,
        "result_url": None,
    }
    queue.prepare()
    assert Worker(database, queue, {"identity_sync": refused}, "worker", Timing(0, 0.01)).step()
    failed = api.get(f"{TASKS}/{task_id}", headers=headers).json()
    assert failed["status"] == "failed"
    assert failed["finished_at"] is not None
    assert failed["problem"] == {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "correlation_id": REQUEST,
    }


def test_a_task_refused_by_field_is_read_with_its_fields(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # A refusal by field says which field, and why, as the envelope of an answer does: the
    # requester reads it as the handler raised it.
    def refused_by_field(_session: Session, _task: Task) -> None:
        short = FieldError("/retention_days", "VALUE_OUT_OF_RANGE", {"minimum": 7})
        unknown = FieldError("/external_copy/location", "UNKNOWN_EXTERNAL_BACKUP_LOCATION")
        code = "VALIDATION_FAILED"
        raise UnprocessableError(code, fields=(short, unknown))

    user_id, headers = person()
    task_id = deposit(database, queue, requested_by=user_id)
    queue.prepare()
    taker = Worker(database, queue, {"identity_sync": refused_by_field}, "worker", Timing(0, 0.01))
    assert taker.step()
    response = api.get(f"{TASKS}/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["problem"] == {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {"pointer": "/retention_days", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": 7}},
            {"pointer": "/external_copy/location", "code": "UNKNOWN_EXTERNAL_BACKUP_LOCATION"},
        ],
        "correlation_id": REQUEST,
    }


def test_a_task_another_account_or_the_platform_asked_for_is_not_found(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    owner, _ = person()
    _, headers = person()
    for requested_by in (owner, None):
        task_id = deposit(database, queue, requested_by=requested_by)
        response = api.get(f"{TASKS}/{task_id}", headers=headers)
        assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")
    for unknown in (str(uuid4()), "not-a-task"):
        assert api.get(f"{TASKS}/{unknown}", headers=headers).status_code == 404
    assert api.get(TASKS, headers=headers).json()["meta"]["total"] == 0


def test_the_list_gives_the_tasks_of_the_caller_the_latest_first_as_its_filters_keep_them(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    user_id, headers = person()
    other, _ = person()
    first, second, third = (deposit(database, queue, requested_by=user_id) for _ in range(3))
    deposit(database, queue, requested_by=other)
    deposit(database, queue)
    finish(database, first, "succeeded", datetime(2026, 10, 1, tzinfo=UTC))
    finish(database, second, "failed", datetime(2026, 10, 3, tzinfo=UTC))

    def listed(query: str = "") -> tuple[list[str], int]:
        response = api.get(f"{TASKS}{query}", headers=headers)
        assert response.status_code == 200
        body = response.json()
        return [item["task_id"] for item in body["items"]], body["meta"]["total"]

    assert listed() == ([str(third), str(second), str(first)], 3)
    assert listed("?status=queued,running") == ([str(third)], 1)
    assert listed("?status=failed,succeeded") == ([str(second), str(first)], 2)
    since = quote(datetime(2026, 10, 2, tzinfo=UTC).isoformat())
    assert listed(f"?finished_since={since}") == ([str(third), str(second)], 2)
    assert listed("?limit=1&offset=1") == ([str(second)], 3)
    page = api.get(f"{TASKS}?limit=1&offset=1", headers=headers).json()
    assert page["meta"] == {"limit": 1, "offset": 1, "total": 3}


def test_the_tasks_are_read_by_a_known_caller_alone(api: ContractClient) -> None:
    for path in (TASKS, f"{TASKS}/{uuid4()}"):
        response = api.get(path)
        assert (response.status_code, response.json()["code"]) == (401, "SESSION_REQUIRED")


def problem(response: Any) -> tuple[int, str, list[str]]:
    """Give the status, the code and the pointers of the fields of a refusal."""
    body = response.json()
    pointers = [field["pointer"] for field in body.get("fields", [])]
    return response.status_code, body["code"], pointers


@pytest.mark.parametrize(
    ("query", "pointer", "code"),
    [
        ("?status=done", "/query/status", "VALIDATION_FAILED"),
        ("?status=", "/query/status", "VALIDATION_FAILED"),
        ("?status=%00", "/query/status", "VALIDATION_FAILED"),
        ("?limit=0", "/query/limit", "VALUE_OUT_OF_RANGE"),
        ("?offset=-1", "/query/offset", "VALUE_OUT_OF_RANGE"),
        ("?finished_since=yesterday", "/query/finished_since", "DATE_INVALID"),
        ("?finished_since=2026-10-02", "/query/finished_since", "DATE_INVALID"),
        ("?finished_since=2026-10-02T00:00:00", "/query/finished_since", "DATE_INVALID"),
    ],
)
def test_a_parameter_the_list_refuses_is_a_value_refused(
    api: ContractClient, person: Person, query: str, pointer: str, code: str
) -> None:
    # A value outside the schema of a parameter is refused at its field (422), never a 500, with
    # the code of its fault: an instant that does not parse, or without its offset, is a date
    # refused (``DATE_INVALID``). The contract declares that 422 (#799): the answer is read
    # through it.
    _, headers = person()
    response = api.get(f"{TASKS}{query}", headers=headers)
    assert problem(response) == (422, "VALIDATION_FAILED", [pointer])
    assert [field["code"] for field in response.json()["fields"]] == [code]
