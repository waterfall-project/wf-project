# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine of the requests: how long it waits, and what it tells a database out of reach from.

A request whose connection fails, or whose pool is spent, is refused naming the database (§4.5.4,
table 12, US-2860); a statement the server judged — a lock refused, a deadlock — is not the database
out of reach, and stays what it was.
"""

import dataclasses
import time
from typing import TYPE_CHECKING, cast

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import errors
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from waterfall.api.app import create_app
from waterfall.platform import database as database_module
from waterfall.platform.database import (
    CONNECT_TIMEOUT,
    OBSERVATION_SECONDS,
    POOL_OVERFLOW,
    POOL_SIZE,
    POOL_TIMEOUT,
    create_database_engine,
    is_unreachable,
)
from waterfall.platform.maintenance import Maintenance

if TYPE_CHECKING:
    from typing import Any

    from sqlalchemy.pool import QueuePool

    from waterfall.api.authentication import Services
    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

ADDRESS = "postgresql://nobody:nothing@127.0.0.1:9/nowhere"


@pytest.mark.story("US-2860")
@pytest.mark.parametrize(
    ("query", "waited"),
    [("", CONNECT_TIMEOUT), ("?connect_timeout=10", 10), ("?connect_timeout=1&x=2", 1)],
    ids=["by default", "the address says ten", "the address says one"],
)
def test_the_connect_timeout_the_address_declares_is_the_one_kept(
    monkeypatch: pytest.MonkeyPatch, query: str, waited: int
) -> None:
    # #4190: the two seconds of the engine are a default, not an override of the operator's.
    given: dict[str, Any] = {}

    def keep(_url: object, **options: Any) -> None:
        given.update(options)

    monkeypatch.setattr(database_module, "create_engine", keep)
    create_database_engine(ADDRESS + query)
    assert int(given["connect_args"]["connect_timeout"]) == waited


@pytest.mark.story("US-2860")
def test_a_request_waits_for_a_connection_of_its_pool_no_longer_than_one_takes_to_open() -> None:
    # #4189: the default of the pool, thirty seconds, is far above what the healthcheck waits.
    engine = create_database_engine(ADDRESS)
    try:
        assert cast("QueuePool", engine.pool).timeout() == POOL_TIMEOUT
    finally:
        engine.dispose()
    assert POOL_TIMEOUT <= CONNECT_TIMEOUT <= OBSERVATION_SECONDS


@pytest.mark.story("US-2860")
def test_the_probe_of_liveness_answers_within_the_pool_timeout_when_every_connection_is_taken(
    services: Services, database: Database, queue: TaskQueue
) -> None:
    # #4189: with the whole reserve lent out, the read of the maintenance gives up at POOL_TIMEOUT
    # and the probe says there is none, within what the healthcheck of Compose waits (two seconds).
    held = [database.engine.connect() for _ in range(POOL_SIZE + POOL_OVERFLOW)]
    served = dataclasses.replace(services, maintenance=Maintenance.of(database, queue))
    try:
        began = time.monotonic()
        answer = TestClient(create_app(served)).get("/api/v1/health")
        elapsed = time.monotonic() - began
    finally:
        for each in held:
            each.close()
    assert (answer.status_code, answer.json()) == (200, {"status": "ok"})
    assert elapsed < POOL_TIMEOUT + 1


def driver_failure(driver: psycopg.Error) -> OperationalError:
    """Give what SQLAlchemy raises when the driver fails with ``driver``."""
    return OperationalError("SELECT 1", {}, driver)


@pytest.mark.story("US-2860")
@pytest.mark.parametrize(
    ("error", "unreachable"),
    [
        (driver_failure(psycopg.OperationalError("connection failed")), True),
        (driver_failure(errors.AdminShutdown("terminating")), True),
        (driver_failure(errors.CannotConnectNow("starting")), True),
        (driver_failure(errors.ConnectionFailure("lost")), True),
        (PoolTimeoutError("the pool is spent"), True),
        (driver_failure(errors.LockNotAvailable("lock")), False),
        (driver_failure(errors.DeadlockDetected("deadlock")), False),
        (driver_failure(errors.QueryCanceled("cancelled")), False),
        (DBAPIError("SELECT 1", {}, errors.UniqueViolation("duplicate")), False),
        (ValueError("a defect"), False),
    ],
    ids=[
        "connection failed",
        "shutdown",
        "starting",
        "connection lost",
        "pool spent",
        "lock refused",
        "deadlock",
        "cancelled",
        "constraint",
        "defect",
    ],
)
def test_a_database_out_of_reach_is_told_from_a_statement_the_server_judged(
    error: BaseException, unreachable: bool
) -> None:
    assert is_unreachable(error) is unreachable


@pytest.mark.story("US-2860")
def test_the_cause_of_a_failure_is_looked_at_too() -> None:
    cause = driver_failure(psycopg.OperationalError("connection failed"))
    wrapped = RuntimeError("the route failed")
    wrapped.__cause__ = cause
    assert is_unreachable(wrapped)
