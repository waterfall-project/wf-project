# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Wait, in a job of the chain, for another job of the same run to succeed (US-1910).

Usage: ``python -m wftools.awaitjob <job> [--within <seconds>]``, in a job of GitHub Actions.

The parts of the paths against the service (service.yml) start before the build of the front
(ci.yml, front-build), beside it: they set up their runner, pull the work image of the paths and
build Keycloak's image meanwhile, and wait for the build only where they download it. A called
workflow starts once every job its caller ``needs`` has ended, never at one of its steps; so
service does not ``need`` front-build, and this tool, run in the step before the download, holds it
until front-build has succeeded — its upload is its last step, and an artifact is not read before it
is uploaded. A front-build that ended otherwise (failure, cancelled, skipped) fails the step,
naming it; one that has not ended within ``--within`` seconds fails it too.

The jobs of the run are read by ``gh`` (``GH_TOKEN``, with ``actions: read``), the latest execution
of each (``filter=latest``), meant so that a job a re-run did not repeat is read as it ended; how
the API answers after a partial re-run is not verified. A reading that fails for a cause that may
pass — GitHub answering 429, 502, 503 or 504, a connection that fails (``gh`` fails without an
HTTP status), an answer that is not JSON — is read again at the next poll, until the bound; any
other failure (403, 404…) fails the wait at once.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

TOOL = "wftools.awaitjob"
"""The name the tool gives its messages."""

POLL = 10.0
"""Seconds between two readings of the jobs: a few requests a part, under GitHub's quota."""

WITHIN = 780.0
"""Seconds a job is waited for by default: front-build takes about a minute, and its
``timeout-minutes`` is 12 (720 s), which this bound exceeds."""

PAGE = 100
"""Jobs a page of the API lists; a run of the chain has about forty."""

MAX_PAGES = 5
"""Pages read at most: more would be a run the chain does not make."""

STATUS = re.compile(r"\bHTTP (\d{3})\b")
"""The status ``gh`` says of a call GitHub answered, as wftools.queue reads it; not imported from
there, so that a change of the report of the queue does not wake the paths against the service."""

TRANSIENT = frozenset({429, 502, 503, 504})
"""The statuses read again at the next poll; 404, 403 and the others fail the wait at once."""


class AwaitError(Exception):
    """A job that will not succeed, or a reading of the jobs that fails, said to the user."""


class UnreadableError(AwaitError):
    """A reading that may pass, read again at the next poll.

    A connection that fails, a status in ``TRANSIENT``, an answer that is not JSON.
    """


def gh(arguments: list[str]) -> str:
    """Run ``gh`` and return its output; a failure is said with what ``gh`` wrote."""
    try:
        result = subprocess.run(["gh", *arguments], capture_output=True, text=True, check=False)
    except FileNotFoundError as error:
        message = "gh is not installed or not on the PATH"
        raise AwaitError(message) from error
    if result.returncode != 0:
        message = f"gh {arguments[0]} failed: {result.stderr.strip()}"
        found = STATUS.search(result.stderr)
        if found is None or int(found.group(1)) in TRANSIENT:
            raise UnreadableError(message)
        raise AwaitError(message)
    return result.stdout


def succeeded(jobs: Sequence[Mapping[str, object]], name: str) -> bool:
    """Return whether the jobs named ``name`` all succeeded, False while one has not ended.

    None found is waited for: GitHub creates a job when the jobs it needs have ended.
    """
    named = [job for job in jobs if job.get("name") == name]
    for job in named:
        if job.get("status") == "completed" and job.get("conclusion") != "success":
            message = f"{name} ended {job.get('conclusion')}: what it makes is not there to read"
            raise AwaitError(message)
    return bool(named) and all(job.get("status") == "completed" for job in named)


def jobs(call: Callable[[list[str]], str], repository: str, run: str) -> list[dict[str, object]]:
    """Return the jobs of the run, the latest execution of each, page by page."""
    found: list[dict[str, object]] = []
    for page in range(1, MAX_PAGES + 1):
        path = (
            f"repos/{repository}/actions/runs/{run}/jobs?filter=latest&per_page={PAGE}&page={page}"
        )
        try:
            answer: object = json.loads(call(["api", path]))
        except json.JSONDecodeError as error:
            message = f"gh api did not answer JSON for the jobs of run {run}"
            raise UnreadableError(message) from error
        listed = cast("dict[str, object]", answer).get("jobs") if isinstance(answer, dict) else None
        if not isinstance(listed, list):
            message = f"gh api did not answer the jobs of run {run}"
            raise AwaitError(message)
        page_jobs = [cast("dict[str, object]", job) for job in cast("list[object]", listed)]
        found.extend(page_jobs)
        if len(page_jobs) < PAGE:
            return found
    message = f"gh api still listed jobs of run {run} after {MAX_PAGES} pages"
    raise AwaitError(message)


@dataclass(frozen=True)
class World:
    """What the wait reads and does outside itself: ``gh``, the clock, a pause."""

    call: Callable[[list[str]], str] = gh
    wait: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic


def await_job(
    name: str, within: float, environment: Mapping[str, str], world: World | None = None
) -> float:
    """Wait for the job ``name`` of this run to succeed; return the seconds waited."""
    world = world or World()
    repository = environment.get("GITHUB_REPOSITORY")
    run = environment.get("GITHUB_RUN_ID")
    if not repository or not run:
        message = "GITHUB_REPOSITORY and GITHUB_RUN_ID are unset: made for a job of GitHub Actions"
        raise AwaitError(message)
    start = world.clock()
    while True:
        try:
            listed = jobs(world.call, repository, run)
        except UnreadableError:
            pass
        else:
            if succeeded(listed, name):
                return world.clock() - start
        if world.clock() - start >= within:
            message = f"{name} has not succeeded within {within:.0f} s"
            raise AwaitError(message)
        world.wait(POLL)


def main(argv: Sequence[str] | None = None) -> int:
    """Wait for the job the command names, and say how long it took."""
    parser = argparse.ArgumentParser(
        prog=TOOL, description="Wait for a job of the same run to succeed."
    )
    parser.add_argument("job", help="the name of the job, as GitHub shows it")
    parser.add_argument("--within", type=float, default=WITHIN, help="seconds to wait at most")
    arguments = parser.parse_args(argv)
    try:
        waited = await_job(arguments.job, arguments.within, os.environ)
    except AwaitError as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    print(f"{arguments.job} succeeded, waited {waited:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
