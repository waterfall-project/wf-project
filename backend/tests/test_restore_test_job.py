# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration under Kubernetes: planned by the schedule, its Job made by the worker.

The schedule deposits the task ``restore_test`` at the interval the chart gives, once a scheduled
backup verified is there to test, and never under Compose, which gives none; the worker makes the
Job the chart describes, named after its task, by the API of Kubernetes, which a server of the test
answers here as the cluster would.
"""

import json
import ssl
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, ClassVar, cast, override
from uuid import UUID

import pytest
from backup_rows import Row, recorded
from sqlalchemy import select, update

from waterfall.platform.authority import made
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ScheduleSettings
from waterfall.platform.tasks import BackgroundTask, Task
from waterfall.worker.restore_test import (
    Jobs,
    KubernetesError,
    RestoreTestJob,
    named,
)
from waterfall.worker.schedule import deposit_due, planned, restore_test_planned

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
# The handler reads no row: the test is made by the Job, and inscribes its outcome itself.
NO_SESSION = cast("Session", None)
MANIFEST: dict[str, Any] = {
    "apiVersion": "batch/v1",
    "kind": "Job",
    "metadata": {"name": "waterfall-restore-test", "labels": {"component": "restore-test"}},
    "spec": {"ttlSecondsAfterFinished": 0},
}


def task_of(task_id: UUID = TASK) -> Task:
    return Task(task_id, "restore_test", {}, None, "test-restore-test-job", 1)


def deposited_kinds(database: Database) -> list[str]:
    with database.transaction() as session:
        return list(session.scalars(select(BackgroundTask.kind).order_by(BackgroundTask.kind)))


def test_without_its_interval_the_test_is_not_planned_as_under_compose() -> None:
    kinds = {each.kind for each in planned(ScheduleSettings.model_construct(purge_interval=600))}
    assert "restore_test" not in kinds
    given = ScheduleSettings.model_construct(purge_interval=600, restore_test_interval=MONTH)
    assert [each.kind for each in planned(given)][-1] == "restore_test"


def test_the_schedule_deposits_the_test_once_a_backup_is_there_to_test_and_once_an_interval(
    database: Database, queue: TaskQueue, logs: Logs
) -> None:
    # Without a scheduled backup verified the test would restore nothing: it is held back; a manual
    # one or one whose verification failed does not count.
    plan = restore_test_planned(
        ScheduleSettings.model_construct(purge_interval=600, restore_test_interval=MONTH)
    )
    taken_at = utc_now() - timedelta(hours=2)
    recorded(database, taken_at, Row(origin="manual"))
    recorded(database, taken_at, Row(origin="scheduled", verification="failed"))
    with logging_context(correlation_id="restore-test-planned"):
        assert deposit_due(database, queue, plan) == []
    held = logs.named("task.held_back")
    assert [each["missing_condition"] for each in held] == ["scheduled_backup_verified"]
    recorded(database, taken_at, Row(origin="scheduled"))
    with logging_context(correlation_id="restore-test-planned"):
        assert deposit_due(database, queue, plan) == ["restore_test"]
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.kind == "restore_test")
            .values(status="succeeded", progress=100, started_at=utc_now(), finished_at=utc_now())
        )
    # Ended, the next is due a month after it was deposited, not before.
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
    assert deposited_kinds(database).count("restore_test") == 2


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


def test_the_worker_makes_the_job_in_its_namespace_once_whatever_the_attempts(logs: Logs) -> None:
    # Made, then refused by its name (409) when the task is taken again: made once, both succeed.
    cluster = Cluster(201)
    run = RestoreTestJob(MANIFEST, Jobs("waterfall", cluster.send))
    assert run(NO_SESSION, task_of()) == {"job": "waterfall-restore-test-0193a0b2"}
    cluster.status = 409
    assert run(NO_SESSION, task_of()) == {"job": "waterfall-restore-test-0193a0b2"}
    assert [path for path, _ in cluster.sent] == ["/apis/batch/v1/namespaces/waterfall/jobs"] * 2
    assert len(logs.named("restore_test.job_made")) == 1
    assert len(logs.named("restore_test.job_already_made")) == 1


@pytest.mark.parametrize("status", [400, 403, 500])
def test_a_job_the_cluster_refuses_fails_the_task(status: int) -> None:
    run = RestoreTestJob(MANIFEST, Jobs("waterfall", Cluster(status).send))
    with pytest.raises(KubernetesError, match=f"answered {status}"):
        run(NO_SESSION, task_of())


class Answer(BaseHTTPRequestHandler):
    """The API of Kubernetes, as the test serves it: it keeps what it is sent, answers 201."""

    received: ClassVar[list[tuple[str, str, dict[str, Any]]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        self.received.append((self.path, self.headers.get("Authorization", ""), body))
        self.send_response(201)
        self.send_header("Content-Length", "0")
        self.end_headers()

    @override
    def log_message(self, format: str, *args: Any) -> None:
        """Write nothing."""


@pytest.fixture
def api() -> Iterator[str]:
    Answer.received.clear()
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


def test_the_worker_reaches_the_api_as_its_service_account_the_token_read_at_each_request(
    tmp_path: Path, api: str
) -> None:
    account = account_in(tmp_path / "account", "first")
    jobs = Jobs.in_cluster(account, api)
    assert jobs.namespace == "waterfall"
    assert jobs.create(MANIFEST) is True
    (account / "token").write_text("renewed\n", encoding="utf-8")
    assert jobs.create(MANIFEST) is True
    assert [(path, said) for path, said, _ in Answer.received] == [
        ("/apis/batch/v1/namespaces/waterfall/jobs", "Bearer first"),
        ("/apis/batch/v1/namespaces/waterfall/jobs", "Bearer renewed"),
    ]
    assert Answer.received[0][2] == MANIFEST


def test_the_job_is_read_from_the_file_the_chart_mounts(tmp_path: Path) -> None:
    manifest = tmp_path / "job.json"
    manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
    account = account_in(tmp_path / "account", "token")
    run = RestoreTestJob.of(str(manifest), account)
    assert run.manifest == MANIFEST
    assert run.jobs.namespace == "waterfall"


def test_an_authority_that_does_not_read_is_said_at_the_start(tmp_path: Path) -> None:
    account = account_in(tmp_path / "account", "token")
    (account / "ca.crt").write_text("not a certificate", encoding="utf-8")
    with pytest.raises(ssl.SSLError):
        Jobs.in_cluster(account, "https://kubernetes.default.svc")
