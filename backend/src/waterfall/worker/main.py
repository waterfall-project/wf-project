# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the worker, and of the command that schedules its tasks.

``waterfall-worker`` runs the tasks of the queue until it is stopped (WF-ARC-0090), and serves its
metrics meanwhile (WF-OBS-0010); ``waterfall-worker schedule`` is the one command the planners
call: it deposits the tasks the platform schedules that are due — the reading of the accounts, the
purge — unless one of their kind is pending (PBS-5.3), and runs none (EP-13, "Une commande planifiée
unique"). Each stops at start, naming the variable that lacks, rather than starting without its
settings (WF-SEC-0010).
"""

import signal
import sys
from typing import TYPE_CHECKING

from waterfall import __version__, schema
from waterfall.core.costs import interface as costs_interface
from waterfall.core.estimate import interface as estimate_interface
from waterfall.core.exchanges import interface as exchanges_interface
from waterfall.core.history import interface as history_interface
from waterfall.core.indicators import interface as indicators_interface
from waterfall.core.planning import interface as planning_interface
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.metrics import Announced, MetricsRegistry, WorkerMetrics
from waterfall.platform.queue import DEPOSIT_TIMEOUT, WORKER_TIMEOUT, TaskQueue
from waterfall.platform.settings import (
    ENV_PREFIX,
    ScheduleSettings,
    Settings,
    SettingsError,
    WorkerSettings,
    load_schedule_settings,
    load_worker_settings,
)
from waterfall.worker import exchanges
from waterfall.worker.backup import BackupTask
from waterfall.worker.identity_sync import IdentitySync
from waterfall.worker.marking import mark
from waterfall.worker.purge import PurgeTask
from waterfall.worker.restore_test import RestoreTestJob
from waterfall.worker.runner import Worker
from waterfall.worker.schedule import deposit_due, planned

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from waterfall.platform.tasks import TaskHandler

NAME = "waterfall-worker"
USAGE = f"usage: {NAME} [--version | schedule]\n"
# The modules that fill the registries of the others at the import of their interface (#2180):
# imported here, so that no revision the worker marks or creates, no import it applies, lacks
# their part — the estimate keeps its images and its rates at the marking (US-1500/L2); the actual
# costs register the format of an extraction, which the worker analyses and applies, and answer
# whether a subproject bears costs to the import of an estimate it applies (US-1610/L2); the
# indicators keep theirs at the marking (US-1670/L1).
EXTENDING = (
    costs_interface,
    estimate_interface,
    exchanges_interface,
    history_interface,
    indicators_interface,
    planning_interface,
)


def handlers(
    settings: WorkerSettings, metrics: WorkerMetrics | None = None
) -> dict[str, TaskHandler]:
    """Give what the worker runs, by kind of task: a backup, the reading of the accounts, a purge.

    The marking is the first task of the trade (US-0970); the analysis and the application of an
    import and an export are the exchanges' (EP-06). The reading of the accounts counts in
    ``metrics`` the directories it could not read (#917). The purge is the task of what expired,
    which the schedule deposits (EP-13, "Une commande planifiée unique"); the test of a restoration,
    under Kubernetes alone, the Job the settings name (US-2930).
    """
    imports = exchanges.ImportTasks.of(settings)
    run: dict[str, TaskHandler] = {
        "backup": BackupTask.of(settings),
        "identity_sync": IdentitySync.of(settings, metrics),
        "revision_mark": mark,
        "import_analysis": imports.analyse,
        "import_apply": imports.apply,
        "export": exchanges.ExportTask.of(settings),
        "purge": PurgeTask.of(settings),
    }
    if settings.restore_test_job is not None:
        run["restore_test"] = RestoreTestJob.of(settings.restore_test_job)
    return run


logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker, or deposit the tasks due, or say why not; a wrong argument returns 2."""
    schema.declared()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if not arguments:
        return _started(load_worker_settings, _work)
    if arguments == ["schedule"]:
        return _started(load_schedule_settings, _schedule)
    sys.stderr.write(f"{USAGE}{NAME}: unexpected arguments: {' '.join(arguments)}\n")
    return 2


def _started[Kind: Settings](load: Callable[[], Kind], run: Callable[[Kind], int]) -> int:
    """Read the settings, or say which variable lacks (2); then set the logs and run."""
    try:
        settings = load()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    return run(settings)


def serve(worker: Worker) -> int:
    """Run a worker until it is stopped: ``SIGTERM`` stops it where it stands, its task undone.

    An error it does not expect — Redis or the database out of reach — ends it (1), said in the
    structured logs, its secrets masked, and not as a bare trace.
    """
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("worker.stopped")
    except Exception:
        logger.exception("worker.failed")
        return 1
    return 0


def _work(settings: WorkerSettings) -> int:
    logger.info("worker.starting", version=__version__)
    registry = MetricsRegistry()
    metrics = WorkerMetrics(registry)
    # Its version, which the status screen presents beside the API's (WF-EXP-0030).
    registry.read_at_collection.append(Announced("worker", __version__))
    # The worker listens to nothing but its metrics, on a port of their own (WF-OBS-0010); a port
    # that cannot be taken is said, as a setting is, before anything is opened.
    try:
        stop_metrics = registry.serve(settings.host, settings.metrics_port)
    except OSError as error:
        sys.stderr.write(
            f"{NAME}: {ENV_PREFIX}METRICS_PORT: cannot listen on "
            f"{settings.host}:{settings.metrics_port}: {error.strerror or error}\n"
        )
        return 2
    try:
        return _run(settings, metrics)
    finally:
        stop_metrics()


def _run(settings: WorkerSettings, metrics: WorkerMetrics) -> int:
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    try:
        TIME_ZONE.read_from(stored_in(database))
        queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=WORKER_TIMEOUT)
        try:
            return serve(Worker(database, queue, handlers(settings, metrics)).count_in(metrics))
        finally:
            queue.close()
    finally:
        database.dispose()


def _schedule(settings: ScheduleSettings) -> int:
    """Deposit what is due for the platform, under a correlation of its own.

    An error it does not expect ends it (1), said in the structured logs, as the worker's does.
    """
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=DEPOSIT_TIMEOUT)
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            try:
                deposit_due(database, queue, planned(settings))
            except Exception:
                logger.exception("schedule.failed")
                return 1
            return 0
    finally:
        queue.close()
        database.dispose()


if __name__ == "__main__":
    sys.exit(main())
