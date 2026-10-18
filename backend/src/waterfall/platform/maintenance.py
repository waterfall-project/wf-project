# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The maintenance of a restoration, kept out of the database the restoration makes again (#604).

While a restoration replaces the databases, the platform is in maintenance: the API answers every
operation but its probe of liveness with 503, and the worker runs no task. The state lives in Redis,
under a key of the platform that describes the task of the restoration: the service of the
restoration sets it before it touches a database, reads it to take up a restoration whose row the
database no longer holds — replaced, or not yet written back — (WF-ARC-0090), and removes it last.
The key is that of the stream of the tasks of the worker, with a suffix: the worker, the API and the
service of the restoration that share a Redis share its maintenance. The sessions of the front,
which Redis keeps under keys of its own, are closed by deleting them.
"""

import json
from dataclasses import dataclass
from typing import Any, Self, cast
from uuid import UUID

from redis import Redis

from waterfall.platform.queue import TaskQueue

# What follows the name of the stream of the tasks in the key of the maintenance.
SUFFIX = ":maintenance"
# The keys under which the front keeps its sessions and its sign-ins (``frontend/src/session``).
FRONT_SESSIONS = "wf:*"
# Delete the keys a pattern matches, page by page, in Redis itself.
FORGET_SESSIONS = """
local cursor, deleted = "0", 0
repeat
    local page = redis.call("SCAN", cursor, "MATCH", ARGV[1], "COUNT", 500)
    cursor = page[1]
    for _, key in ipairs(page[2]) do deleted = deleted + redis.call("DEL", key) end
until cursor == "0"
return deleted
"""


@dataclass(frozen=True, slots=True)
class Restoring:
    """The task of the restoration that holds the platform in maintenance, and its attempts.

    ``caches_cleared`` once an attempt has asked Keycloak to clear its caches: from then on, it may
    serve the realm of the backup, whose secrets are not the installation's, until the realm of
    the installation is applied again. ``abandoned`` once its attempts are spent: nothing takes it
    up again, and the maintenance stays, for an operator.
    """

    task_id: UUID
    payload: dict[str, Any]
    requested_by: UUID | None
    correlation_id: str
    attempts: int
    caches_cleared: bool = False
    abandoned: bool = False


class Maintenance:
    """The maintenance of the platform, as the service of the restoration sets and lifts it."""

    def __init__(self, client: Redis, key: str, sessions: str = FRONT_SESSIONS) -> None:
        self.client = client
        self.key = key
        self.sessions = sessions

    @classmethod
    def of(cls, queue: TaskQueue, sessions: str = FRONT_SESSIONS) -> Self:
        """Keep the maintenance beside the queue of the tasks, in its Redis."""
        return cls(queue.client, queue.stream + SUFFIX, sessions)

    def current(self) -> Restoring | None:
        """Give the restoration that holds the platform in maintenance, if one does."""
        held = self.client.get(self.key)
        if not isinstance(held, str):
            return None
        kept = json.loads(held)
        requested_by = kept["requested_by"]
        return Restoring(
            UUID(kept["task_id"]),
            kept["payload"],
            None if requested_by is None else UUID(requested_by),
            kept["correlation_id"],
            kept["attempts"],
            caches_cleared=kept.get("caches_cleared", False),
            abandoned=kept.get("abandoned", False),
        )

    def hold(self, restoring: Restoring) -> None:
        """Put the platform in maintenance for a restoration, or say one more of its attempts."""
        kept = {
            "task_id": str(restoring.task_id),
            "payload": restoring.payload,
            "requested_by": None if restoring.requested_by is None else str(restoring.requested_by),
            "correlation_id": restoring.correlation_id,
            "attempts": restoring.attempts,
            "caches_cleared": restoring.caches_cleared,
            "abandoned": restoring.abandoned,
        }
        self.client.set(self.key, json.dumps(kept))

    def lift(self) -> None:
        """End the maintenance: the platform serves its operations again."""
        self.client.delete(self.key)

    def close_front_sessions(self) -> int:
        """Delete every session and sign-in the front keeps, and say how many keys went."""
        return int(cast("int", self.client.eval(FORGET_SESSIONS, 0, self.sessions)))
