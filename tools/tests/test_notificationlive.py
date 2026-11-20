# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Alertmanager started by its script, in front of a mail server of the test (US-2880).

test_notification.py holds the shape of the configuration the script writes, which amtool accepts.
Here the server of the release the platform runs is started by deploy/compose/alertmanager.sh, on a
folder of its own and a free port, and given an alert: the mail server of the test, a socket that
speaks the little of SMTP a message needs, receives the message, or is not called at all without
WATERFALL_ALERT_SMTP_HOST. The delays of the route (group_wait, group_interval) are shortened by a
program that stands for Alertmanager between the script and the real one: neither the script nor
the production is touched.
"""

import contextlib
import email
import http.client
import json
import os
import socket
import subprocess
import threading
import time
from typing import TYPE_CHECKING, Self

import pytest
from test_notification import SERVER, START

from wftools import kubetools

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from email.message import Message
    from pathlib import Path
    from types import TracebackType

WAIT = 30.0
QUIET = 4.0
OK = 200
Mail = tuple[str, list[str], "Message"]


class MailServer:
    """A mail server that accepts every message and keeps it, and counts its connections."""

    def __init__(self) -> None:
        self.messages: list[Mail] = []
        self.connections = 0
        self._lock = threading.Lock()
        self._socket = socket.socket()
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen()
        self.port: int = self._socket.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self._socket.close()

    def _accept(self) -> None:
        while True:
            try:
                connection, _ = self._socket.accept()
            except OSError:
                return
            with self._lock:
                self.connections += 1
            threading.Thread(target=self._serve, args=(connection,), daemon=True).start()

    def _serve(self, connection: socket.socket) -> None:
        sender = ""
        recipients: list[str] = []
        with connection, connection.makefile("rwb") as stream:

            def say(line: str) -> None:
                stream.write(f"{line}\r\n".encode())
                stream.flush()

            say("220 test ESMTP")
            while line := stream.readline().decode().strip():
                word = line.split(" ", 1)[0].upper()
                if word == "DATA":
                    say("354 go on")
                    lines: list[bytes] = []
                    while (row := stream.readline()).rstrip(b"\r\n") != b".":
                        lines.append(row)
                    with self._lock:
                        self.messages.append(
                            (sender, recipients, email.message_from_bytes(b"".join(lines)))
                        )
                    sender, recipients = "", []
                    say("250 queued")
                elif word == "QUIT":
                    say("221 bye")
                    return
                else:
                    if word == "MAIL":
                        sender = line.split("<", 1)[1].split(">", 1)[0]
                    elif word == "RCPT":
                        recipients.append(line.split("<", 1)[1].split(">", 1)[0])
                    say("250 ok")

    def received(self) -> list[Mail]:
        with self._lock:
            return list(self.messages)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def shortened(folder: Path) -> Path:
    """Write the program that shortens the delays of the route, then hands over to Alertmanager."""
    program = folder / "alertmanager-fast.sh"
    program.write_text(
        "#!/bin/sh\n"
        "file=${1#--config.file=}\n"
        "sed -i -e 's/group_wait: 30s/group_wait: 1s/' "
        "-e 's/group_interval: 5m/group_interval: 1s/' \"$file\"\n"
        f'exec {kubetools.installed("alertmanager")} "$@"\n',
        encoding="utf-8",
    )
    program.chmod(0o755)
    return program


def call(port: int, method: str, path: str, body: bytes | None = None) -> tuple[int, bytes]:
    """Call Alertmanager over HTTP, and give the status and the body of its answer."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        headers = {"Content-Type": "application/json"} if body else {}
        connection.request(method, path, body, headers)
        answer = connection.getresponse()
        return answer.status, answer.read()
    finally:
        connection.close()


def post(port: int, **given: object) -> None:
    """Post an alert to Alertmanager, as Prometheus does."""
    now = time.time()
    posted = {
        "labels": {"alertname": "component_unavailable", "component": "database"},
        "annotations": {"summary": "the database does not answer"},
        "startsAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 60)),
        **given,
    }
    status, _ = call(port, "POST", "/api/v2/alerts", json.dumps([posted]).encode())
    assert status == OK


def until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.2)
    message = f"no {what} in {WAIT:.0f} seconds"
    raise AssertionError(message)


@contextlib.contextmanager
def running(folder: Path, port: int, **given: str) -> Generator[None]:
    """Start Alertmanager by its script, on the port, and stop it at the end."""
    variables = {
        "PATH": os.environ["PATH"],
        "RENDERED": str(folder / "rendered"),
        "ALERTMANAGER": str(shortened(folder)),
        **given,
    }
    started = subprocess.Popen(
        [
            "sh",
            str(START),
            f"--web.listen-address=127.0.0.1:{port}",
            f"--storage.path={folder / 'data'}",
            "--cluster.listen-address=",
        ],
        env=variables,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def ready() -> bool:
        try:
            return call(port, "GET", "/-/ready")[0] == OK
        except OSError:
            return False

    try:
        until(ready, "ready Alertmanager")
        yield
    finally:
        started.terminate()
        try:
            started.wait(timeout=10)
        except subprocess.TimeoutExpired:
            started.kill()
            started.wait()


@pytest.mark.story("US-2880")
def test_each_alert_posted_to_alertmanager_is_notified_by_e_mail_and_its_end_too(
    tmp_path: Path,
) -> None:
    # Proper to US-2880: « notifie chaque alerte par courriel » : the message comes to the server
    # the environment names, from the sender and to the recipient it names; the end of the alert
    # (send_resolved) is notified by a second one.
    with MailServer() as mail:
        given = {
            **SERVER,
            "WATERFALL_ALERT_SMTP_HOST": f"127.0.0.1:{mail.port}",
            "WATERFALL_ALERT_SMTP_REQUIRE_TLS": "false",
        }
        port = free_port()
        with running(tmp_path, port, **given):
            post(port)
            until(lambda: len(mail.received()) >= 1, "message of the alert")
            post(port, endsAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 1)))
            until(lambda: len(mail.received()) >= 2, "message of the end of the alert")
        first, second = mail.received()[:2]
        for sender, recipients, message in (first, second):
            assert sender == SERVER["WATERFALL_ALERT_SMTP_FROM"]
            assert recipients == [SERVER["WATERFALL_ALERT_RECIPIENT"]]
            assert SERVER["WATERFALL_ALERT_SMTP_FROM"] in message["From"]
            assert SERVER["WATERFALL_ALERT_RECIPIENT"] in message["To"]
            assert "component_unavailable" in message["Subject"]
        assert "FIRING" in first[2]["Subject"]
        assert "RESOLVED" in second[2]["Subject"]


@pytest.mark.story("US-2880")
def test_without_a_mail_server_named_alertmanager_calls_none_and_keeps_the_alert(
    tmp_path: Path,
) -> None:
    # Proper to US-2880: « sans serveur, il ne notifie rien » : the sender and the recipient are
    # set, and a server listens, but the environment does not name it: no connection is made.
    with MailServer() as mail:
        given = {key: value for key, value in SERVER.items() if key != "WATERFALL_ALERT_SMTP_HOST"}
        port = free_port()
        with running(tmp_path, port, **given):
            post(port)
            time.sleep(QUIET)
            alerts = json.loads(call(port, "GET", "/api/v2/alerts")[1])
        assert [item["labels"]["alertname"] for item in alerts] == ["component_unavailable"]
        assert mail.connections == 0
        assert mail.received() == []
