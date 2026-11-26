# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the trial of the chart holds while the API goes from one instance to three (US-2800/L2).

Requests are held for the whole of the upgrade: each of several threads asks for the account of
the first administrator, signed in — the front asks the API for it — as fast as the platform
answers, and records every request that does not end on it. The upgrade is without interruption
when none fails; and when no pod that was there is gone or restarted, PostgreSQL's included:
scaling the API changes one value, and no pod reads it.
"""

import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from html import unescape
from typing import TYPE_CHECKING, Any

from wftools.production import OK, Browser, Platform, ProductionError, Send

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping

TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL)
"""The title of a page, which says what it is when it is not the account."""
DIGEST = re.compile(r'digest\\?":\\?"([^"\\]+)')
"""The digest of an error a page of Next streams: what failed, WATERFALL_SESSION_LOST or another."""
THREADS = 4
"""How many requests are held at once."""
PAUSE = 0.05
"""The seconds between two requests of a thread."""
LEAST = 50
"""The fewest requests a passage must have held: fewer says the load was not there."""
OWNERS = frozenset({"ReplicaSet", "StatefulSet"})
"""The owners of the pods that are the platform's, those a Job or a CronJob makes being gone by
design."""


@dataclass(slots=True)
class Tally:
    """What the requests held saw: how many were sent, and which did not end well."""

    sent: int = 0
    failed: list[str] = field(default_factory=list[str])
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, failure: str | None) -> None:
        """Count a request, and keep what was wrong with it when something was."""
        with self.lock:
            self.sent += 1
            if failure is not None:
                self.failed.append(failure)


def request_once(
    send: Send, cookies: Mapping[str, str], platform: Platform, email: str
) -> str | None:
    """Ask for the account of the first administrator; return what failed, or None."""
    browser = Browser(send, dict(cookies))
    try:
        answer, address = browser.open(f"{platform.address}/account")
    except ProductionError as error:
        return str(error)
    if answer.status != OK:
        return f"the account answered {answer.status}"
    if email not in unescape(answer.body):
        # Where the page ended, and what it is: the sign-in after a lost session, or the account
        # saying it could not be read.
        found = TITLE.search(answer.body)
        title = unescape(found.group(1)).strip() if found else "no title"
        failed = DIGEST.search(answer.body)
        digest = f", digest {failed.group(1)}" if failed else ""
        return f"the account does not name the first administrator: {address}, {title!r}{digest}"
    return None


def hold_requests(attempt: Callable[[], str | None], stop: threading.Event, tally: Tally) -> None:
    """Make one request after the other, until ``stop`` is set, and tally each."""
    while not stop.is_set():
        tally.record(attempt())
        stop.wait(PAUSE)


@contextmanager
def requests_held(
    send: Send, browser: Browser, platform: Platform, email: str, threads: int = THREADS
) -> Generator[Tally]:
    """Hold requests of the signed-in browser on the platform for as long as the block runs."""
    tally, stop = Tally(), threading.Event()
    cookies = dict(browser.cookies)

    def attempt() -> str | None:
        return request_once(send, cookies, platform, email)

    workers = [
        threading.Thread(target=hold_requests, args=(attempt, stop, tally), daemon=True)
        for _ in range(threads)
    ]
    for worker in workers:
        worker.start()
    # One request at least from each thread before the passage starts: the load is there at once.
    while tally.sent < threads and any(worker.is_alive() for worker in workers):
        time.sleep(PAUSE)
    try:
        yield tally
    finally:
        stop.set()
        for worker in workers:
            worker.join()


def check_uninterrupted(tally: Tally) -> None:
    """Hold that requests were held through the passage, and that none failed."""
    if tally.sent < LEAST:
        message = f"only {tally.sent} requests were held through the passage, {LEAST} at least"
        raise ProductionError(message)
    if tally.failed:
        first = tally.failed[0]
        message = f"{len(tally.failed)} of {tally.sent} requests failed during the passage: {first}"
        raise ProductionError(message)


def pods_of(listing: Mapping[str, Any]) -> dict[str, tuple[str, int]]:
    """Return the pods of the platform that run — name to identifier and restarts — from kubectl.

    Those a Job or a CronJob made are left out: they are meant to come and go.
    """
    found: dict[str, tuple[str, int]] = {}
    for item in listing["items"]:
        metadata = item["metadata"]
        owners = {owner["kind"] for owner in metadata.get("ownerReferences", [])}
        if not owners & OWNERS or item["status"].get("phase") != "Running":
            continue
        statuses = item["status"].get("containerStatuses", [])
        found[metadata["name"]] = (
            metadata["uid"],
            sum(status["restartCount"] for status in statuses),
        )
    return found


def check_untouched(
    before: Mapping[str, tuple[str, int]], after: Mapping[str, tuple[str, int]]
) -> None:
    """Hold that every pod there was is still there, the same, and was not restarted."""
    for name, was in before.items():
        if name not in after:
            message = f"the pod {name} is gone after the passage: it was replaced"
            raise ProductionError(message)
        if after[name] != was:
            message = f"the pod {name} was restarted by the passage: {was} then {after[name]}"
            raise ProductionError(message)


def check_before(done: str, started: str) -> None:
    """Hold that a step finished before another began: two times of kubectl, in UTC, in ISO form."""
    if not done or not started or done > started:
        message = f"the migrations ended at {done!r}, after the installation began at {started!r}"
        raise ProductionError(message)
