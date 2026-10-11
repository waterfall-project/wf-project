# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A worker of the tests, in a process of its own, for a test that stops it as the platform does.

``python worker_process.py <stream> <consumer> <mode> <file>`` runs a worker on the stream of a
test, on the database and the Redis its environment names, as ``waterfall-worker`` does — ``serve``
included. Its handler of the reading of the accounts inscribes its work; in the mode ``stall`` it
then creates the file, and waits to be stopped; in the mode ``finish`` it ends.
"""

import os
import sys
import time
from pathlib import Path

from sqlalchemy.orm import Session
from task_handlers import inscribe

from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import Task
from waterfall.worker.main import serve
from waterfall.worker.runner import Timing, Worker

# Longer than any test waits: the worker is stopped before.
STALL = 120


def main() -> int:
    """Run the worker of the test until it is stopped."""
    stream, consumer, mode, file = sys.argv[1:]

    def handler(session: Session, task: Task) -> None:
        inscribe(session, task)
        if mode == "stall":
            Path(file).touch()
            time.sleep(STALL)

    database = Database(create_database_engine(os.environ["WATERFALL_DATABASE_URL"]))
    queue = TaskQueue.connect(os.environ["WATERFALL_REDIS_URL"], stream)
    timing = Timing(claim_after=0, block=0.1)
    return serve(Worker(database, queue, {"identity_sync": handler}, consumer, timing))


if __name__ == "__main__":
    sys.exit(main())
