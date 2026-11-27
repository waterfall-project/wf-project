# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Cancel the runs of the chain that the merge queue has made stale (US-2800/L7, #5122).

The merge queue builds a pull request on a ref of its own,
``gh-readonly-queue/<base>/pr-<N>-<sha>``, and builds it again on a new sha when the queue is
rebuilt. The concurrency group of the chain cannot catch the old run, whose ref differs, so it
kept the runners while the new ones waited and timed out. On a ``merge_group`` event, the first
job of the chain runs this module: it cancels the runs of ``chain`` that are queued or in progress
and whose ref is an earlier build of the same pull request in the same queue (same base, same
number, another sha, an older run than its own: a newer one is the live build), and those of a
pull request that has left the queue. It never touches another base, another event, or its own run.

Usage: ``python -m wftools.queuecancel`` with ``GH_TOKEN``, ``GITHUB_REPOSITORY``,
``GITHUB_RUN_ID`` and ``GITHUB_REF_NAME`` set, as the chain sets them. When the list of the pull
requests in the queue cannot be read, only the earlier builds of the same pull request are
cancelled: an error never empties the queue.
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import cast

from wftools.tracking import TrackingError, gh

REF = re.compile(r"gh-readonly-queue/(?P<base>.+)/pr-(?P<number>\d+)-(?P<sha>[0-9a-f]+)")
PENDING = frozenset({"queued", "waiting", "pending", "requested", "in_progress"})
WORKFLOW = "chain"
ENTRIES = (
    "query($owner: String!, $name: String!, $branch: String!) { repository(owner: $owner,"
    " name: $name) { mergeQueue(branch: $branch) { entries(first: 100) { totalCount nodes {"
    " pullRequest { number } } } } } }"
)


@dataclass(frozen=True)
class Build:
    """A build of the merge queue: the base branch, the pull request and the sha it was built on."""

    base: str
    number: int
    sha: str


def parse_ref(ref: str) -> Build | None:
    """Read a ref of the merge queue; ``None`` for any other ref."""
    found = REF.fullmatch(ref)
    if found is None:
        return None
    return Build(found["base"], int(found["number"]), found["sha"])


def stale(
    runs: list[dict[str, object]], current: str, current_id: int, in_queue: set[int] | None
) -> list[tuple[dict[str, object], int]]:
    """Return the runs to cancel, each with its pull request.

    ``in_queue`` is the numbers of the pull requests the queue of the base holds, or ``None`` when
    it could not be read: then only the earlier builds of the current pull request are stale.
    """
    mine = parse_ref(current)
    if mine is None:
        return []
    chosen: list[tuple[dict[str, object], int]] = []
    for run in runs:
        build = parse_ref(str(run.get("headBranch", "")))
        if (
            build is None
            or build.base != mine.base
            or run.get("event") != "merge_group"
            or run.get("status") not in PENDING
            or run.get("databaseId") == current_id
        ):
            continue
        identifier = run.get("databaseId")
        earlier = (
            build.number == mine.number
            and build.sha != mine.sha
            and isinstance(identifier, int)
            and identifier < current_id
        )
        left = in_queue is not None and build.number not in in_queue
        if earlier or left:
            chosen.append((run, build.number))
    return chosen


def list_runs() -> list[dict[str, object]]:
    """Read the runs of the chain of the merge queue, the latest hundred."""
    text = gh(
        [
            *("run", "list", "--workflow", WORKFLOW, "--event", "merge_group", "--limit", "100"),
            *("--json", "databaseId,headBranch,status,event,url"),
        ]
    )
    return cast("list[dict[str, object]]", json.loads(text))


def queued_numbers(repository: str, base: str) -> set[int] | None:
    """Read the pull requests in the queue of a base, or ``None`` when it cannot be read."""
    owner, name = repository.split("/", 1)
    try:
        text = gh(
            [
                *("api", "graphql", "-f", f"query={ENTRIES}", "-f", f"owner={owner}"),
                *("-f", f"name={name}", "-f", f"branch={base}"),
            ]
        )
        queue = json.loads(text)["data"]["repository"]["mergeQueue"]
        nodes = queue["entries"]["nodes"]
        if queue["entries"]["totalCount"] > len(nodes):
            print(f"queue truncated ({len(nodes)} of {queue['entries']['totalCount']}): not used")
            return None
        return {node["pullRequest"]["number"] for node in queue["entries"]["nodes"]}
    except (TrackingError, KeyError, TypeError, ValueError) as error:
        print(f"queue unreadable, only the earlier builds of the pull request: {error}")
        return None


def main() -> int:
    """Cancel the stale runs, writing each to the log; never fail the chain."""
    environment = os.environ
    ref = environment["GITHUB_REF_NAME"]
    mine = parse_ref(ref)
    if mine is None:
        print(f"{ref} is not a ref of the merge queue: nothing to cancel")
        return 0
    try:
        runs = list_runs()
    except (TrackingError, ValueError) as error:
        print(f"::warning::runs of the chain unreadable, nothing cancelled: {error}")
        return 0
    # The runs first, then the queue: a pull request that enters the queue between the two reads
    # has its run missing from the list, not wrongly classed as having left the queue.
    in_queue = queued_numbers(environment["GITHUB_REPOSITORY"], mine.base)
    for run, number in stale(runs, ref, int(environment["GITHUB_RUN_ID"]), in_queue):
        print(f"cancel run {run['databaseId']} {run['url']}: #{number}, {run['headBranch']}")
        try:
            gh(["run", "cancel", str(run["databaseId"])])
        except TrackingError as error:
            # A run that has just finished answers 409: housekeeping, not a failure of the chain.
            print(f"::warning::run {run['databaseId']} not cancelled: {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
