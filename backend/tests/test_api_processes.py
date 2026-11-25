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
from metrics_reading import samples, value
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
# How many processes serve the API.
PROCESSES = 2


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
        text = self.logs.read_text(encoding="utf-8")
        # The workers write while this reads: a last line without its newline is not finished.
        lines = text.split("\n")[:-1]
        return [json.loads(line).get("event", "") for line in lines if line.startswith("{")]


def wait_for_started(served: Served, expected: int, deadline: float) -> None:
    """Wait until ``expected`` processes have written ``service.started``, or fail with the logs."""
    while (opened := served.events().count("service.started")) < expected:
        assert served.process.poll() is None, served.logs.read_text(encoding="utf-8")
        assert time.monotonic() < deadline, (
            f"{opened} of {expected} processes started:\n{served.logs.read_text(encoding='utf-8')}"
        )
        time.sleep(0.1)


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
        "WATERFALL_API_PROCESSES": str(PROCESSES),
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
        # A first 200 proves one process ready, not both: wait until each has opened its services.
        wait_for_started(started, PROCESSES, deadline)
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


def test_the_requests_served_by_two_processes_are_counted_together(
    served: Served, database: Database, realm: TestRealm
) -> None:
    # Proper to US-2870: the API serves on several processes, and its metrics count the requests
    # of them all, whichever process the collection reaches (WF-OBS-0010).
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**raw_account(idp_subject=SUBJECT)))
    signed_in = bearer(realm.token(SUBJECT, KEY))
    asked = 0
    while realm.reads < 2 and asked < ATTEMPTS:
        assert answer(served.port, "/api/v1/me", signed_in)[0] == 200
        asked += 1
    assert realm.reads == 2, f"{asked} requests, all served by one process"
    for _ in range(4):
        response = httpx2.get(f"http://127.0.0.1:{served.port}/api/v1/metrics", timeout=10)
        read = samples(response.text)
        assert value(read, "waterfall_api_requests_total", operation="getMe", status="200") == asked


def test_the_logs_read_while_written_leave_out_a_last_line_cut_short(tmp_path: Path) -> None:
    # A worker may be writing its record while the fixture reads: the cut line is not counted.
    logs = tmp_path / "api.log"
    logs.write_text('{"event": "service.started"}\n{"event": "service.sta', encoding="utf-8")
    running = subprocess.Popen([sys.executable, "-c", "pass"])
    running.wait()
    assert Served(running, 0, logs).events() == ["service.started"]


def test_the_wait_for_the_processes_fails_with_the_count_and_the_logs(tmp_path: Path) -> None:
    logs = tmp_path / "api.log"
    logs.write_text('{"event": "service.started"}\nnoise\n', encoding="utf-8")
    running = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        served = Served(running, 0, logs)
        with pytest.raises(AssertionError) as failure:
            wait_for_started(served, 2, time.monotonic() + 0.3)
    finally:
        stop(running)
    assert "1 of 2 processes started" in str(failure.value)
    assert "noise" in str(failure.value)


def test_each_process_closes_its_services_when_the_api_stops(served: Served) -> None:
    # Proper to US-2230: each process opens its services and closes them when it stops.
    served.process.send_signal(signal.SIGTERM)
    assert served.process.wait(STOP_SECONDS) == 0
    assert served.events().count("service.stopped") == PROCESSES
