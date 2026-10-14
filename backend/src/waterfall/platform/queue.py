# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The queue of the background tasks: a stream of Redis, read by one group of workers (PBS-3.2).

An entry carries the identifier of a task, which lives in the database: Redis keeps nothing
durable. An entry read stays pending until acknowledged; a worker that stops leaves it pending, and
another claims it once idle long enough (``XAUTOCLAIM``). An entry acknowledged is deleted: the
stream names only what may still have to run. The restorations have a stream of their own, beside
that of the worker, which the service of the restoration alone reads (#953).
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Self, cast
from uuid import UUID

import redis
from redis import Redis
from redis.exceptions import ResponseError

STREAM = "waterfall:tasks"
# What follows the name of the stream of the tasks in that of the stream of the restorations.
RESTORES = ":restores"
GROUP = "workers"
FIELD = "task_id"
# How long a deposit waits for Redis, in seconds, when a request or the schedule makes it: a deposit
# lost is deposited again by the worker, a request held keeps its caller waiting.
DEPOSIT_TIMEOUT = 1.0
# How long a socket of the worker waits for Redis, in seconds: more than a read of the worker waits.
WORKER_TIMEOUT = 10.0
# Where a sweep of the entries left pending starts, and what Redis gives back once it has ended.
SWEEP_START = "0-0"

type RawEntry = tuple[str, Mapping[str, str] | None]


@dataclass(frozen=True, slots=True)
class Entry:
    """An entry of the stream, and the task it names; ``None`` if it names none that can be read."""

    entry_id: str
    task_id: UUID | None


def _task_of(fields: Mapping[str, str] | None) -> UUID | None:
    try:
        return UUID((fields or {}).get(FIELD, ""))
    except ValueError:
        return None


def _entries(raw: Iterable[Any]) -> list[Entry]:
    return [Entry(entry_id, _task_of(fields)) for entry_id, fields in cast("list[RawEntry]", raw)]


class TaskQueue:
    """The stream of the tasks, as the API deposits in it and the workers read it."""

    def __init__(self, client: Redis, stream: str = STREAM) -> None:
        self.client = client
        self.stream = stream

    @classmethod
    def connect(cls, address: str, stream: str = STREAM, *, timeout: float) -> Self:
        """Open the queue on the Redis an address designates, waiting for it ``timeout`` at most.

        Each opener says how long it waits: a request ``DEPOSIT_TIMEOUT``, the worker
        ``WORKER_TIMEOUT``.
        """
        client = redis.from_url(
            address, decode_responses=True, socket_timeout=timeout, socket_connect_timeout=timeout
        )
        return cls(client, stream)

    def restores(self) -> "TaskQueue":
        """Give the stream of the restorations of this queue, in its Redis (#953)."""
        return TaskQueue(self.client, self.stream + RESTORES)

    def deposit(self, task_id: UUID) -> None:
        """Put a task at the end of the queue."""
        self.client.xadd(self.stream, {FIELD: str(task_id)})

    def prepare(self) -> None:
        """Create the stream and the group of the workers, unless they exist.

        The group reads the stream from its start: what was deposited before it existed runs too.
        """
        try:
            self.client.xgroup_create(self.stream, GROUP, id="0", mkstream=True)
        except ResponseError as error:
            if not str(error).startswith("BUSYGROUP"):
                raise

    def read(self, consumer: str, block_ms: int) -> list[Entry]:
        """Take the next entry nobody has read, waiting for one at most ``block_ms``."""
        answer = self.client.xreadgroup(
            GROUP, consumer, {self.stream: ">"}, count=1, block=block_ms
        )
        streams = cast("list[tuple[str, list[RawEntry]]]", answer)
        return [entry for _, raw in streams for entry in _entries(raw)]

    def reclaim(
        self, consumer: str, idle_ms: int, start: str = SWEEP_START
    ) -> tuple[str, list[Entry]]:
        """Take over the next entry another consumer has left pending for ``idle_ms`` at least.

        Redis looks at a few pending entries from ``start`` on, and gives where to look next:
        ``SWEEP_START`` once it has looked at them all. A sweep that always started again from the
        first would never reach an idle entry behind recent ones.
        """
        answer = self.client.xautoclaim(self.stream, GROUP, consumer, idle_ms, start, count=1)
        return answer[0], _entries(answer[1])

    def acknowledge(self, entry_id: str) -> None:
        """Say an entry done, and delete it from the stream."""
        self.client.xack(self.stream, GROUP, entry_id)
        self.client.xdel(self.stream, entry_id)

    def waiting(self) -> set[UUID]:
        """Give the tasks the stream still names: deposited, and not acknowledged."""
        entries = _entries(self.client.xrange(self.stream) or [])
        return {entry.task_id for entry in entries if entry.task_id}

    def close(self) -> None:
        """Close the connections."""
        self.client.close()
