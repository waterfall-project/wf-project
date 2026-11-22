# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration under Kubernetes: planned and started by the schedule, by its Job.

The schedule makes the Job the chart describes once a scheduled backup verified is there to test,
then at the interval the chart gives, and never under Compose, which gives no Job; it writes the
task ``restore_test``, ended, naming the Job, by which it knows when the next is due. The API of
Kubernetes is answered here by a server of the test, as the cluster would.
"""

import json
import ssl
import threading
from dataclasses import replace
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, ClassVar, override
from uuid import UUID

import pytest
from backup_rows import Row, recorded
from sqlalchemy import select, update

from waterfall.platform.authority import made
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ScheduleSettings
from waterfall.platform.tasks import BackgroundTask, purge_ended
from waterfall.worker.restore_test import (
    Jobs,
    KubernetesError,
    RestoreTestJob,
    named,
    start_restore_test,
)
from waterfall.worker.schedule import Planned, deposit_due, every, planned, restore_test_planned

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

pytestmark = pytest.mark.story("US-2930")

MONTH = 30 * 24 * 3600
TASK = UUID("0193a0b2-4c5d-7e6f-8a9b-0c1d2e3f4a5b")
JOBS = "/apis/batch/v1/namespaces/waterfall/jobs"
MANIFEST: dict[str, Any] = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {"name": "waterfall-restore-test", "labels": {"component": "restore-test"}},
    "spec": {"ttlSecondsAfterFinished": 0},
}
GIVEN = ScheduleSettings.model_construct(
    purge_interval=600, restore_test_job="/restore-test/job.json", restore_test_interval=MONTH
)


class Answer(BaseHTTPRequestHandler):
    """The API of Kubernetes, as the test serves it: it keeps what it is sent, says ``status``."""

    received: ClassVar[list[tuple[str, str, dict[str, Any]]]] = []
    status: ClassVar[int] = 201

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        self.received.append((self.path, self.headers.get("Authorization", ""), body))
        self.send_response(self.status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    @override
    def log_message(self, format: str, *args: Any) -> None:
        """Write nothing."""


@pytest.fixture
def api() -> Iterator[str]:
    Answer.received.clear()
    Answer.status = 201
    server = ThreadingHTTPServer(("127.0.0.1", 0), Answer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def account_in(folder: Path, token: str) -> Path:
    """Write what Kubernetes mounts of a service account: its token, its namespace, its roots."""
    folder.mkdir()
    (folder / "token").write_text(f"{token}\n", encoding="utf-8")
    (folder / "namespace").write_text("waterfall\n", encoding="utf-8")
    (folder / "ca.crt").write_bytes(made(utc_now()).pem())
    return folder


def manifest_in(folder: Path) -> Path:
    """Write the Job as the chart mounts it."""
    manifest = folder / "job.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    return manifest


@pytest.fixture
def plan(tmp_path: Path, api: str) -> tuple[Planned, ...]:
    """Plan the test as the chart does, its Job made by the API the test serves."""
    manifest = str(manifest_in(tmp_path))
    account = account_in(tmp_path / "account", "token")
    (test,) = restore_test_planned(GIVEN)

    def start(session: Session) -> UUID | None:
        return start_restore_test(session, manifest, account, api)

    return (replace(test, start=start),)


def started(database: Database) -> list[tuple[str, Any, Any, Any]]:
    """Read the tasks of the tests started: their state, their requester and their result."""
    task = BackgroundTask
    with database.transaction() as session:
        rows = session.execute(
            select(task.status, task.requested_by, task.result).where(task.kind == "restore_test")
        ).all()
    return [("restore_test", *row) for row in rows]


def test_without_its_job_the_test_is_not_planned_as_under_compose() -> None:
    kinds = {each.kind for each in planned(ScheduleSettings.model_construct(purge_interval=600))}
    assert "restore_test" not in kinds
    assert [each.kind for each in planned(GIVEN)][-1] == "restore_test"
    assert ScheduleSettings.model_construct().restore_test_interval == MONTH


@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_schedule_starts_the_test_once_a_backup_is_there_to_test_and_once_an_interval(
    database: Database, queue: TaskQueue, logs: Logs, plan: tuple[Planned, ...]
) -> None:
    # « Un test de restauration mensuel est exécuté » : without a scheduled backup verified the
    # test would restore nothing, and is held back — a manual one, or one whose verification
    # failed, does not count; then the schedule makes its Job, and writes its task, ended.
    taken_at = utc_now() - timedelta(hours=2)
    recorded(database, taken_at, Row(origin="manual"))
    recorded(database, taken_at, Row(origin="scheduled", verification="failed"))
    with logging_context(correlation_id="restore-test-planned"):
        assert deposit_due(database, queue, plan) == []
    held = logs.named("task.held_back")
    assert [each["missing_condition"] for each in held] == ["scheduled_backup_verified"]
    assert Answer.received == []
    recorded(database, taken_at, Row(origin="scheduled"))
    with logging_context(correlation_id="restore-test-planned"):
        assert deposit_due(database, queue, plan) == ["restore_test"]
    ((path, _, job),) = Answer.received
    assert path == JOBS
    name = job["metadata"]["name"]
    assert name.startswith("waterfall-restore-test-")
    assert started(database) == [("restore_test", "succeeded", None, {"job": name})]
    (made_log,) = logs.named("restore_test.job_made")
    assert made_log["job"] == name
    # Nothing goes to the queue: no worker runs the test.
    assert queue.waiting() == set()
    # The next is due a month after the latest was started, not before.
    with logging_context(correlation_id="restore-test-planned"):
        assert deposit_due(database, queue, plan) == []
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.kind == "restore_test")
            .values(submitted_at=utc_now() - timedelta(seconds=MONTH))
        )
    with logging_context(correlation_id="restore-test-planned"):
        assert deposit_due(database, queue, plan) == ["restore_test"]
    assert len(Answer.received) == 2
    assert len(started(database)) == 2


@pytest.mark.requirement("WF-EXP-0060-A")
@pytest.mark.parametrize("status", [403, 500])
def test_a_job_the_cluster_refuses_writes_no_task_and_the_test_stays_due(
    database: Database, queue: TaskQueue, logs: Logs, plan: tuple[Planned, ...], status: int
) -> None:
    # A Role missing, a quota, the API down: the test did not start, nothing says it did, and the
    # next schedule asks again; the other kinds of the schedule are deposited all the same.
    with_purge = (every("purge", 600), *plan)
    recorded(database, utc_now() - timedelta(hours=2), Row(origin="scheduled"))
    Answer.status = status
    with logging_context(correlation_id="restore-test-refused"):
        assert deposit_due(database, queue, with_purge) == ["purge"]
    assert started(database) == []
    (refused,) = logs.named("restore_test.job_not_made")
    assert f"answered {status}" in refused["exception"]
    Answer.status = 201
    with logging_context(correlation_id="restore-test-refused"):
        assert deposit_due(database, queue, with_purge) == ["restore_test"]
    assert len(Answer.received) == 2


def test_a_job_that_cannot_be_read_starts_no_test_and_says_so(
    database: Database, logs: Logs, tmp_path: Path, api: str
) -> None:
    account = account_in(tmp_path / "account", "token")
    with database.transaction() as session, logging_context(correlation_id="restore-test-file"):
        assert start_restore_test(session, str(tmp_path / "absent.json"), account, api) is None
    assert started(database) == []
    assert len(logs.named("restore_test.job_not_made")) == 1
    assert Answer.received == []


class Cluster:
    """What a fake API of Kubernetes answers to the creation of a Job, and what it was sent."""

    def __init__(self, status: int) -> None:
        self.status = status
        self.sent: list[tuple[str, Mapping[str, Any]]] = []

    def send(self, path: str, body: Mapping[str, Any]) -> int:
        self.sent.append((path, body))
        return self.status


def test_the_job_is_named_after_its_task_and_keeps_the_rest_of_its_manifest() -> None:
    job = named(MANIFEST, TASK)
    assert job["metadata"] == {
        "name": "waterfall-restore-test-0193a0b2",
        "labels": {"component": "restore-test"},
    }
    assert job["spec"] == MANIFEST["spec"]
    assert MANIFEST["metadata"]["name"] == "waterfall-restore-test"


@pytest.mark.requirement("WF-EXP-0060-A")
def test_a_job_whose_name_the_cluster_holds_is_taken_as_made(
    database: Database, logs: Logs
) -> None:
    run = RestoreTestJob(MANIFEST, Jobs("waterfall", Cluster(409).send))
    with database.transaction() as session, logging_context(correlation_id="restore-test-409"):
        task_id = run.start(session)
    (said,) = logs.named("restore_test.job_already_made")
    assert said["task_id"] == str(task_id)
    assert started(database) == [("restore_test", "succeeded", None, {"job": said["job"]})]


@pytest.mark.parametrize("status", [400, 403, 500])
def test_a_job_the_cluster_refuses_is_said_refused(status: int) -> None:
    jobs = Jobs("waterfall", Cluster(status).send)
    with pytest.raises(KubernetesError, match=f"answered {status}"):
        jobs.create(MANIFEST)


def test_the_purge_spares_the_latest_test_started_so_a_short_retention_does_not_make_it_due(
    database: Database, plan: tuple[Planned, ...]
) -> None:
    # A retention of the tasks shorter than the interval of the test would, if the purge took the
    # latest task, make the test due again at each purge: it spares the latest of the kind.
    for days in (40, 10):
        with database.transaction() as session, logging_context(correlation_id="retention"):
            task_id = RestoreTestJob(MANIFEST, Jobs("waterfall", Cluster(201).send)).start(session)
            back = utc_now() - timedelta(days=days)
            session.execute(
                update(BackgroundTask)
                .where(BackgroundTask.id == task_id)
                .values(submitted_at=back, started_at=back, finished_at=back)
            )
    with database.transaction() as session:
        assert purge_ended(session, utc_now(), ()) == 1
        assert plan[0].due(session, utc_now()) is False
    assert len(started(database)) == 1


def test_the_schedule_reaches_the_api_as_its_service_account_the_token_read_at_each_request(
    tmp_path: Path, api: str
) -> None:
    account = account_in(tmp_path / "account", "first")
    jobs = Jobs.in_cluster(account, api)
    assert jobs.namespace == "waterfall"
    assert jobs.create(MANIFEST) is True
    (account / "token").write_text("renewed\n", encoding="utf-8")
    assert jobs.create(MANIFEST) is True
    assert [(path, said) for path, said, _ in Answer.received] == [
        (JOBS, "Bearer first"),
        (JOBS, "Bearer renewed"),
    ]
    assert Answer.received[0][2] == MANIFEST


def test_the_job_is_read_from_the_file_the_chart_mounts(tmp_path: Path) -> None:
    manifest = manifest_in(tmp_path)
    account = account_in(tmp_path / "account", "token")
    run = RestoreTestJob.of(str(manifest), account)
    assert run.manifest == MANIFEST
    assert run.jobs.namespace == "waterfall"


def test_an_authority_that_does_not_read_is_said_at_the_start(tmp_path: Path) -> None:
    account = account_in(tmp_path / "account", "token")
    (account / "ca.crt").write_text("not a certificate", encoding="utf-8")
    with pytest.raises(ssl.SSLError):
        Jobs.in_cluster(account, "https://kubernetes.default.svc")
