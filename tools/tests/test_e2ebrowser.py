# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The server of the browser that `make e2e-service` starts in the work image (US-1910, #3010).

The lines of the Makefile that start it (`e2e-browser`) run here, under the shell make uses, with a
stand-in for the server in place of the image: it records its path and its pid, answers any request,
ignores SIGINT as a server in a container does, and stops on SIGTERM. What is held: the paths know
a path drawn at each run, the port must be free, a server that dies ends the wait at once, and a
shell interrupted stops the server. That Playwright's `run-server` takes `--path` is not seen here.
The pull of the image by service.yml, which tries again on a registry that does not answer and not
on one that refuses, is played the same way, with a stand-in for Docker.
"""

import os
import re
import signal
import socket
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest
import yaml

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

STAND_IN = """
import http.server, os, signal, sys
args = sys.argv
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
port = int(args[args.index("--port") + 1])
open(os.environ["STAND_IN_RECORD"], "w").write(f"{os.getpid()} {args[args.index('--path') + 1]}")
http.server.HTTPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
"""
LINES = re.compile(r"^(E2E_BROWSER_PORT|e2e-port-free|e2e-browser) \??=.*$", re.MULTILINE)
PROBE = """{lines}
E2E_IMAGE = image
probe: ; @cd . && {{ $(e2e-browser) $(COMMAND); }}
"""


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Probe:
    """The lines of the Makefile that start the server, played by make in a temporary directory."""

    def __init__(self, directory: Path) -> None:
        self.record = directory / "record"
        stand_in = directory / "stand_in.py"
        stand_in.write_text(STAND_IN, encoding="utf-8")
        lines = "\n".join(match.group(0) for match in LINES.finditer(self.text()))
        (directory / "probe.mk").write_text(PROBE.format(lines=lines), encoding="utf-8")
        self.directory = directory
        self.stand_in = f"{sys.executable} {stand_in}"
        self.port = free_port()

    @staticmethod
    def text() -> str:
        return (REPOSITORY / "Makefile").read_text(encoding="utf-8")

    def start(self, command: str, *, server: str | None = None) -> subprocess.Popen[str]:
        environment = {**os.environ, "STAND_IN_RECORD": str(self.record)}
        return subprocess.Popen(
            [
                "make",
                "--no-print-directory",
                "-f",
                str(self.directory / "probe.mk"),
                f"e2e-in-image={server or self.stand_in}",
                f"E2E_BROWSER_PORT={self.port}",
                f"COMMAND={command}",
                "probe",
            ],
            cwd=self.directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )

    def served(self) -> tuple[int, str]:
        pid, path = self.record.read_text(encoding="utf-8").split()
        return int(pid), path


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_until(condition: Callable[[], bool], seconds: float = 20) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def probe(tmp_path: Path) -> Probe:
    return Probe(tmp_path)


def test_the_paths_connect_to_the_path_the_server_was_given_and_the_server_stops(
    probe: Probe,
) -> None:
    """The endpoint carries a path drawn at each run, and the server stops with the shell."""
    first = probe.start('echo "$$PW_TEST_CONNECT_WS_ENDPOINT"')
    out, _ = first.communicate(timeout=60)
    pid, path = probe.served()
    assert first.returncode == 0
    assert re.fullmatch(r"/[0-9a-f]{32}", path)
    assert out.strip() == f"ws://127.0.0.1:{probe.port}{path}"
    assert wait_until(lambda: not alive(pid))
    second = probe.start("true")
    second.communicate(timeout=60)
    assert probe.served()[1] != path


def test_a_port_already_taken_stops_before_the_server_starts(probe: Probe) -> None:
    """A server already on the port is not waited for as ours."""
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", probe.port))
        taken.listen()
        run = probe.start("true")
        _, err = run.communicate(timeout=60)
    assert run.returncode != 0
    assert f"port {probe.port} is taken" in err
    assert not probe.record.exists()


def test_a_server_that_dies_ends_the_wait_without_the_two_minutes(probe: Probe) -> None:
    """The wait stops at the death of the server, whose command here ends at once."""
    started = time.monotonic()
    run = probe.start("true", server="false")
    run.communicate(timeout=60)
    assert run.returncode != 0
    assert time.monotonic() - started < 30


def test_an_interrupted_shell_stops_the_server(probe: Probe) -> None:
    """SIGINT, as Ctrl-C sends it to the whole group, leaves no server on the port."""
    run = probe.start("sleep 300")
    assert wait_until(probe.record.exists)
    pid, _ = probe.served()
    assert alive(pid)
    time.sleep(1)  # the shell has gone on to its command
    os.killpg(run.pid, signal.SIGINT)
    run.communicate(timeout=60)
    assert run.returncode != 0
    assert wait_until(lambda: not alive(pid))


PULL_ERRORS = [
    ("denied: permission_denied: read_package", 1),
    ("manifest unknown: manifest unknown", 1),
    ("Error response from daemon: not found", 1),
    ("Get https://ghcr.io/v2/: net/http: TLS handshake timeout", 4),
]


@pytest.mark.parametrize(("message", "attempts"), PULL_ERRORS)
def test_the_pull_of_the_work_image_tries_again_on_a_silence_and_not_on_a_refusal(
    tmp_path: Path, message: str, attempts: int
) -> None:
    """A registry that denies the image or does not hold it ends the step at the first attempt."""
    workflow = yaml.safe_load(
        (REPOSITORY / ".github/workflows/service.yml").read_text(encoding="utf-8")
    )
    step = next(
        step for step in workflow["jobs"]["paths"]["steps"] if "docker pull" in step.get("run", "")
    )
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    count = tmp_path / "count"
    (bin_directory / "docker").write_text(
        f'#!/bin/sh\necho x >> {count}\necho "{message}" >&2\nexit 1\n', encoding="utf-8"
    )
    (bin_directory / "sleep").write_text("#!/bin/sh\n", encoding="utf-8")
    for fake in bin_directory.iterdir():
        fake.chmod(0o755)
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env={
            "PATH": f"{bin_directory}:{os.environ['PATH']}",
            "RUNNER_TEMP": str(tmp_path),
            "E2E_IMAGE": "ghcr.io/x/e2e@sha256:0",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert len(count.read_text(encoding="utf-8").split()) == attempts
