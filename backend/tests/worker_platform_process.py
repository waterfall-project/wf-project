# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A worker of the tests with the handlers of the platform, in a process of its own.

``python worker_platform_process.py <stream> <consumer> <kind> <mode> <file>`` runs a worker on the
stream of a test, on the database and the Redis its environment names and on the bucket of the
tests (``WATERFALL_TEST_STORAGE_URL``, ``WATERFALL_TEST_BUCKET``), as ``waterfall-worker`` does,
``serve`` included. It runs the one kind of task given, by the handler of the platform — the
marking, the application of an import, whose format is the one of the tests (``imports_trial``).
In the mode ``stall`` it creates the file once the work is done and not committed, and waits to be
stopped; in the mode ``finish`` it ends the task.
"""

import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import pytest
from imports_trial import TrialFormat, stand_in

from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.queue import WORKER_TIMEOUT, TaskQueue
from waterfall.platform.storage import Bucket
from waterfall.worker.exchanges import ImportTasks
from waterfall.worker.main import serve
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task

# Longer than any test waits: the worker is stopped before.
STALL = 120


def main() -> int:
    """Run the worker of the test until it is stopped."""
    stream, consumer, kind, mode, file = sys.argv[1:]
    address = urlsplit(os.environ["WATERFALL_TEST_STORAGE_URL"])
    bucket = Bucket.connect(
        os.environ["WATERFALL_TEST_BUCKET"],
        f"{address.scheme}://{address.hostname}:{address.port}",
        "us-east-1",
        address.username or "",
        address.password or "",
    )
    stand_in(pytest.MonkeyPatch(), "remaining", TrialFormat())
    works: dict[str, Callable[[Session, Task], Mapping[str, Any] | None]] = {
        "revision_mark": mark,
        "import_apply": ImportTasks(bucket).apply,
    }
    work = works[kind]

    def handler(session: Session, task: Task) -> Mapping[str, Any] | None:
        result = work(session, task)
        if mode == "stall":
            Path(file).touch()
            time.sleep(STALL)
        return result

    database = Database(create_database_engine(os.environ["WATERFALL_DATABASE_URL"]))
    TIME_ZONE.read_from(stored_in(database))
    queue = TaskQueue.connect(os.environ["WATERFALL_REDIS_URL"], stream, timeout=WORKER_TIMEOUT)
    timing = Timing(claim_after=0, block=0.1)
    return serve(Worker(database, queue, {kind: handler}, consumer, timing))


if __name__ == "__main__":
    sys.exit(main())
