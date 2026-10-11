# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the worker, and of the command that schedules a task.

``waterfall-worker`` runs the tasks of the queue until it is stopped (WF-ARC-0090);
``waterfall-worker enqueue <kind>`` deposits a task the platform schedules, unless one of that kind
is pending (PBS-5.3). Each stops at start, naming the variable that lacks, rather than starting
without its settings (WF-SEC-0010).
"""

import signal
import sys
from collections.abc import Callable, Sequence

from sqlalchemy import func, select

from waterfall import __version__
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.queue import TaskQueue
from waterfall.platform.settings import (
    Settings,
    SettingsError,
    load_service_settings,
    load_settings,
)
from waterfall.platform.tasks import TaskHandler, TaskKind, pending_task, submit
from waterfall.worker.runner import Worker

NAME = "waterfall-worker"
USAGE = f"usage: {NAME} [--version | enqueue <kind>]\n"

# What the worker runs, by kind of task: the reading of the accounts comes with US-0370/L2.
HANDLERS: dict[str, TaskHandler] = {}
# The kinds the platform schedules (PBS-5.3); the scheduled backup comes with EP-13.
SCHEDULED: tuple[TaskKind, ...] = ("identity_sync",)
# The key of the advisory lock under which a schedule looks for a pending task, then deposits.
SCHEDULE_LOCK = 3_700_010

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker, or schedule a task, or say why not; a wrong argument returns 2."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if not arguments:
        return _started(load_service_settings, _work)
    match arguments:
        case ["enqueue", kind] if kind in SCHEDULED:
            return _started(load_settings, lambda settings: _enqueue(settings, kind))
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
    """Run a worker until it is stopped: ``SIGTERM`` stops it where it stands, its task undone."""
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        worker.run()
    except KeyboardInterrupt:
        logger.info("worker.stopped")
    return 0


def _work(settings: Settings) -> int:
    logger.info("worker.starting", version=__version__)
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value())
    try:
        return serve(Worker(database, queue, HANDLERS))
    finally:
        queue.close()
        database.dispose()


def _enqueue(settings: Settings, kind: TaskKind) -> int:
    """Deposit a task of ``kind`` for the platform, under a correlation of its own."""
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value())
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            with database.transaction() as session:
                session.execute(select(func.pg_advisory_xact_lock(SCHEDULE_LOCK)))
                pending = pending_task(session, kind)
                deposited = submit(session, queue, kind, None) if pending is None else None
            event = "task.already_pending" if deposited is None else "task.enqueued"
            logger.info(event, kind=kind, task_id=str(pending or deposited))
    finally:
        queue.close()
        database.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
