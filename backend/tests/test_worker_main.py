# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands of the worker: it refuses to start without its secrets, runs, stops, schedules."""

import json
import os
import signal
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import redis
from access_rows import holder
from purge_environment import storage_environment
from sqlalchemy import update
from task_handlers import task

import waterfall
from waterfall.platform.correlation import FORM
from waterfall.platform.database import Database, utc_now
from waterfall.platform.queue import WORKER_TIMEOUT, TaskQueue
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import LIFETIME, FileUpload, Whole, object_key_of, record_whole
from waterfall.worker import main as worker_main
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

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
        (SCHEDULE, ("DATABASE_URL",)),
        (
            ["purge"],
            (
                "DATABASE_URL",
                "REDIS_URL",
                "STORAGE_ADDRESS",
                "STORAGE_ACCESS_KEY",
                "STORAGE_SECRET",
            ),
        ),
    ],
    ids=["worker", "schedule", "purge"],
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
        ["enqueue"],
        ["enqueue", "backup"],
        ["enqueue", "identity_sync", "now"],
        ["purge", "now"],
    ],
)
def test_any_argument_but_the_version_or_a_kind_the_platform_schedules_is_refused(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert worker_main.main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("usage: waterfall-worker [--version | enqueue <kind> | purge]\n")
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
    assert set(worker.handlers) == {
        "backup",
        "identity_sync",
        "revision_mark",
        "import_analysis",
        "import_apply",
        "export",
    }
    assert worker.consumer
    # A read as long as the socket's wait would end in a timeout, and stop the worker.
    waits = worker.queue.client.connection_pool.connection_kwargs["socket_timeout"]
    assert worker.timing.block < waits == WORKER_TIMEOUT


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
    unreachable = "postgresql+psycopg://waterfall:s3cret-of-the-schedule@127.0.0.1:9/waterfall"
    for name, value in {**service_environment, "WATERFALL_DATABASE_URL": unreachable}.items():
        monkeypatch.setenv(name, value)
    assert worker_main.main(SCHEDULE) == 1
    err = capsys.readouterr().err
    (failed,) = records(err)
    assert (failed["event"], failed["kind"], failed["actor"]) == (
        "task.enqueue_failed",
        "identity_sync",
        "platform",
    )
    assert FORM.fullmatch(str(failed["correlation_id"]))
    assert "OperationalError" in str(failed["exception"])


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


@pytest.fixture
def purge_environment(
    service_environment: dict[str, str], backups_bucket: Bucket, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Give the process what the purge reads: the database, Redis and the bucket of the tests."""
    environment = {**service_environment, **storage_environment(backups_bucket)}
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    return environment


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("logs", "database", "purge_environment")
def test_the_purge_runs_under_its_lock_and_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    # The verb the scheduler calls (EP-06, "La purge"): it runs under a correlation of its own, and
    # says it is done, with what the storage lost.
    assert worker_main.main(["purge"]) == 0
    (done,) = records(capsys.readouterr().err)
    assert (done["event"], done["actor"]) == ("purge.done", "platform")
    assert (done["objects"], done["deposits"]) == (0, 0)
    assert FORM.fullmatch(str(done["correlation_id"]))


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("logs", "purge_environment")
def test_the_purge_deletes_the_deposit_expired_and_its_object_after_its_transaction(
    database: Database, backups_bucket: Bucket, capsys: pytest.CaptureFixture[str]
) -> None:
    # « Un fichier déposé et jamais confirmé disparaît au terme du délai d'expiration » : the verb
    # deletes the row, validates, then the object.
    upload_id = uuid4()
    key = object_key_of(upload_id)
    backups_bucket.put(key, b"WF")
    user = holder(database)
    with database.transaction() as session:
        record_whole(session, upload_id, Whole("oublie.wft", 2, user), utc_now() - LIFETIME * 2)
    assert worker_main.main(["purge"]) == 0
    (done,) = records(capsys.readouterr().err)
    assert (done["event"], done["objects"]) == ("purge.done", 1)
    assert backups_bucket.size(key) is None
    with database.transaction() as session:
        assert session.get(FileUpload, upload_id) is None


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("logs", "purge_environment")
def test_a_purge_whose_storage_does_not_answer_still_purges_the_rows_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database: Database,
) -> None:
    # The storage out of reach is no reason to keep the rows: what it holds, the next pass sweeps.
    monkeypatch.setenv("WATERFALL_STORAGE_ADDRESS", "http://127.0.0.1:9")
    upload_id = uuid4()
    user = holder(database)
    with database.transaction() as session:
        record_whole(session, upload_id, Whole("oublie.wft", 2, user), utc_now() - LIFETIME * 2)
    assert worker_main.main(["purge"]) == 0
    said = [(each["event"], each.get("objects")) for each in records(capsys.readouterr().err)]
    assert said == [
        ("purge.storage_unlisted", None),
        ("purge.storage_unavailable", None),
        ("purge.done", 1),
    ]
    with database.transaction() as session:
        assert session.get(FileUpload, upload_id) is None


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("logs", "database", "purge_environment")
@pytest.mark.parametrize(("hours", "expected"), [(None, 12), ("3", 3)])
def test_the_history_of_a_session_is_kept_for_the_hours_the_settings_say_twelve_by_default(
    hours: str | None, expected: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The entries of a session older than ``WATERFALL_UNDO_RETENTION_HOURS`` are purged.
    if hours is not None:
        monkeypatch.setenv("WATERFALL_UNDO_RETENTION_HOURS", hours)
    called: list[tuple[datetime, datetime]] = []

    def purge(_session: Session, *, before: datetime, now: datetime) -> None:
        called.append((before, now))

    monkeypatch.setattr(worker_main.history_interface, "purge", purge)
    assert worker_main.main(["purge"]) == 0
    ((before, now),) = called
    assert now - before == timedelta(hours=expected)


@pytest.mark.usefixtures("logs", "purge_environment")
def test_a_purge_that_cannot_reach_the_database_ends_in_failure_said_in_its_logs(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    unreachable = "postgresql+psycopg://waterfall:s3cret-of-the-purge@127.0.0.1:9/waterfall"
    monkeypatch.setenv("WATERFALL_DATABASE_URL", unreachable)
    assert worker_main.main(["purge"]) == 1
    err = capsys.readouterr().err
    (failed,) = records(err)
    assert (failed["event"], failed["actor"]) == ("purge.failed", "platform")
    assert "s3cret-of-the-purge" not in err
