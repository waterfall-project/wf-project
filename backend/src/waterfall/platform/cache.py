# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cache of the indicators of the current day, kept in the Redis of the queue (WF-DAT-0130-A).

One document per project and per day, under a key that carries the fingerprint of what the
indicators depend on: a write changes the key, so no entry is ever served for a state that is no
longer the project's, and the validity period, set at the write, bounds what is kept. The cache
holds a copy, never the only one: a Redis that does not answer — connection, delay, reply — is no
reason to refuse a read or an entry. The read gives ``None``, the write is ignored, and the fault
is logged once by process and by cause, the class of the error (``indicators.cache_unavailable``);
the caller computes.
"""

from typing import TYPE_CHECKING, Any, Self

from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from waterfall.platform.logs import get_logger
from waterfall.platform.queue import DEPOSIT_TIMEOUT

if TYPE_CHECKING:
    from waterfall.platform.queue import TaskQueue

# What every key of the cache starts with, beside the keys of the queue, in the same database.
PREFIX = "waterfall:indicators:"

logger = get_logger(__name__)

# The causes already logged by this process: an installation whose Redis is down would otherwise
# write one record per read.
_reported: set[str] = set()


def forget_reports() -> None:
    """Forget the causes already logged, so that the next of each is logged again (tests)."""
    _reported.clear()


class IndicatorsCache:
    """The entries of the indicators, as the API reads and writes them."""

    def __init__(self, client: Redis, ttl: int) -> None:
        self.client = client
        self.ttl = ttl

    @classmethod
    def of(cls, queue: TaskQueue, ttl: int) -> Self:
        """Keep the cache beside the queue of the tasks, in its Redis, for ``ttl`` seconds an entry.

        The cache opens its own connections to that Redis, with the delay of a deposit,
        ``DEPOSIT_TIMEOUT``, whatever delay the queue was opened with: a read or a write of the
        cache waits for Redis no longer. Its pool is its own: ``close`` releases it.
        """
        source = queue.client.connection_pool
        kwargs: dict[str, Any] = {
            **source.connection_kwargs,
            "socket_timeout": DEPOSIT_TIMEOUT,
            "socket_connect_timeout": DEPOSIT_TIMEOUT,
        }
        pool = ConnectionPool(connection_class=source.connection_class, **kwargs)
        return cls(Redis(connection_pool=pool), ttl)

    def close(self) -> None:
        """Release the connections of the cache."""
        self.client.close()
        self.client.connection_pool.disconnect()

    def read(self, key: str) -> str | None:
        """Give the document kept under a key, or ``None`` if none is or Redis does not answer.

        A client that gives bytes, not decoded strings, is served all the same; an entry that is not
        UTF-8 is unreadable, hence ``None``, and logged like the other causes.
        """
        try:
            document = self.client.get(PREFIX + key)
        except RedisError as error:
            _report(error)
            return None
        if isinstance(document, bytes):
            try:
                return document.decode("utf-8")
            except UnicodeDecodeError as error:
                _report(error)
                return None
        return document if isinstance(document, str) else None

    def write(self, key: str, document: str) -> None:
        """Keep a document under a key for the validity period; ignore a Redis that fails."""
        try:
            self.client.set(PREFIX + key, document, ex=self.ttl)
        except RedisError as error:
            _report(error)


def _report(error: RedisError | UnicodeDecodeError) -> None:
    """Log the first fault of each cause; the cause is the class of the error.

    Two ``ResponseError`` (``WRONGTYPE``, ``OOM``, ``READONLY``…) are one cause: the message of the
    first is logged with it. It carries no identifier and no password, only the address of the Redis
    (``host:port``) for a connection or a delay error.
    """
    cause = type(error).__name__
    if cause in _reported:
        return
    _reported.add(cause)
    logger.warning("indicators.cache_unavailable", cause=cause, message=str(error))
