# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A task of a kind the worker does not run waits for a newer worker, then fails (US-2850, #809).

During a rolling update (WF-EXP-0030), a new API deposits a kind an old worker has no handler for:
the old worker leaves the entry, unacknowledged, and counts no attempt; a newer worker claims it.
"""

from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import update
from task_handlers import REQUEST, Runs, deposit, task

from waterfall.platform.database import Database, utc_now
from waterfall.platform.settings import WorkerSettings
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Mapping

    from support import Logs

    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.tasks import TaskHandler

pytestmark = pytest.mark.story("US-2850")

AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)


def worker(
    database: Database, queue: TaskQueue, name: str, kinds: Mapping[str, TaskHandler], wait: float
) -> Worker:
    """Give a worker of the queue, a consumer of its own, that waits ``wait`` seconds."""
    queue.prepare()
    return Worker(database, queue, kinds, name, replace(AT_ONCE, unknown_kind_wait=wait))


def submitted_ago(database: Database, task_id: object, age: timedelta) -> None:
    """Say a task was submitted ``age`` ago."""
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == task_id)
            .values(submitted_at=utc_now() - age)
        )


def test_a_task_of_an_unknown_kind_stays_pending_without_an_attempt(
    database: Database, queue: TaskQueue, logs: Logs
) -> None:
    older = worker(database, queue, "old", {}, wait=3600)
    task_id = deposit(database, queue)
    assert older.step()
    left = task(database, task_id)
    assert (left.status, left.attempts, left.problem) == ("queued", 0, None)
    assert queue.waiting() == {task_id}
    (said,) = logs.named("task.left")
    assert (said["reason"], said["correlation_id"]) == ("kind_unhandled", REQUEST)
    assert logs.named("task.failed") == []
    # Left again by each look: the entry is claimed again and again, never acknowledged.
    assert older.step()
    assert task(database, task_id).attempts == 0
    assert queue.waiting() == {task_id}


def test_a_newer_worker_takes_the_task_the_older_one_left(
    database: Database, queue: TaskQueue
) -> None:
    older = worker(database, queue, "old", {}, wait=3600)
    runs = Runs()
    newer = worker(database, queue, "new", {"identity_sync": runs}, wait=3600)
    task_id = deposit(database, queue)
    assert older.step()
    while queue.waiting() and newer.step():
        pass
    ended = task(database, task_id)
    assert (ended.status, ended.attempts, runs) == ("succeeded", 1, [task_id])
    assert queue.waiting() == set()


@pytest.mark.parametrize(
    ("age", "left"),
    [(timedelta(minutes=59), True), (timedelta(minutes=61), False)],
    ids=["within-the-wait", "wait-spent"],
)
def test_a_task_of_an_unknown_kind_fails_once_its_wait_is_spent_since_its_deposit(
    database: Database, queue: TaskQueue, logs: Logs, age: timedelta, *, left: bool
) -> None:
    older = worker(database, queue, "old", {}, wait=3600)
    task_id = deposit(database, queue)
    submitted_ago(database, task_id, age)
    assert older.step()
    ended = task(database, task_id)
    assert (ended.status, ended.attempts) == ("queued" if left else "failed", 0)
    assert bool(logs.named("task.left")) is left
    assert (queue.waiting() == {task_id}) is left
    if not left:
        (said,) = logs.named("task.failed")
        assert said["reason"] == "kind_unhandled"
        assert ended.problem is not None
        assert ended.problem["code"] == "INTERNAL_ERROR"


def test_the_wait_is_a_setting_of_the_worker_shipped_at_an_hour() -> None:
    assert WorkerSettings.model_fields["unknown_kind_wait_seconds"].default == 3600
    assert Timing().unknown_kind_wait == 3600.0
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        WorkerSettings.model_validate({"unknown_kind_wait_seconds": 0})
