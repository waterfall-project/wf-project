# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The worker and its queue: a task runs in the worker alone, once, whole or not at all.

The tests register their own handler on the kind of the reading of the accounts, whose handler
comes with US-0370/L2, which proves again on it what they prove of the mechanism. The worker runs
here one step at a time; a stop is what ``SIGTERM`` raises in it (``serve``), and a worker started
again is another consumer of the queue.
"""

from collections.abc import Callable, Mapping
from itertools import count
from uuid import uuid4

import grimp
import pytest
from redis.exceptions import ResponseError
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import Logs
from task_handlers import REQUEST, Runs, deposit, held_run, inscribe, inscriptions, task

from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import FIELD, TaskQueue
from waterfall.platform.tasks import BackgroundTask, Task, TaskError, TaskHandler, submit
from waterfall.worker.runner import MAX_ATTEMPTS, Timing, Worker

# Every entry pending is taken over at once: the tests stand for a worker started again.
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
INTERNAL = {"code": "INTERNAL_ERROR", "status": 500, "correlation_id": REQUEST}
NEWER = {"backup_version": "1.1.0", "installed_version": "1.0.0"}
UNREACHABLE = "redis://127.0.0.1:9/0"

type MakeWorker = Callable[[Mapping[str, TaskHandler]], Worker]


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> MakeWorker:
    """Give a maker of workers on the queue of the test, each a consumer of its own."""
    numbers = count()

    def make(handlers: Mapping[str, TaskHandler]) -> Worker:
        queue.prepare()
        return Worker(database, queue, handlers, f"worker-{next(numbers)}", AT_ONCE)

    return make


def interrupted(session: Session, task: Task) -> None:
    """Do the work, then be stopped before the end, as ``SIGTERM`` stops the worker."""
    inscribe(session, task)
    raise KeyboardInterrupt


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_deposited_task_runs_in_the_worker_and_never_in_the_request_that_deposits_it(
    database: Database, queue: TaskQueue, worker: MakeWorker
) -> None:
    # « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir
    # exécuté. » : the handlers are the worker's, which the API cannot reach; a request that
    # deposits a task ends with it queued, deposited once its transaction is committed.
    graph = grimp.build_graph("waterfall")
    assert not graph.chain_exists("waterfall.api", "waterfall.worker", as_packages=True)
    runs = Runs()
    with logging_context(correlation_id=REQUEST), database.transaction() as session:
        task_id = submit(session, queue, "identity_sync", None)
        assert queue.waiting() == set()
    assert (queue.waiting(), task(database, task_id).status, runs) == ({task_id}, "queued", [])
    taker = worker({"identity_sync": runs})
    assert taker.step()
    taker.redeposit()
    assert runs == [task_id]
    ended = task(database, task_id)
    assert (ended.status, ended.progress, ended.attempts) == ("succeeded", 100, 1)
    assert ended.finished_at is not None
    with database.transaction() as session:
        absent = BackgroundTask.result.is_(None) & BackgroundTask.problem.is_(None)
        assert session.scalar(select(absent).where(BackgroundTask.id == task_id))
    assert queue.waiting() == set()


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_task_is_deposited_once_committed_and_under_a_correlation_alone(
    database: Database, queue: TaskQueue
) -> None:
    def request() -> None:
        with logging_context(correlation_id=REQUEST), database.transaction() as session:
            submit(session, queue, "identity_sync", None)
            raise LookupError

    with pytest.raises(LookupError):
        request()
    with pytest.raises(TaskError), database.transaction() as session:
        submit(session, queue, "identity_sync", None)
    assert queue.waiting() == set()


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_task_inscribes_its_work_under_the_correlation_of_the_request_that_deposited_it(
    database: Database, queue: TaskQueue, worker: MakeWorker, logs: Logs
) -> None:
    # The identifier made at the entrance of the platform reaches the worker by the task it
    # starts, and the journal by the work of the task (#701).
    task_id = deposit(database, queue)
    assert worker({"identity_sync": inscribe}).step()
    (inscribed,) = inscriptions(database)
    assert (inscribed.correlation_id, inscribed.actor_user_id) == (REQUEST, None)
    assert inscribed.params == {"task_id": str(task_id)}
    records = logs.named("task.started") + logs.named("task.succeeded")
    assert len(records) == 2
    for record in records:
        assert (record["correlation_id"], record["actor"]) == (REQUEST, "platform")
        assert record["task_id"] == str(task_id)


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_failed_task_is_followed_from_its_request_to_its_failure_by_one_identifier(
    database: Database, queue: TaskQueue, worker: MakeWorker, logs: Logs
) -> None:
    # « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul
    # identifiant, que le message présenté à l'utilisateur contient. » : the problem the requester
    # reads carries the correlation of its request, as the logs of the task do; the work of the
    # failed task is undone, its end kept.
    code = "BACKUP_FROM_NEWER_VERSION"

    def refused(session: Session, task: Task) -> None:
        inscribe(session, task)
        raise UnprocessableError(code, NEWER)

    task_id = deposit(database, queue)
    assert worker({"identity_sync": refused}).step()
    ended = task(database, task_id)
    assert (ended.status, ended.finished_at is not None) == ("failed", True)
    assert ended.problem == {
        "code": code,
        "status": 422,
        "params": NEWER,
        "correlation_id": REQUEST,
    }
    assert inscriptions(database) == []
    (failed,) = logs.named("task.failed")
    assert (failed["correlation_id"], failed["code"]) == (REQUEST, code)


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_worker_stopped_during_a_task_leaves_the_base_unchanged_and_the_task_runs_again(
    database: Database, queue: TaskQueue, worker: MakeWorker
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après
    # redémarrage. » : the work of the stopped attempt is rolled back; its entry, left pending, is
    # taken over by the worker started again, which runs the task from the start.
    task_id = deposit(database, queue)
    with pytest.raises(KeyboardInterrupt):
        worker({"identity_sync": interrupted}).step()
    assert inscriptions(database) == []
    assert (task(database, task_id).status, task(database, task_id).attempts) == ("running", 1)
    assert queue.waiting() == {task_id}
    assert worker({"identity_sync": inscribe}).step()
    (inscribed,) = inscriptions(database)
    assert inscribed.params == {"task_id": str(task_id)}
    assert (task(database, task_id).status, task(database, task_id).attempts) == ("succeeded", 2)
    assert queue.waiting() == set()


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_task_stopped_at_each_of_its_three_attempts_fails_without_a_fourth(
    database: Database, queue: TaskQueue, worker: MakeWorker
) -> None:
    # « Une tâche interrompue est reprise ou échoue sans laisser d'état intermédiaire. »
    task_id, runs = deposit(database, queue), Runs()
    for _ in range(MAX_ATTEMPTS):
        with pytest.raises(KeyboardInterrupt):
            worker({"identity_sync": interrupted}).step()
    assert worker({"identity_sync": runs}).step()
    ended = task(database, task_id)
    assert (ended.status, ended.attempts, ended.problem, runs) == ("failed", 3, INTERNAL, [])
    assert inscriptions(database) == []
    assert queue.waiting() == set()


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_task_that_runs_elsewhere_is_left_pending_and_a_task_deposited_twice_runs_once(
    database: Database, queue: TaskQueue, worker: MakeWorker
) -> None:
    # An entry taken over while its task still runs finds the lock of the run held, and waits; a
    # second entry of a task that ended is dropped.
    task_id, runs = deposit(database, queue), Runs()
    queue.deposit(task_id)
    taker = worker({"identity_sync": runs})
    with held_run(database, task_id):
        assert taker.step()
        assert (runs, task(database, task_id).status) == ([], "queued")
    assert taker.step()
    assert taker.step()
    assert runs == [task_id]
    assert queue.waiting() == set()


def broken(session: Session, task: Task) -> None:
    """Do the work, then fail for no reason the requester can act on."""
    inscribe(session, task)
    message = "the provider answered nonsense"
    raise RuntimeError(message)


type Breaking = tuple[Mapping[str, TaskHandler], int, str]


@pytest.mark.parametrize(
    "breaking",
    [({}, 0, "kind_unhandled"), ({"identity_sync": broken}, 1, "error")],
    ids=["unhandled", "broken"],
)
def test_a_task_no_handler_runs_or_whose_handler_breaks_fails_under_its_correlation(
    database: Database, queue: TaskQueue, worker: MakeWorker, logs: Logs, breaking: Breaking
) -> None:
    handlers, attempts, reason = breaking
    task_id = deposit(database, queue)
    assert worker(handlers).step()
    ended = task(database, task_id)
    assert (ended.status, ended.attempts, ended.problem) == ("failed", attempts, INTERNAL)
    assert inscriptions(database) == []
    (failed,) = logs.named("task.failed")
    assert (failed["reason"], failed["correlation_id"]) == (reason, REQUEST)
    assert ("the provider answered nonsense" in failed.get("exception", "")) is bool(handlers)
    assert queue.waiting() == set()


@pytest.mark.requirement("WF-ARC-0040-A")
def test_a_task_deposited_before_redis_is_emptied_runs_once_it_is_back(
    database: Database, queue: TaskQueue, worker: MakeWorker
) -> None:
    # « Une tâche demandée avant le vidage de Redis et non encore prise est exécutée après le
    # rétablissement. » : the stream and its group are lost; the worker makes them again and
    # deposits the queued tasks again, from the table. A task that ran when its entry was lost is
    # taken up again, unless its lock is still held: it still runs.
    stopped, queued, running = (deposit(database, queue) for _ in range(3))
    with pytest.raises(KeyboardInterrupt):
        worker({"identity_sync": interrupted}).step()
    with database.transaction() as session:
        started = {"status": "running", "attempts": 1, "started_at": utc_now()}
        session.execute(update(BackgroundTask).where(BackgroundTask.id == running).values(started))
    runs = Runs()
    taker = worker({"identity_sync": runs})
    queue.client.delete(queue.stream)
    with held_run(database, running):
        assert not taker.step()
        assert queue.waiting() == {queued, stopped}
    while taker.step():
        pass
    assert sorted(runs) == sorted([queued, stopped])
    assert task(database, running).status == "running"


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.parametrize(("every", "named"), [(60, 0), (0, 1)], ids=["period", "due"])
def test_a_task_whose_deposit_redis_refused_is_deposited_by_the_worker_at_start_then_each_period(
    database: Database, queue: TaskQueue, logs: Logs, every: float, named: int
) -> None:
    # The request is not failed by a deposit that follows its commit; the worker deposits the
    # queued tasks the stream does not name when it starts, and at the end of each period.
    lost = deposit(database, TaskQueue.connect(UNREACHABLE, queue.stream))
    (refused,) = logs.named("task.deposit_failed")
    assert refused["task_id"] == str(lost)
    queue.prepare()
    taker = Worker(database, queue, {"identity_sync": inscribe}, "worker", Timing(0, 0.01, every))
    steps = count()

    def step() -> bool:
        if next(steps):
            raise KeyboardInterrupt
        deposit(database, TaskQueue.connect(UNREACHABLE, queue.stream))
        return Worker.step(taker)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(taker, "step", step)
        with pytest.raises(KeyboardInterrupt):
            taker.run()
    assert task(database, lost).status == "succeeded"
    assert len(queue.waiting()) == named


def test_an_entry_that_names_no_task_known_is_dropped_and_redis_refusing_more_is_not_hidden(
    queue: TaskQueue, worker: MakeWorker, logs: Logs
) -> None:
    runs = Runs()
    taker = worker({"identity_sync": runs})
    queue.client.xadd(queue.stream, {FIELD: "not-a-task"})
    queue.client.xadd(queue.stream, {FIELD: str(uuid4())})
    assert (taker.step(), taker.step(), taker.step()) == (True, True, False)
    assert (runs, queue.client.xlen(queue.stream)) == ([], 0)
    assert len(logs.named("queue.entry_unreadable")) == 1
    queue.client.delete(queue.stream)
    queue.client.set(queue.stream, "not a stream")
    with pytest.raises(ResponseError, match="WRONGTYPE"):
        queue.prepare()
    with pytest.raises(ResponseError, match="WRONGTYPE"):
        taker.step()


def test_what_a_handler_gives_or_refuses_with_is_kept_as_json(
    database: Database, queue: TaskQueue, worker: MakeWorker
) -> None:
    def gives(_session: Session, task: Task) -> Mapping[str, object]:
        return {"task": task.task_id}

    def refuses(_session: Session, task: Task) -> None:
        code = "LAST_ADMINISTRATOR"
        raise UnprocessableError(code, {"conflicting_object_id": task.task_id})

    given, refused = deposit(database, queue), deposit(database, queue, kind="backup")
    taker = worker({"identity_sync": gives, "backup": refuses})
    assert taker.step()
    assert taker.step()
    assert task(database, given).result == {"task": str(given)}
    problem = task(database, refused).problem
    assert (problem or {}).get("params") == {"conflicting_object_id": str(refused)}


def test_a_read_of_the_worker_waits_less_than_its_socket_waits_for_redis(queue: TaskQueue) -> None:
    # A read as long as the socket's wait would end in a timeout, and stop the worker.
    assert Timing().block < queue.client.connection_pool.connection_kwargs["socket_timeout"]
