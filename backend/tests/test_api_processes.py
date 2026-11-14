# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API served by two processes: one user is served by either, the same (US-2230).

The API is started as the platform starts it, ``python -m waterfall.api.main``, on the database
and the Redis of the tests and the realm of test. Each process reads the keys of the realm the
first time it validates a token: the realm counts its readings, and so tells when a request was
served by a process that had served none before.
"""

import contextlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

import httpx2
import pytest
from realm import KEY, TestRealm
from sqlalchemy import insert
from support import PLATFORM_ADDRESSES, PLATFORM_SECRETS, bearer, raw_account

from waterfall.core.users.tables import UserAccount

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from waterfall.platform.database import Database

SUBJECT = "0d6f9a52-3c1e-4f7a-9b8d-5e2c7a1f4b63"
# How long the processes take to start, and to stop, at most.
START_SECONDS = 60.0
STOP_SECONDS = 30.0
# How many requests may go to the first process before the other serves one.
ATTEMPTS = 500


def free_port() -> int:
    """Give a port of the loopback that nothing listens on now."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def answer(port: int, path: str, headers: dict[str, str] | None = None) -> tuple[int, Any]:
    """Ask the API on a connection of its own, and give the status and the body it answers."""
    response = httpx2.get(f"http://127.0.0.1:{port}{path}", headers=headers, timeout=10)
    return response.status_code, response.json()


class Served:
    """The API started on its processes, and the file its logs are written to."""

    def __init__(self, process: subprocess.Popen[bytes], port: int, logs: Path) -> None:
        self.process = process
        self.port = port
        self.logs = logs

    def events(self) -> list[str]:
        """Give the event of each record of the logs written so far."""
        lines = self.logs.read_text(encoding="utf-8").splitlines()
        return [json.loads(line).get("event", "") for line in lines if line.startswith("{")]


def stop(process: subprocess.Popen[bytes]) -> None:
    """Stop the API and every worker of its group, killing them if they do not stop in time."""
    group = process.pid
    try:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(STOP_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # The process leads its own session: its group is the API and the workers it started.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(group, signal.SIGKILL)
        process.wait()


@pytest.fixture
def served(
    database: Database, service_environment: dict[str, str], realm: TestRealm, tmp_path: Path
) -> Iterator[Served]:
    """Start the API on two processes, wait for it to answer, then stop it."""
    del database
    port = free_port()
    environment = {
        **PLATFORM_SECRETS,
        **PLATFORM_ADDRESSES,
        **service_environment,
        "WATERFALL_KEYCLOAK_ADDRESS": realm.address,
        "WATERFALL_PORT": str(port),
        "WATERFALL_API_PROCESSES": "2",
    }
    logs = tmp_path / "api.log"
    with logs.open("wb") as written:
        process = subprocess.Popen(
            [sys.executable, "-m", "waterfall.api.main"],
            env=environment,
            stderr=written,
            start_new_session=True,
        )
    started = Served(process, port, logs)
    try:
        deadline = time.monotonic() + START_SECONDS
        while True:
            assert process.poll() is None, logs.read_text(encoding="utf-8")
            try:
                if answer(port, "/api/v1/health")[0] == 200:
                    break
            except httpx2.TransportError:
                pass
            assert time.monotonic() < deadline, logs.read_text(encoding="utf-8")
            time.sleep(0.1)
        yield started
    finally:
        stop(process)


@pytest.mark.requirement("WF-ARC-0080-A")
def test_two_successive_requests_of_a_user_served_by_two_processes_give_the_same_result(
    served: Served, database: Database, realm: TestRealm
) -> None:
    # « Deux requêtes successives d'un même utilisateur, servies par deux instances différentes,
    # donnent le même résultat sans qu'il ait à se reconnecter. »
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**raw_account(idp_subject=SUBJECT)))
    signed_in = bearer(realm.token(SUBJECT, KEY))
    first = answer(served.port, "/api/v1/me", signed_in)
    assert first[0] == 200
    assert first[1]["email"] == "claire.martin@example.org"
    # One process has validated a token, and read the keys for it.
    assert realm.reads == 1
    answers = [first]
    while realm.reads == 1 and len(answers) < ATTEMPTS:
        answers.append(answer(served.port, "/api/v1/me", signed_in))
    # The last request is the first the other process served, right after one of the first's:
    # the same token, the same answer.
    assert realm.reads == 2, f"{len(answers)} requests, all served by one process"
    assert answers[-2:] == [first, first]
    assert all(given == first for given in answers)


def test_each_process_closes_its_services_when_the_api_stops(served: Served) -> None:
    # Proper to US-2230: each process opens its services and closes them when it stops.
    served.process.send_signal(signal.SIGTERM)
    assert served.process.wait(STOP_SECONDS) == 0
    assert served.events().count("service.stopped") == 2
