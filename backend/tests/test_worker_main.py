# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of the worker: it refuses to start without its secrets, runs, stops, schedules."""

import json
import os
import signal
import socket
from collections import Counter
from datetime import timedelta
from typing import TYPE_CHECKING

import httpx2
import pytest
import redis
from sqlalchemy import select, update
from test_api_processes import free_port

import waterfall
from waterfall.core.users.tables import IdentitySyncSchedule
from waterfall.platform.correlation import FORM
from waterfall.platform.database import Database, utc_now
from waterfall.platform.queue import WORKER_TIMEOUT, TaskQueue
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import main as worker_main
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from support import Logs

    from waterfall.platform.settings import ServiceSettings

SCHEDULE = ["schedule"]


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
    [
        (
            [],
            (
                "DATABASE_URL",
                "REDIS_URL",
                "SERVICE_CLIENT_SECRET",
                "STORAGE_SECRET",
                "BACKUP_DATABASE_URL",
                "KEYCLOAK_DATABASE_URL",
            ),
        ),
        (SCHEDULE, ("DATABASE_URL", "REDIS_URL")),
    ],
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
    [
        ["--versoin"],
        ["schedule", "now"],
        ["enqueue", "identity_sync"],
        ["purge"],
    ],
)
@pytest.mark.story("US-2830")
def test_any_argument_but_the_version_or_the_schedule_is_refused_the_old_verbs_with_them(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert worker_main.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("usage: waterfall-worker [--version | schedule]\n")
    assert arguments[-1] in captured.err.splitlines()[-1]


@pytest.mark.usefixtures("platform_environment", "logs")
def test_with_its_secrets_the_worker_runs_the_kinds_it_has_a_handler_for(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_METRICS_PORT", str(free_port()))
    served: list[Worker] = []

    def serve(worker: Worker) -> int:
        served.append(worker)
        return 0

    monkeypatch.setattr(worker_main, "serve", serve)
    assert worker_main.main([]) == 0
    (worker,) = served
    assert set(worker.handlers) == {
        "backup",
        "backup_copy",
        "identity_sync",
        "revision_mark",
        "structure_merge",
        "risk_occurrence",
        "import_analysis",
        "import_apply",
        "export",
        "purge",
        "partition_reserve",
    }
    assert worker.consumer
    # A read as long as the socket's wait would end in a timeout, and stop the worker.
    waits = worker.queue.client.connection_pool.connection_kwargs["socket_timeout"]
    assert worker.timing.block < waits == WORKER_TIMEOUT
    assert worker.timing.unknown_kind_wait == 3600


@pytest.mark.story("US-2850")
@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_wait_of_the_deployment_is_the_one_the_worker_keeps_for_an_unknown_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_METRICS_PORT", str(free_port()))
    monkeypatch.setenv("WATERFALL_UNKNOWN_KIND_WAIT_SECONDS", "7200")
    served: list[Worker] = []

    def serve(worker: Worker) -> int:
        served.append(worker)
        return 0

    monkeypatch.setattr(worker_main, "serve", serve)
    assert worker_main.main([]) == 0
    (worker,) = served
    assert worker.timing.unknown_kind_wait == 7200


@pytest.mark.requirement("WF-OBS-0010-A")
@pytest.mark.usefixtures("platform_environment", "logs")
def test_the_worker_answers_on_its_metrics_endpoint_while_it_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Le front, l'API et le worker répondent sur leur point de métriques. » : the worker, on the
    # port its settings name, while it runs, its tasks counted; the port is closed when it stops.
    port = free_port()
    monkeypatch.setenv("WATERFALL_METRICS_PORT", str(port))
    answers: list[httpx2.Response] = []

    def serve(worker: Worker) -> int:
        assert worker.metrics is not None
        answers.append(httpx2.get(f"http://127.0.0.1:{port}/metrics", timeout=10))
        return 0

    monkeypatch.setattr(worker_main, "serve", serve)
    assert worker_main.main([]) == 0
    (answer,) = answers
    assert answer.status_code == 200
    assert "# TYPE waterfall_worker_tasks_total counter" in answer.text
    assert "waterfall_identity_directory_sync_failures_total 0.0" in answer.text
    # Its version, which the status screen presents (WF-EXP-0030, US-2890).
    version = waterfall.__version__
    announced = f'waterfall_component_version{{component="worker",version="{version}"}} 1.0'
    assert announced in answer.text
    with pytest.raises(httpx2.TransportError):
        httpx2.get(f"http://127.0.0.1:{port}/metrics", timeout=1)


@pytest.mark.usefixtures("platform_environment", "logs")
def test_a_metrics_port_already_taken_stops_the_worker_naming_the_variable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Proper to US-2870: a port the worker cannot listen on is a setting wrong, said as the others
    # are (2), not a bare error; the worker has opened nothing, and runs nothing.
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        monkeypatch.setenv("WATERFALL_HOST", "127.0.0.1")
        monkeypatch.setenv("WATERFALL_METRICS_PORT", str(taken.getsockname()[1]))
        served: list[Worker] = []

        def serve(worker: Worker) -> int:
            served.append(worker)
            return 0

        monkeypatch.setattr(worker_main, "serve", serve)
        assert worker_main.main([]) == 2
    assert "WATERFALL_METRICS_PORT" in capsys.readouterr().err
    assert served == []


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


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_worker_that_loses_redis_ends_in_failure_said_in_its_logs_without_its_secrets(
    database: Database,
    queue: TaskQueue,
    logs: Logs,
    platform_settings: ServiceSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Une recherche des secrets et des jetons connus dans les journaux ne les trouve pas. » : an
    # error the worker does not expect is a record of its logs, masked as they are, never a bare
    # trace; the worker ends in failure, for the platform to start it again.
    address = platform_settings.redis_url.get_secret_value()
    worker = Worker(database, queue, {})

    def run() -> None:
        message = f"Error 111 connecting to {address}. Connection refused."
        raise redis.ConnectionError(message)

    monkeypatch.setattr(worker, "run", run)
    before = signal.getsignal(signal.SIGTERM)
    try:
        assert worker_main.serve(worker) == 1
    finally:
        signal.signal(signal.SIGTERM, before)
    (failed,) = logs.named("worker.failed")
    assert "redis.exceptions.ConnectionError: Error 111 connecting to" in failed["exception"]
    assert logs.named("worker.stopped") == []
    assert all(secret not in logs.text for secret in platform_settings.secret_values())


def test_a_schedule_that_cannot_reach_the_database_ends_in_failure_said_in_its_logs(
    service_environment: dict[str, str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreachable = "postgresql+psycopg://waterfall@127.0.0.1:9/waterfall"
    for name, value in {**service_environment, "WATERFALL_DATABASE_URL": unreachable}.items():
        monkeypatch.setenv(name, value)
    assert worker_main.main(SCHEDULE) == 1
    err = capsys.readouterr().err
    (failed,) = records(err)
    assert (failed["event"], failed["actor"]) == ("schedule.failed", "platform")
    assert FORM.fullmatch(str(failed["correlation_id"]))
    assert "OperationalError" in str(failed["exception"])


@pytest.fixture
def scheduled(
    service_environment: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Give the process what the schedule reads: the database and Redis, and nothing else."""
    for name, value in service_environment.items():
        monkeypatch.setenv(name, value)
    return service_environment


@pytest.fixture
def owing_a_reading(database: Database) -> None:
    """Make the schedule of the readings owe one: written ten days ago, due since its 01:30."""
    with database.transaction() as session:
        session.execute(
            update(IdentitySyncSchedule).values(
                updated_at=utc_now() - timedelta(days=10),
                timing_changed_at=utc_now() - timedelta(days=10),
            )
        )


def tasks_of(database: Database) -> dict[str, BackgroundTask]:
    """Read the tasks the schedule deposited, by kind."""
    with database.transaction() as session:
        return {row.kind: row for row in session.scalars(select(BackgroundTask))}


@pytest.mark.story("US-2830")
@pytest.mark.usefixtures("logs", "scheduled", "owing_a_reading")
def test_the_schedule_deposits_the_reading_of_the_accounts_and_the_purge_for_the_platform(
    database: Database, platform_queue: TaskQueue, capsys: pytest.CaptureFixture[str]
) -> None:
    # propre à US-2830 : « la purge de ce qui a expiré est une tâche de fond, inscrite et mise en
    # file par la commande planifiée » : both kinds are written for the platform, under a
    # correlation of the command's own, and put in the queue; none is run.
    assert worker_main.main(SCHEDULE) == 0
    deposited = tasks_of(database)
    assert sorted(deposited) == ["identity_sync", "partition_reserve", "purge"]
    assert sorted(platform_queue.waiting()) == sorted(row.id for row in deposited.values())
    for row in deposited.values():
        assert (row.status, row.requested_by, row.attempts) == ("queued", None, 0)
        assert FORM.fullmatch(row.correlation_id)
    said = [(each["event"], each["kind"]) for each in records(capsys.readouterr().err)]
    # And the filling of the reserve of partitions, empty (US-2830/L4).
    assert said == [
        ("task.enqueued", "identity_sync"),
        ("task.enqueued", "purge"),
        ("task.enqueued", "partition_reserve"),
    ]


@pytest.mark.story("US-2830")
@pytest.mark.usefixtures("logs", "scheduled", "owing_a_reading")
def test_the_schedule_deposits_nothing_of_a_kind_that_is_pending_nor_before_its_interval(
    database: Database, platform_queue: TaskQueue, capsys: pytest.CaptureFixture[str]
) -> None:
    # « [la commande] ne dépose rien dont une tâche du même genre est en file ou en cours » : a
    # task queued or running stops its kind, one that ended recently leaves it not yet due.
    assert worker_main.main(SCHEDULE) == 0
    first = tasks_of(database)
    capsys.readouterr()
    for changes in ({"status": "queued"}, {"status": "running"}):
        with database.transaction() as session:
            session.execute(update(BackgroundTask).values(changes))
        assert worker_main.main(SCHEDULE) == 0
    ended = {"status": "succeeded", "finished_at": utc_now()}
    with database.transaction() as session:
        session.execute(update(BackgroundTask).values(ended))
    assert worker_main.main(SCHEDULE) == 0
    kept = ("identity_sync", "purge")
    after = tasks_of(database)
    assert {kind: after[kind].id for kind in kept} == {kind: first[kind].id for kind in kept}
    # The filling of the reserve of partitions is due while the reserve is short, not at an
    # interval: ended, it is deposited again, the reserve still empty (US-2830/L4).
    with database.transaction() as session:
        fillings = session.scalars(
            select(BackgroundTask.id).where(BackgroundTask.kind == "partition_reserve")
        ).all()
    assert len(fillings) == 2
    assert first["partition_reserve"].id in fillings
    assert len(platform_queue.waiting()) == 4
    said = [(each["event"], each.get("kind")) for each in records(capsys.readouterr().err)]
    pending = [
        ("task.already_pending", "identity_sync"),
        ("task.already_pending", "purge"),
        ("task.already_pending", "partition_reserve"),
    ]
    assert said == [*pending, *pending, ("task.enqueued", "partition_reserve")]


@pytest.mark.story("US-2830")
@pytest.mark.usefixtures("logs", "scheduled")
def test_the_schedule_deposits_the_purge_again_once_its_interval_has_passed_since_the_last(
    database: Database, platform_queue: TaskQueue, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The purge at its own interval: the latest task of the kind, whatever its state, fixes when
    # the next one is due. (The reading of the accounts is not due at an interval of the
    # installation but at the time of its schedule: test_identity_sync_planned.py.)
    assert worker_main.main(SCHEDULE) == 0
    # The purge ended an hour after its deposit.
    ended = {"status": "failed", "finished_at": utc_now(), "problem": {"code": "X", "status": 500}}
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.kind == "purge")
            .values(ended | {"submitted_at": utc_now() - timedelta(hours=1)})
        )
    monkeypatch.setenv("WATERFALL_PURGE_INTERVAL", "3700")
    assert worker_main.main(SCHEDULE) == 0
    with database.transaction() as session:
        counts = Counter(session.scalars(select(BackgroundTask.kind)))
    # The filling of the reserve, queued since the first, is not deposited again (US-2830/L4).
    assert counts == {"purge": 1, "partition_reserve": 1}
    monkeypatch.setenv("WATERFALL_PURGE_INTERVAL", "3500")
    assert worker_main.main(SCHEDULE) == 0
    with database.transaction() as session:
        counts = Counter(session.scalars(select(BackgroundTask.kind)))
    assert counts == {"purge": 2, "partition_reserve": 1}
    assert len(platform_queue.waiting()) == 3


@pytest.mark.story("US-2830")
@pytest.mark.usefixtures("scheduled")
def test_a_schedule_whose_interval_is_no_positive_number_says_so_and_returns_two(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_PURGE_INTERVAL", "0")
    assert worker_main.main(SCHEDULE) == 2
    assert "WATERFALL_PURGE_INTERVAL" in capsys.readouterr().err
