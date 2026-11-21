# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the backups share: a worker that runs them, and a bucket that damages them."""

from typing import TYPE_CHECKING

from waterfall.platform.storage import Bucket
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from uuid import UUID

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue
    from waterfall.worker.backup import BackupTask


type Run = Callable[[BackupTask], UUID]


def worker_of(database: Database, queue: TaskQueue, taking: BackupTask) -> Worker:
    """Give a worker of the queue of the test that runs the backups."""
    queue.prepare()
    return Worker(database, queue, {"backup": taking}, "worker-backup", Timing(0, 0.1))


class Corrupting(Bucket):
    """A bucket that gives back every object with bytes of its middle overwritten."""

    def download(self, key: str, path: Path) -> None:
        super().download(key, path)
        damaged = bytearray(path.read_bytes())
        middle = len(damaged) // 2
        damaged[middle : middle + 16] = b"\xff" * 16
        path.write_bytes(bytes(damaged))
