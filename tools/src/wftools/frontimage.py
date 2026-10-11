# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Build the production image of the front, start it, and hold what it must do (US-0430).

Usage: ``python -m wftools.frontimage``.

The chain publishes the stage ``production`` of ``frontend/Dockerfile`` after a merge alone
(``images.yml``); a pull request that changes what makes it — the Dockerfile, the configuration of
Next, the dependencies — builds it here first, and holds that:

- nothing read from the environment is fixed at the build: the routes ``next build`` prerenders are
  the error page of Next and the icon alone, which read nothing;
- the image starts without a variable of the platform, and ``/`` answers;
- the fake back of the mock-up (``WATERFALL_AUTH=mock``) is refused without ``WATERFALL_E2E``: ``/``
  answers ``500``, and the server says why.
"""

import http.client
import json
import subprocess
import sys
import time
from collections.abc import Callable, Mapping

from wftools import REPOSITORY

IMAGE = "waterfall-front:check"
"""The local tag of the image built here; it is never pushed."""

PRERENDERED = frozenset({"/_global-error", "/icon.svg"})
"""The routes ``next build`` may prerender: they read nothing of the environment."""

MANIFEST = "/app/.next/prerender-manifest.json"
REFUSAL = "WATERFALL_AUTH=mock is refused in production"
SERVER_ERROR = 500
WAIT = 60.0
"""How long the server of a container has to answer, in seconds."""

Run = Callable[[list[str]], int]
Read = Callable[[list[str]], tuple[int, str]]
Fetch = Callable[[str, int], int | None]


class FrontImageError(Exception):
    """What the image of the front does not do as it must."""


def check_prerendered(manifest: str) -> None:
    """Refuse a build that prerendered a route other than the error page and the icon."""
    try:
        routes: dict[str, object] = json.loads(manifest)["routes"]
    except (ValueError, KeyError, TypeError) as error:
        message = f"the prerender manifest of the image does not read: {error}"
        raise FrontImageError(message) from error
    if fixed := sorted(set(routes) - PRERENDERED):
        message = f"next build prerendered {', '.join(fixed)}: a page would be fixed at the build"
        raise FrontImageError(message)


def _output(read: Read, command: list[str]) -> str:
    """Run a command that must succeed, and return what it said."""
    code, output = read(command)
    if code != 0:
        message = f"{' '.join(command)} failed ({code}): {output.strip()}"
        raise FrontImageError(message)
    return output.strip()


def answer(
    read: Read, fetch: Fetch, environment: Mapping[str, str], wait: float = WAIT
) -> tuple[int, str]:
    """Start the image with this environment alone; return the status of ``/`` and the logs."""
    variables = [word for name, value in environment.items() for word in ("-e", f"{name}={value}")]
    started = ["docker", "run", "--detach", "--publish", "127.0.0.1::3000", *variables, IMAGE]
    container = _output(read, started)
    try:
        address = _output(read, ["docker", "port", container, "3000/tcp"]).splitlines()[0]
        host, port = address.rsplit(":", 1)
        deadline = time.monotonic() + wait
        while (status := fetch(host, int(port))) is None:
            if time.monotonic() > deadline:
                message = f"the front did not answer at {address} within {wait:.0f} s"
                raise FrontImageError(message)
            time.sleep(0.5)
        return status, _output(read, ["docker", "logs", container])
    finally:
        read(["docker", "rm", "--force", container])


def check(read: Read, fetch: Fetch) -> None:
    """Hold the image built to what it must do."""
    manifest = ["docker", "run", "--rm", "--entrypoint", "cat", IMAGE, MANIFEST]
    check_prerendered(_output(read, manifest))
    print(f"  prerendered: {', '.join(sorted(PRERENDERED))} alone")
    status, _ = answer(read, fetch, {})
    if status >= SERVER_ERROR:
        message = f"/ answered {status} without a variable of the platform"
        raise FrontImageError(message)
    print(f"  / answers {status} without a variable of the platform")
    status, logged = answer(read, fetch, {"WATERFALL_AUTH": "mock"})
    if status != SERVER_ERROR or REFUSAL not in logged:
        message = f"WATERFALL_AUTH=mock without WATERFALL_E2E is not refused: / answered {status}"
        raise FrontImageError(message)
    print("  WATERFALL_AUTH=mock without WATERFALL_E2E is refused")


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPOSITORY, check=False).returncode


def _read(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode, f"{result.stdout}{result.stderr}"


def _fetch(host: str, port: int) -> int | None:
    """Return the status of ``GET /``, a redirection not followed; None while nothing answers."""
    connection = http.client.HTTPConnection(host, port, timeout=10)
    try:
        connection.request("GET", "/")
        return connection.getresponse().status
    except (OSError, http.client.HTTPException):
        return None
    finally:
        connection.close()


def main(run: Run = _run, read: Read = _read, fetch: Fetch = _fetch) -> int:
    """Build the image of the front, then hold it; fail naming what it does not do."""
    build = ["docker", "build", "--target", "production", "--tag", IMAGE, "frontend"]
    print(f"  {' '.join(build)}", flush=True)
    try:
        if code := run(build):
            return code
        check(read, fetch)
    except (FrontImageError, OSError) as error:
        print(f"wftools.frontimage: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
