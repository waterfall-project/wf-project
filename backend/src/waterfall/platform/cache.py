# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cache of the indicators of the current day, kept in the Redis of the queue (WF-DAT-0130-A).

One document per scope of a project and per day, under a key that carries the fingerprint of what
the indicators depend on: a write changes the key, so no entry is ever served for a state that is no
longer the project's, and the validity period, set at the write, bounds what is kept. The cache
holds a copy, never the only one: a Redis that does not answer — connection, delay, reply — is no
reason to refuse a read or an entry. The read gives ``None`` (``lookup`` tells it from an entry
absent: ``UNAVAILABLE``), the write is ignored, and the fault is logged once by process and by
cause, the class of the error (``indicators.cache_unavailable``); the caller computes.
"""

from typing import TYPE_CHECKING, Any, Self, cast

from redis import ConnectionPool, Redis
from redis.exceptions import RedisError

from waterfall.platform.logs import get_logger
from waterfall.platform.queue import DEPOSIT_TIMEOUT

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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


class Unavailable:
    """What ``lookup`` gives for a Redis that does not answer, as opposed to an entry absent."""

    __slots__ = ()


UNAVAILABLE = Unavailable()


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
        """Give the document kept under a key, or ``None`` if none is or Redis does not answer."""
        found = self.lookup(key)
        return None if isinstance(found, Unavailable) else found

    def lookup(self, key: str) -> str | Unavailable | None:
        """Give the document kept under a key, ``None`` if none is, ``UNAVAILABLE`` if Redis fails.

        A client that gives bytes, not decoded strings, is served all the same; an entry that is not
        UTF-8 is unreadable, hence ``None`` (the entry is written again), and logged like the other
        causes.
        """
        try:
            document: object = self.client.get(PREFIX + key)
        except RedisError as error:
            _report(error)
            return UNAVAILABLE
        return _decoded(document)

    def lookup_many(self, keys: Sequence[str]) -> list[str | None] | Unavailable:
        """Give the documents kept under keys, in their order, in one exchange with Redis.

        Each as ``lookup`` gives it — ``None`` for an entry absent or not UTF-8 —; ``UNAVAILABLE``
        for all when Redis fails.
        """
        if not keys:
            return []
        try:
            documents = cast("list[object]", self.client.mget([PREFIX + key for key in keys]))
        except RedisError as error:
            _report(error)
            return UNAVAILABLE
        return [_decoded(each) for each in documents]

    def write(self, key: str, document: str) -> None:
        """Keep a document under a key for the validity period; ignore a Redis that fails."""
        try:
            self.client.set(PREFIX + key, document, ex=self.ttl)
        except RedisError as error:
            _report(error)

    def write_many(self, documents: Mapping[str, str]) -> None:
        """Keep documents under their keys, each for the validity period; stop at a Redis failing.

        No transaction: each entry stands alone. The first failure is ignored, as by ``write``, and
        the documents left are not written: the read waits for Redis once, not once by document.
        """
        for key, document in documents.items():
            try:
                self.client.set(PREFIX + key, document, ex=self.ttl)
            except RedisError as error:
                _report(error)
                return


def _decoded(document: object) -> str | None:
    """Give a document as Redis gave it, decoded; ``None`` when absent or not UTF-8 (logged)."""
    if isinstance(document, bytes):
        try:
            return document.decode("utf-8")
        except UnicodeDecodeError as error:
            _report(error)
            return None
    return document if isinstance(document, str) else None


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
