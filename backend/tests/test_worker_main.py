# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of the worker: it refuses to start without its secrets, runs, stops, schedules."""

import json
import os
import signal

import pytest
from sqlalchemy import update
from support import Logs
from task_handlers import task

import waterfall
from waterfall.platform.correlation import FORM
from waterfall.platform.database import Database, utc_now
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import main as worker_main
from waterfall.worker.runner import Worker

SCHEDULE = ["enqueue", "identity_sync"]


def records(text: str) -> list[dict[str, object]]:
    """Read the records a command wrote, one JSON object per line."""
    return [json.loads(line) for line in text.splitlines()]


def test_the_version_is_stated_without_starting_anything(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert worker_main.main(["--version"]) == 0
    assert capsys.readouterr().out == f"waterfall-worker {waterfall.__version__}\n"


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.parametrize(
    ("arguments", "secrets"),
    [([], ("DATABASE_URL", "REDIS_URL", "SERVICE_CLIENT_SECRET")), (SCHEDULE, ("DATABASE_URL",))],
    ids=["worker", "schedule"],
)
def test_without_its_secrets_the_worker_returns_failure_and_names_them(
    arguments: list[str], secrets: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    # « Le démarrage d'un service sans les secrets attendus échoue en le disant, plutôt que de
    # démarrer sans. » : the worker, and the command that schedules its tasks.
    with pytest.MonkeyPatch.context() as patch:
        for name in [name for name in os.environ if name.startswith("WATERFALL_")]:
            patch.delenv(name)
        assert worker_main.main(arguments) == 2
    said = capsys.readouterr().err
    assert all(f"WATERFALL_{secret}: is missing" in said for secret in secrets)


@pytest.mark.parametrize(
    "arguments",
    [["--versoin"], ["enqueue"], ["enqueue", "backup"], ["enqueue", "identity_sync", "now"]],
)
def test_any_argument_but_the_version_or_a_kind_the_platform_schedules_is_refused(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert worker_main.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("usage: waterfall-worker [--version | enqueue <kind>]\n")
    assert arguments[-1] in captured.err.splitlines()[-1]


@pytest.mark.usefixtures("platform_environment", "logs")
def test_with_its_secrets_the_worker_runs_the_kinds_it_has_a_handler_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    served: list[Worker] = []

    def serve(worker: Worker) -> int:
        served.append(worker)
        return 0

    monkeypatch.setattr(worker_main, "serve", serve)
    assert worker_main.main([]) == 0
    (worker,) = served
    assert worker.handlers is worker_main.HANDLERS
    assert worker.consumer


def test_a_stop_of_the_platform_stops_the_worker_where_it_stands(
    database: Database, queue: TaskQueue, logs: Logs, monkeypatch: pytest.MonkeyPatch
) -> None:
    worker = Worker(database, queue, {})
    monkeypatch.setattr(worker, "run", lambda: os.kill(os.getpid(), signal.SIGTERM))
    before = signal.getsignal(signal.SIGTERM)
    try:
        assert worker_main.serve(worker) == 0
    finally:
        signal.signal(signal.SIGTERM, before)
    assert len(logs.named("worker.stopped")) == 1


@pytest.mark.usefixtures("logs")
def test_the_schedule_deposits_a_task_for_the_platform_unless_one_is_pending(
    database: Database,
    platform_queue: TaskQueue,
    service_environment: dict[str, str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in service_environment.items():
        monkeypatch.setenv(name, value)
    assert worker_main.main(SCHEDULE) == 0
    (deposited,) = platform_queue.waiting()
    scheduled = task(database, deposited)
    assert (scheduled.kind, scheduled.status, scheduled.requested_by) == (
        "identity_sync",
        "queued",
        None,
    )
    assert FORM.fullmatch(scheduled.correlation_id)
    ended = {"status": "succeeded", "finished_at": utc_now()}
    for changes in ({"status": "queued"}, {"status": "running"}, ended):
        with database.transaction() as session:
            session.execute(
                update(BackgroundTask).where(BackgroundTask.id == deposited).values(changes)
            )
        assert worker_main.main(SCHEDULE) == 0
    (_, following) = sorted(platform_queue.waiting())
    assert task(database, following).status == "queued"
    said = [record["event"] for record in records(capsys.readouterr().err)]
    pending = "task.already_pending"
    assert said == ["task.enqueued", pending, pending, "task.enqueued"]
