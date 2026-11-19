# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The metrics of the worker: its tasks by kind and outcome, the directories the reading misses.

The worker runs here one step at a time on the queue of the test, its tasks counted in a registry
of its own, as ``waterfall-worker`` counts them in that of its process.
"""

from typing import TYPE_CHECKING

import httpx2
import pytest
from metrics_reading import samples, value
from task_handlers import Runs, deposit, task
from test_api_processes import free_port

from waterfall.platform.errors import UnprocessableError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.metrics import (
    DIRECTORY_SYNC_FAILURES,
    MetricsRegistry,
    WorkerMetrics,
)
from waterfall.worker.identity_sync import IdentitySync
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.keycloak_admin import RealmAccount
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.tasks import Task

AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
TASKS = "waterfall_worker_tasks_total"
DURATIONS = "waterfall_worker_task_duration_seconds_count"


def refuses(_session: Session, _task: Task) -> None:
    """Refuse the task, as a rule of the trade does."""
    code = "VALIDATION_FAILED"
    raise UnprocessableError(code)


class StoppedError(Exception):
    """The reading of the accounts stopped by the test, once the directories are synchronised."""


class FailingDirectories(KeycloakAdmin):
    """A provider that says it failed entries of its directories, then is not read further."""

    def synchronize_directories(self) -> int:
        """Say three entries failed, over the directories."""
        return 3

    def list_accounts(self) -> list[RealmAccount]:
        """Stop the reading: what follows the synchronisation is not this test's."""
        raise StoppedError


def test_the_tasks_are_counted_by_kind_and_outcome_with_how_long_they_ran(
    database: Database, queue: TaskQueue
) -> None:
    # Proper to US-2870: for the worker, the duration and the failure rate of the tasks by kind; a
    # task that no handler runs fails without running, and is counted without a duration.
    queue.prepare()
    registry = MetricsRegistry()
    handlers = {"identity_sync": Runs(), "backup": refuses}
    worker = Worker(database, queue, handlers, "worker-0", AT_ONCE).count_in(
        WorkerMetrics(registry)
    )
    for kind in ("identity_sync", "identity_sync", "backup", "export"):
        deposit(database, queue, kind=kind)
    while worker.step():
        pass
    read = samples(registry.expose().decode())
    assert value(read, TASKS, kind="identity_sync", outcome="succeeded") == 2
    assert value(read, TASKS, kind="backup", outcome="failed") == 1
    assert value(read, TASKS, kind="export", outcome="failed") == 1
    assert value(read, DURATIONS, kind="identity_sync") == 2
    assert value(read, DURATIONS, kind="backup") == 1
    assert value(read, DURATIONS, kind="export") is None


@pytest.mark.requirement("WF-OBS-0010-A")
def test_the_registry_of_a_process_answers_on_a_port_of_its_own() -> None:
    # « Le front, l'API et le worker répondent sur leur point de métriques. » : the worker, which
    # listens to nothing else, serves its registry on a port of its own, and stops serving it.
    registry = MetricsRegistry()
    WorkerMetrics(registry).task_ended("export", succeeded=True, seconds=1.5)
    port = free_port()
    stop = registry.serve("127.0.0.1", port)
    try:
        response = httpx2.get(f"http://127.0.0.1:{port}/metrics", timeout=10)
    finally:
        stop()
    assert response.status_code == 200
    read = samples(response.text)
    assert value(read, TASKS, kind="export", outcome="succeeded") == 1
    with pytest.raises(httpx2.TransportError):
        httpx2.get(f"http://127.0.0.1:{port}/metrics", timeout=1)


def test_the_entries_the_directories_failed_in_a_reading_of_the_accounts_are_counted(
    database: Database,
    queue: TaskQueue,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
) -> None:
    # Proper to US-2870: the failures of the synchronisation of the federated directories during a
    # reading of the accounts are carried by a metric (#917), whatever the reading becomes.
    registry = MetricsRegistry()
    metrics = WorkerMetrics(registry)
    reading = IdentitySync(FailingDirectories(keycloak, realm_settings), metrics=metrics)
    queue.prepare()
    worker = Worker(database, queue, {"identity_sync": reading}, "worker-0", AT_ONCE)
    task_id = deposit(database, queue)
    assert worker.count_in(metrics).step()
    assert task(database, task_id).status == "failed"
    read = samples(registry.expose().decode())
    assert value(read, f"{DIRECTORY_SYNC_FAILURES}_total") == 3
    assert value(read, TASKS, kind="identity_sync", outcome="failed") == 1
