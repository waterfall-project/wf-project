# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the worker, and of the command that schedules a task.

``waterfall-worker`` runs the tasks of the queue until it is stopped (WF-ARC-0090);
``waterfall-worker enqueue <kind>`` deposits a task the platform schedules, unless one of that kind
is pending (PBS-5.3); ``waterfall-worker purge`` purges what expired — imports, deposits, exports,
history — under a lock of its own (EP-06, "La purge"). Each stops at start, naming the variable that
lacks, rather than starting without its settings (WF-SEC-0010).
"""

import signal
import sys
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall import __version__, schema
from waterfall.core.costs import interface as costs_interface
from waterfall.core.estimate import interface as estimate_interface
from waterfall.core.exchanges import interface as exchanges_interface
from waterfall.core.history import interface as history_interface
from waterfall.core.planning import interface as planning_interface
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.queue import DEPOSIT_TIMEOUT, WORKER_TIMEOUT, TaskQueue
from waterfall.platform.settings import (
    PurgeSettings,
    Settings,
    SettingsError,
    WorkerSettings,
    load_purge_settings,
    load_settings,
    load_worker_settings,
)
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import TaskHandler, TaskKind, pending_task, submit
from waterfall.worker import exchanges
from waterfall.worker.backup import BackupTask
from waterfall.worker.identity_sync import IdentitySync
from waterfall.worker.marking import mark
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

NAME = "waterfall-worker"
USAGE = f"usage: {NAME} [--version | enqueue <kind> | purge]\n"
# The modules that fill the registries of the others at the import of their interface (#2180):
# imported here, so that no revision the worker marks or creates, no import it applies, lacks
# their part — the estimate keeps its images and its rates at the marking (US-1500/L2); the actual
# costs register the format of an extraction, which the worker analyses and applies, and answer
# whether a subproject bears costs to the import of an estimate it applies (US-1610/L2).
EXTENDING = (
    costs_interface,
    estimate_interface,
    exchanges_interface,
    history_interface,
    planning_interface,
)


def handlers(settings: WorkerSettings) -> dict[str, TaskHandler]:
    """Give what the worker runs, by kind of task: a backup, the reading of the accounts, a marking.

    The marking is the first task of the trade (US-0970); the analysis and the application of an
    import and an export are the exchanges' (EP-06).
    """
    imports = exchanges.ImportTasks.of(settings)
    return {
        "backup": BackupTask.of(settings),
        "identity_sync": IdentitySync.of(settings),
        "revision_mark": mark,
        "import_analysis": imports.analyse,
        "import_apply": imports.apply,
        "export": exchanges.ExportTask.of(settings),
    }


# The kinds the platform schedules (PBS-5.3); the scheduled backup comes with EP-13.
SCHEDULED: tuple[TaskKind, ...] = ("identity_sync",)
# The key of the advisory lock under which a schedule looks for a pending task, then deposits.
SCHEDULE_LOCK = 3_700_010
# The key of the advisory lock of a purge: two purges never run together.
PURGE_LOCK = 3_700_020

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker, or schedule a task, or say why not; a wrong argument returns 2."""
    schema.declared()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if not arguments:
        return _started(load_worker_settings, _work)
    match arguments:
        case ["enqueue", kind] if kind in SCHEDULED:
            return _started(load_settings, lambda settings: _enqueue(settings, kind))
        case ["purge"]:
            return _started(load_purge_settings, _purge)
        case ["enqueue", kind]:
            fault = f"not a kind the platform schedules: {kind}"
        case _:
            fault = f"unexpected arguments: {' '.join(arguments)}"
    sys.stderr.write(f"{USAGE}{NAME}: {fault}\n")
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
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=WORKER_TIMEOUT)
    try:
        return serve(Worker(database, queue, handlers(settings)))
    finally:
        queue.close()
        database.dispose()


def _enqueue(settings: Settings, kind: TaskKind) -> int:
    """Deposit a task of ``kind`` for the platform, under a correlation of its own."""
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=DEPOSIT_TIMEOUT)
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            return _schedule(database, queue, kind)
    finally:
        queue.close()
        database.dispose()


def _schedule(database: Database, queue: TaskQueue, kind: TaskKind) -> int:
    """Deposit a task of ``kind``, unless one is pending; the lock keeps two schedules apart.

    An error it does not expect ends it (1), said in the structured logs, as the worker's does.
    """
    try:
        with database.transaction() as session:
            session.execute(select(func.pg_advisory_xact_lock(SCHEDULE_LOCK)))
            pending = pending_task(session, kind)
            deposited = submit(session, queue, kind, None) if pending is None else None
    except Exception:
        logger.exception("task.enqueue_failed", kind=kind)
        return 1
    event = "task.already_pending" if deposited is None else "task.enqueued"
    logger.info(event, kind=kind, task_id=str(pending or deposited))
    return 0


def _stored(bucket: Bucket, now: datetime) -> exchanges_interface.Stored:
    """List the old objects of the prefixes the purge sweeps; a storage out of reach lists none.

    The rows are purged all the same: what the storage keeps, the next pass sweeps.
    """
    try:
        return exchanges_interface.stored_before(bucket, now)
    except UnavailableError:
        logger.warning("purge.storage_unlisted")
        return exchanges_interface.Stored()


def _purge(settings: PurgeSettings) -> int:
    """Purge what expired, under a correlation of its own; an unexpected error ends it (1).

    The rows are purged in one transaction, under the advisory lock of the purge; the storage
    loses what they designated once it is validated, never before: an object is not deleted for a
    row a failed transaction keeps. The old objects of the storage are listed before the lock.
    """
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    bucket = Bucket.of_backups(settings)
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            now = utc_now()
            stored = _stored(bucket, now)
            try:
                with database.transaction() as session:
                    session.execute(select(func.pg_advisory_xact_lock(PURGE_LOCK)))
                    purged = exchanges_interface.purge(session, now, stored)
                    history_interface.purge(
                        session,
                        before=now - timedelta(hours=settings.undo_retention_hours),
                        now=now,
                    )
            except Exception:
                logger.exception("purge.failed")
                return 1
            exchanges_interface.remove_purged(bucket, purged)
            logger.info("purge.done", objects=len(purged.objects), deposits=len(purged.deposits))
            return 0
    finally:
        database.dispose()


if __name__ == "__main__":
    sys.exit(main())
