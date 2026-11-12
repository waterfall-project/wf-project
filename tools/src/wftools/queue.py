# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Report the runs of the merge queue of a branch, and classify their failures (US-1880).

Usage: ``python -m wftools.queue [--branch BRANCH] [--last N] [--since YYYY-MM-DD]``.

The runs are those of the chain (the workflow ``ci.yml``, named ``chain``) on the ``merge_group``
event, read by ``gh``: the merge queue tests a pull request on a reference
``gh-readonly-queue/<branch>/pr-…``, so the branch is the prefix of that reference. Without a
branch, every branch counts. ``--since`` keeps the runs created on that day or after it, in UTC;
``--last`` the most recent of them; without either, the last 50.

For each run the report counts the runs by conclusion, the failures by job and step — and by
target of the Makefile, ``make: *** [Makefile:n: target]`` —, the tests and the paths that failed
with their file and line, read from the log of the failed job (Playwright, pytest, Vitest), the
wall time of the succeeded runs in median and at the 90th percentile, and the runner minutes, the
sum of the durations of the jobs. A failure is classified against ``tools/queue-known.toml``:
known flakiness, infrastructure, or regression, an entry for a regression naming its runs, since
only a reading of the run makes a failure a regression. What no entry recognizes is « to
classify »: the tool never decides alone. ``gate``, which fails because another job failed, is not
a failure of its own unless no other job failed.

The reading by ``gh`` is the class ``GitHub``; everything else works on what it returns, and is
tested on excerpts of real logs. Nothing of this runs in the chain: the command runs from a
workstation (decision of EP-24).
"""

import argparse
import json
import math
import re
import statistics
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Protocol, cast

from wftools import REPOSITORY
from wftools.tracking import TrackingError, gh

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from pathlib import Path

KNOWN = REPOSITORY / "tools" / "queue-known.toml"
WORKFLOW = "ci.yml"
QUEUE = "gh-readonly-queue/"
GATE = "gate"
DEFAULT_LAST = 50
PAGE = 100

FLAKY = "known flakiness"
INFRASTRUCTURE = "infrastructure"
REGRESSION = "regression"
TO_CLASSIFY = "to classify"
KINDS = (FLAKY, INFRASTRUCTURE, REGRESSION)
FAILED_JOB = ("failure", "timed_out", "cancelled")

STAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?")
ESCAPE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
MAKE_ERROR = re.compile(r"^make(?:\[\d+\])?: \*\*\* \[[^:\]]+:\d+: ([^\]]+)\]")
RUNNER_ERROR = "##[error]"
# The runner's own word when a command failed; any other is the cause: « The operation was
# canceled. » for a job past its time.
EXIT = "Process completed with exit code"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
TELLING = re.compile(r"(?i)error|fail|could not|unable|cannot|denied|refused|timed? ?out|\b5\d\d\b")
# Playwright: the list under « N failed », and the numbered block of each failure; its separator
# is U+203A, written as its escape.
PLAYWRIGHT_COUNT = re.compile(r"^\s+\d+ failed$")
PLAYWRIGHT_TEST = re.compile(r"^\s+\[([\w-]+)\] \u203a (\S+?):(\d+):\d+ \u203a (.+?)\s*$")
PLAYWRIGHT_BLOCK = re.compile(r"^\s+\d+\) \[[\w-]+\] \u203a (\S+?):(\d+):\d+ \u203a ")
# A frame names its file from the front's directory: ``at f (/…/frontend/e2e/x.ts:39:22)``.
PLAYWRIGHT_AT = re.compile(r"^\s+at (?:[^(]+ \()?\S*?/frontend/(\S+?:\d+):\d+\)?$")
# pytest: the short summary, the section of each failure, the locations of its traceback.
PYTEST_SUMMARY = re.compile(r"^(FAILED|ERROR) (\S+?\.py)::(.+?)(?: - (.*))?$")
PYTEST_SECTION = re.compile(r"^_+ (?:ERROR at (?:setup|teardown) of )?(\S.*?) _+$")
PYTEST_LOCATION = re.compile(r"^(\S+\.py):(\d+): ?\S*$")
PYTEST_END = re.compile(r"^=+ .* =+$")
# Vitest: « FAIL  [project]  file > describe > test », then « U+276F file:line:column ».
VITEST_FAIL = re.compile(r"^\s*FAIL\s+(?:\S+\s+)?(\S+\.(?:[cm]?[jt]sx?)) > (.+?)\s*$")
VITEST_BLOCK = 12
VITEST_AT = re.compile(r"^\s*\u276f (\S+?):(\d+):\d+")


class QueueError(Exception):
    """A request the tool refuses, or a file it cannot read, said to the user."""


@dataclass(frozen=True, slots=True)
class Job:
    """A job of a run, as the API of the jobs gives it."""

    identifier: int
    name: str
    conclusion: str
    started: datetime | None
    completed: datetime | None
    failed_step: str

    @property
    def minutes(self) -> float:
        """Return how long the job held its runner, in minutes."""
        if self.started is None or self.completed is None or self.completed < self.started:
            return 0.0
        return (self.completed - self.started).total_seconds() / 60


@dataclass(frozen=True, slots=True)
class Run:
    """A run of the chain in the merge queue."""

    identifier: int
    branch: str
    status: str
    conclusion: str
    created: datetime
    started: datetime
    jobs: tuple[Job, ...] = ()

    @property
    def wall(self) -> float | None:
        """Return the wall time of a finished run, from its start to its last job, in minutes."""
        ends = [job.completed for job in self.jobs if job.completed is not None]
        if self.status != "completed" or not ends:
            return None
        return (max(ends) - self.started).total_seconds() / 60


@dataclass(frozen=True, slots=True)
class Failure:
    """What failed in a job: a test or a path, or the job itself when its log names none."""

    run: int
    job: str
    step: str
    target: str = ""
    file: str = ""
    line: int | None = None
    name: str = ""
    where: str = ""
    message: str = ""
    evidence: str = ""

    @property
    def test(self) -> str:
        """Return the test as the report names it: ``file:line``, or the file, or nothing."""
        if not self.file:
            return ""
        return f"{self.file}:{self.line}" if self.line is not None else self.file


@dataclass(frozen=True, slots=True)
class Known:
    """An entry of ``tools/queue-known.toml``: what it recognizes, and how it classifies it."""

    kind: str
    family: str
    issue: str
    job: re.Pattern[str] | None = None
    step: re.Pattern[str] | None = None
    test: re.Pattern[str] | None = None
    lines: tuple[int, int] | None = None
    message: re.Pattern[str] | None = None
    runs: frozenset[int] = frozenset()

    def recognizes(self, failure: Failure) -> bool:
        """Say whether every pattern the entry gives matches the failure."""
        if self.runs and failure.run not in self.runs:
            return False
        if self.job is not None and not self.job.search(failure.job):
            return False
        if self.step is not None and not self.step.search(f"{failure.step}\n{failure.target}"):
            return False
        if self.test is not None and not self.test.search(f"{failure.test} {failure.name}"):
            return False
        if self.lines is not None and (
            failure.line is None or not self.lines[0] <= failure.line <= self.lines[1]
        ):
            return False
        text = f"{failure.where}\n{failure.message}\n{failure.evidence}"
        return self.message is None or self.message.search(text) is not None


@dataclass(slots=True)
class Catalogue:
    """The known failures and the reference."""

    entries: list[Known] = field(default_factory=list[Known])
    reference: str = ""

    def classify(self, failure: Failure) -> tuple[str, Known | None]:
        """Return the class of a failure and the first entry that recognizes it, if any."""
        for entry in self.entries:
            if entry.recognizes(failure):
                return entry.kind, entry
        return TO_CLASSIFY, None


class Source(Protocol):
    """What the report reads from GitHub."""

    def runs(self, page: int, since: date | None) -> list[dict[str, object]]:
        """Return a page of the ``merge_group`` runs of the chain, the most recent first."""
        ...

    def jobs(self, run: int) -> list[dict[str, object]]:
        """Return the jobs of a run, with their steps."""
        ...

    def log(self, job: int) -> str:
        """Return the log of a job."""
        ...


class GitHub:
    """The reading by ``gh``: one call a page of runs, a run's jobs, a job's log."""

    def __init__(self, call: Callable[[list[str]], str] = gh) -> None:
        self.call = call

    def runs(self, page: int, since: date | None) -> list[dict[str, object]]:
        """Return a page of the ``merge_group`` runs of the chain, the most recent first."""
        query = f"event=merge_group&per_page={PAGE}&page={page}"
        if since is not None:
            query += f"&created=>={since.isoformat()}"
        path = f"repos/{{owner}}/{{repo}}/actions/workflows/{WORKFLOW}/runs?{query}"
        answer = _json(self.call(["api", path]), "the runs")
        runs = _member(answer, "workflow_runs")
        if not isinstance(runs, list):
            message = "gh api did not answer the runs of the chain"
            raise QueueError(message)
        return [cast("dict[str, object]", run) for run in cast("list[object]", runs)]

    def jobs(self, run: int) -> list[dict[str, object]]:
        """Return the jobs of a run, with their steps."""
        path = f"repos/{{owner}}/{{repo}}/actions/runs/{run}/jobs?per_page=100"
        answer = _json(self.call(["api", path]), f"the jobs of run {run}")
        jobs = _member(answer, "jobs")
        if not isinstance(jobs, list):
            message = f"gh api did not answer the jobs of run {run}"
            raise QueueError(message)
        return [cast("dict[str, object]", job) for job in cast("list[object]", jobs)]

    def log(self, job: int) -> str:
        """Return the log of a job; its colours are escape sequences ``gh`` must let through."""
        return self.call(
            ["api", "--allow-escape-sequences", f"repos/{{owner}}/{{repo}}/actions/jobs/{job}/logs"]
        )


def _json(text: str, what: str) -> object:
    try:
        return cast("object", json.loads(text))
    except json.JSONDecodeError as error:
        message = f"gh api did not answer JSON for {what}"
        raise QueueError(message) from error


def _member(answer: object, key: str) -> object:
    return cast("dict[str, object]", answer).get(key) if isinstance(answer, dict) else None


def _moment(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value).astimezone(UTC)


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def read_job(data: dict[str, object]) -> Job:
    """Return a job from the API, with the name of its first step that did not succeed."""
    steps = data.get("steps")
    failed = ""
    for step in cast("list[object]", steps) if isinstance(steps, list) else []:
        if isinstance(step, dict):
            step_data = cast("dict[str, object]", step)
            if step_data.get("conclusion") in FAILED_JOB:
                failed = _text(step_data.get("name"))
                break
    return Job(
        identifier=int(cast("int", data["id"])),
        name=_text(data.get("name")),
        conclusion=_text(data.get("conclusion")),
        started=_moment(data.get("started_at")),
        completed=_moment(data.get("completed_at")),
        failed_step=failed,
    )


def read_run(data: dict[str, object]) -> Run:
    """Return a run from the API, without its jobs."""
    created = _moment(data.get("created_at"))
    if created is None:
        message = f"gh api answered a run without its creation: {data.get('id')}"
        raise QueueError(message)
    return Run(
        identifier=int(cast("int", data["id"])),
        branch=_text(data.get("head_branch")),
        status=_text(data.get("status")),
        conclusion=_text(data.get("conclusion")),
        created=created,
        started=_moment(data.get("run_started_at")) or created,
    )


def queued_branch(reference: str) -> str:
    """Return the branch a reference of the merge queue tests, ``main`` for ``…/main/pr-n-sha``."""
    if not reference.startswith(QUEUE):
        return reference
    return reference.removeprefix(QUEUE).rpartition("/pr-")[0]


def select(
    source: Source, branch: str | None, last: int | None, since: date | None
) -> Iterator[Run]:
    """Yield the runs of the branch, the most recent first, read page by page as far as needed."""
    count = 0
    page = 1
    while last is None or count < last:
        listed = source.runs(page, since)
        for data in listed:
            run = read_run(data)
            if branch is not None and queued_branch(run.branch) != branch:
                continue
            yield run
            count += 1
            if last is not None and count >= last:
                return
        if len(listed) < PAGE:
            return
        page += 1


def clean(log: str) -> list[str]:
    """Return the lines of a job's log without their time stamp and colours."""
    return [ESCAPE.sub("", STAMP.sub("", line)).rstrip("\r") for line in log.splitlines()]


def _blocks(lines: list[str]) -> dict[tuple[str, int], list[str]]:
    blocks: dict[tuple[str, int], list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        header = PLAYWRIGHT_BLOCK.match(line)
        if header:
            current = blocks.setdefault((header.group(1), int(header.group(2))), [])
        elif PLAYWRIGHT_COUNT.match(line):
            current = None
        elif current is not None:
            current.append(line)
    return blocks


def playwright(lines: list[str], base: Failure) -> list[Failure]:
    """Return the paths Playwright lists under « N failed », with the block of each failure.

    ``where`` is the first frame of the block, a helper such as ``own-project.ts`` or the path's own
    line; the message, its first ``Error:``; the evidence, the whole block.
    """
    blocks = _blocks(lines)
    found: list[Failure] = []
    listing = False
    for line in lines:
        if PLAYWRIGHT_COUNT.match(line):
            listing = True
            continue
        test = PLAYWRIGHT_TEST.match(line) if listing else None
        if test is None:
            listing = False
            continue
        file, number = test.group(2), int(test.group(3))
        block = blocks.get((file, number), [])
        frames = [m.group(1) for m in map(PLAYWRIGHT_AT.match, block) if m is not None]
        errors = [text.strip() for text in block if text.strip().startswith("Error:")]
        found.append(
            replace(
                base,
                file=file,
                line=number,
                name=test.group(4),
                where=frames[0] if frames else "",
                message=errors[0] if errors else "",
                evidence="\n".join(block),
            )
        )
    return found


def _pytest_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in lines:
        section = PYTEST_SECTION.match(line)
        if section and not section.group(1).startswith("_ "):
            current = sections.setdefault(section.group(1), [])
        elif PYTEST_END.match(line):
            current = None
        elif current is not None:
            current.append(line)
    return sections


def pytest(lines: list[str], base: Failure) -> list[Failure]:
    """Return the tests of pytest's short summary, with the section of each failure.

    The line is the last of the traceback in the test's own file; ``where`` the last location of
    the traceback, which a fixture or a helper may hold; the evidence, the whole section.
    """
    sections = _pytest_sections(lines)
    found: list[Failure] = []
    for line in lines:
        summary = PYTEST_SUMMARY.match(line)
        if summary is None:
            continue
        file, name = summary.group(2), summary.group(3)
        body = sections.get(name.replace("::", "."), [])
        locations = [m for m in map(PYTEST_LOCATION.match, body) if m is not None]
        own = [int(m.group(2)) for m in locations if m.group(1) == file]
        found.append(
            replace(
                base,
                file=file,
                line=own[-1] if own else None,
                name=name,
                where=f"{locations[-1].group(1)}:{locations[-1].group(2)}" if locations else "",
                message=summary.group(4) or "",
                evidence="\n".join(body),
            )
        )
    return found


def vitest(lines: list[str], base: Failure) -> list[Failure]:
    """Return the tests Vitest says ``FAIL``, with the first frame and the error under each."""
    found: list[Failure] = []
    for index, line in enumerate(lines):
        failed = VITEST_FAIL.match(line)
        if failed is None:
            continue
        file = failed.group(1)
        block: list[str] = []
        for following in lines[index + 1 : index + VITEST_BLOCK]:
            if VITEST_FAIL.match(following):
                break
            block.append(following)
        frames = [m for m in map(VITEST_AT.match, block) if m is not None]
        said = [text.strip() for text in block if text.strip() and not VITEST_AT.match(text)]
        own = [int(m.group(2)) for m in frames if m.group(1) == file]
        found.append(
            replace(
                base,
                file=file,
                line=own[0] if own else None,
                name=failed.group(2),
                where=f"{frames[0].group(1)}:{frames[0].group(2)}" if frames else "",
                message=said[0] if said else "",
                evidence="\n".join(block),
            )
        )
    return found


def outcome(lines: list[str]) -> tuple[str, str, str]:
    """Return the target of the Makefile that failed, the telling line, and the lines before it.

    The evidence is the end of the log before its first error of the runner, where a download
    refused or a package missing is said; the telling line, the runner's error when it is not the
    exit code of a command, else the last line of the evidence that names an error. An identifier
    of the run in it (the temporary script of a step) is elided, for the shards to be told alike.
    """
    target = ""
    for line in lines:
        made = MAKE_ERROR.match(line)
        if made:
            target = made.group(1)
            break
    end = next((i for i, line in enumerate(lines) if line.startswith(RUNNER_ERROR)), len(lines))
    tail = [
        line.strip()
        for line in lines[max(0, end - 30) : end]
        if line.strip() and not MAKE_ERROR.match(line)
    ]
    error = lines[end].removeprefix(RUNNER_ERROR).strip() if end < len(lines) else ""
    telling = [line for line in tail if TELLING.search(line) and not line.startswith("hint:")]
    if error and not error.startswith(EXIT):
        message = error
    else:
        message = telling[-1] if telling else tail[-1] if tail else error
    return target, UUID.sub("…", message), "\n".join([*tail, error])


def failures_of(run: int, job: Job, log: str) -> list[Failure]:
    """Return what failed in a job, read from its log: its tests, or the job itself."""
    lines = clean(log)
    target, message, evidence = outcome(lines)
    base = Failure(run=run, job=job.name, step=job.failed_step, target=target)
    tests = [*playwright(lines, base), *pytest(lines, base), *vitest(lines, base)]
    once = list({(test.file, test.line, test.name): test for test in reversed(tests)}.values())
    return once[::-1] or [replace(base, message=message, evidence=evidence)]


def failed_jobs(run: Run) -> list[Job]:
    """Return the jobs a failed run failed by: ``gate`` only when no other job failed."""
    failed = [job for job in run.jobs if job.conclusion in FAILED_JOB]
    own = [job for job in failed if job.name != GATE]
    return own or failed


def gather(source: Source, runs: Iterable[Run]) -> tuple[list[Run], list[Failure]]:
    """Read the jobs of each run, and the log of each job a failed run failed by."""
    read: list[Run] = []
    failures: list[Failure] = []
    for listed in runs:
        jobs = tuple(read_job(job) for job in source.jobs(listed.identifier))
        run = replace(listed, jobs=jobs)
        read.append(run)
        if run.conclusion != "failure":
            continue
        for job in failed_jobs(run):
            try:
                log = source.log(job.identifier)
            except (TrackingError, QueueError) as error:
                log = f"{RUNNER_ERROR}log unreadable: {error}"
            failures.extend(failures_of(run.identifier, job, log))
    return read, failures


ENTRY_KEYS = frozenset(
    (
        "class",
        "family",
        "issue",
        "frequency",
        "cause",
        "job",
        "step",
        "test",
        "lines",
        "message",
        "runs",
    )
)
CAUSES = ("établie : ", "hypothèse : ")
BOUNDS = 2


def _pattern(entry: dict[str, object], key: str, where: str) -> re.Pattern[str] | None:
    value = entry.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        message = f"{where}: {key} is not a pattern"
        raise QueueError(message)
    try:
        return re.compile(value)
    except re.error as error:
        message = f"{where}: {key} is not a regular expression: {error}"
        raise QueueError(message) from error


def _required(entry: dict[str, object], key: str, where: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        message = f"{where}: {key} is missing"
        raise QueueError(message)
    return value


def _numbers(entry: dict[str, object], key: str, where: str) -> list[int]:
    value = entry.get(key, [])
    if not isinstance(value, list) or not all(
        isinstance(item, int) for item in cast("list[object]", value)
    ):
        message = f"{where}: {key} is not a list of numbers"
        raise QueueError(message)
    return cast("list[int]", value)


def _lines(entry: dict[str, object], where: str) -> tuple[int, int] | None:
    if "lines" not in entry:
        return None
    lines = _numbers(entry, "lines", where)
    if len(lines) != BOUNDS or lines[0] > lines[1] or "test" not in entry:
        message = f"{where}: lines is [first, last], beside a test"
        raise QueueError(message)
    return lines[0], lines[1]


def read_entry(entry: dict[str, object], where: str) -> Known:
    """Return an entry of the known failures, refusing one that would recognize badly."""
    unknown = sorted(set(entry) - ENTRY_KEYS)
    if unknown:
        message = f"{where}: unknown keys {', '.join(unknown)}"
        raise QueueError(message)
    kind = _required(entry, "class", where)
    if kind not in KINDS:
        message = f"{where}: class {kind!r} is none of {', '.join(KINDS)}"
        raise QueueError(message)
    _required(entry, "frequency", where)
    if not _required(entry, "cause", where).startswith(CAUSES):
        message = f"{where}: the cause opens with « établie : » or « hypothèse : »"
        raise QueueError(message)
    runs = frozenset(_numbers(entry, "runs", where))
    if kind == REGRESSION and not runs:
        message = f"{where}: a regression names the runs a reading found it in"
        raise QueueError(message)
    known = Known(
        kind=kind,
        family=_required(entry, "family", where),
        issue=_required(entry, "issue", where),
        job=_pattern(entry, "job", where),
        step=_pattern(entry, "step", where),
        test=_pattern(entry, "test", where),
        lines=_lines(entry, where),
        message=_pattern(entry, "message", where),
        runs=runs,
    )
    if not (known.job or known.step or known.test or known.message or known.runs):
        message = f"{where}: the entry recognizes nothing"
        raise QueueError(message)
    return known


def read_reference(data: object) -> str:
    """Return the reference as the report prints it, or nothing when the file has none."""
    if data is None:
        return ""
    try:
        table = cast("dict[str, object]", data)
        within = cast("dict[str, int]", table["failed_in"])
        days = cast("list[date]", table["wall_days"])
        detail = ", ".join(f"{n} in {job}" for job, n in within.items())
        return (
            f"reference, every branch, from {table['since']} to {table['until']}: "
            f"{table['runs']} runs, {table['failed']} failed ({detail}); median wall time "
            f"{table['wall_median']} min on {' and '.join(str(day) for day in days)}"
        )
    except (KeyError, AttributeError, TypeError) as error:
        message = f"the reference of the known failures is incomplete: {error}"
        raise QueueError(message) from error


def read_catalogue(path: Path = KNOWN) -> Catalogue:
    """Return the known failures and the reference of ``tools/queue-known.toml``."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        message = f"{path.name} cannot be read: {error}"
        raise QueueError(message) from error
    entries = data.get("known", [])
    if not isinstance(entries, list):
        message = f"{path.name}: known is not a list of tables"
        raise QueueError(message)
    catalogue = Catalogue(reference=read_reference(data.get("reference")))
    for index, entry in enumerate(cast("list[object]", entries), start=1):
        if not isinstance(entry, dict):
            message = f"{path.name}: known entry {index} is not a table"
            raise QueueError(message)
        catalogue.entries.append(read_entry(cast("dict[str, object]", entry), f"known {index}"))
    return catalogue


def percentile(values: list[float], rank: float) -> float:
    """Return a percentile by the nearest rank: the smallest value with ``rank`` of them at most."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(rank * len(ordered)) - 1)]


SEVERITY = (REGRESSION, TO_CLASSIFY, FLAKY, INFRASTRUCTURE)
SHARD = re.compile(r"\s*\(\d+/\d+\)$")


def _label(kind: str, entry: Known | None) -> str:
    return f"{kind} ({entry.family}, {entry.issue})" if entry is not None else kind


def durations(runs: list[Run]) -> list[str]:
    """Return the wall time of the succeeded runs and the runner minutes of the finished ones."""
    walls = [run.wall for run in runs if run.conclusion == "success" and run.wall is not None]
    used = [sum(job.minutes for job in run.jobs) for run in runs if run.status == "completed"]
    lines: list[str] = []
    if walls:
        lines.append(
            f"wall time of the {len(walls)} succeeded runs: median "
            f"{statistics.median(walls):.1f} min, 90th percentile {percentile(walls, 0.9):.1f} min"
        )
    if used:
        lines.append(
            f"runner minutes of the {len(used)} finished runs: {sum(used):.1f} in all, "
            f"median {statistics.median(used):.1f} a run"
        )
    return lines


def _summary(runs: list[Run], kinds: dict[int, set[str]], branch: str | None) -> list[str]:
    counted = Counter(
        run.conclusion if run.status == "completed" else "not finished" for run in runs
    )
    worst = Counter(min(found, key=SEVERITY.index) for found in kinds.values())
    finished = counted["success"] + counted["failure"]
    without = worst[FLAKY] + worst[INFRASTRUCTURE]
    rate = 100 * without / finished if finished else 0.0
    first, latest = min(run.created for run in runs), max(run.created for run in runs)
    head = (
        f"chain, merge_group, {branch or 'every branch'}: {len(runs)} runs created from "
        f"{first:%Y-%m-%d %H:%M} to {latest:%Y-%m-%d %H:%M} UTC"
    )
    ends = (
        f"  {counted['success']} succeeded, {counted['failure']} failed, "
        f"{counted['cancelled']} cancelled, {counted['not finished']} not finished"
    )
    classes = (
        f"  failed without regression: {without} of {finished} finished runs ({rate:.1f} %) — "
        f"known flakiness {worst[FLAKY]}, infrastructure {worst[INFRASTRUCTURE]}; "
        f"to classify {worst[TO_CLASSIFY]}; regression {worst[REGRESSION]}"
    )
    return [
        head,
        ends,
        classes,
        *(f"  {line}" for line in durations(runs)),
    ]


def _by_step(failures: list[Failure]) -> list[str]:
    seen = {(SHARD.sub("", f.job), f.step, f.target, f.run) for f in failures}
    steps = Counter((job, step, target) for job, step, target, _ in seen)
    lines = ["failed runs by job and step:"] if steps else []
    for (job, step, target), n in sorted(steps.items(), key=lambda item: (-item[1], item[0])):
        made = f" (make {target})" if target else ""
        lines.append(f"  {n:4}  {job} — {step or 'no failed step'}{made}")
    return lines


def _by_test(classified: list[tuple[Failure, str, Known | None]]) -> list[str]:
    tests: dict[str, tuple[set[int], str, str]] = {}
    for failure, kind, entry in classified:
        if failure.test:
            runs, _, _ = tests.setdefault(failure.test, (set(), failure.name, _label(kind, entry)))
            runs.add(failure.run)
    lines = ["failed tests and paths:"] if tests else []
    for test, (runs, name, label) in sorted(tests.items(), key=lambda t: (-len(t[1][0]), t[0])):
        lines.append(f"  {len(runs):4}  {test}  {name[:80]}  [{label}]")
    return lines


def _by_run(classified: list[tuple[Failure, str, Known | None]]) -> list[str]:
    """Return each failure of each run, the shards of a job that failed alike said once."""
    lines: dict[str, int] = {}
    for failure, kind, entry in classified:
        what = failure.test or failure.message[:120]
        at = f" at {failure.where}" if failure.where and failure.where != failure.test else ""
        job = SHARD.sub("", failure.job)
        line = f"  {failure.run}  {job} — {failure.step}: {what}{at}  [{_label(kind, entry)}]"
        lines[line] = lines.get(line, 0) + 1
    listed = [f"{line} ({n} jobs)" if n > 1 else line for line, n in lines.items()]
    return ["failures, run by run:", *listed] if listed else []


def report(
    runs: list[Run], failures: list[Failure], catalogue: Catalogue, branch: str | None
) -> str:
    """Return the report of the runs and their failures, classified against the catalogue."""
    if not runs:
        return f"no run of the merge queue for {branch or 'any branch'} in the window\n"
    classified = [(failure, *catalogue.classify(failure)) for failure in failures]
    kinds: dict[int, set[str]] = {}
    for failure, kind, _ in classified:
        kinds.setdefault(failure.run, set()).add(kind)
    out = [
        *_summary(runs, kinds, branch),
        *_by_step(failures),
        *_by_test(classified),
        *_by_run(classified),
    ]
    if catalogue.reference:
        out.append(catalogue.reference)
    return "\n".join(out) + "\n"


def window(branch: str, last: str, since: str) -> tuple[str | None, int | None, date | None]:
    """Return the branch, the number of runs and the first day the command line asks for."""
    try:
        count = int(last) if last else None
        first = date.fromisoformat(since) if since else None
    except ValueError as error:
        message = f"LAST is a number of runs, SINCE a date YYYY-MM-DD: {error}"
        raise QueueError(message) from error
    if count is not None and count < 1:
        message = "LAST is at least 1"
        raise QueueError(message)
    if count is None and first is None:
        count = DEFAULT_LAST
    return branch or None, count, first


def main(arguments: list[str], source: Source | None = None, known: Path = KNOWN) -> int:
    """Print the report of the merge queue of a branch; fail on what cannot be read."""
    parser = argparse.ArgumentParser(prog="wftools.queue", description="Report the merge queue.")
    parser.add_argument("--branch", default="", help="epic/EP-nn or main; every branch if empty")
    parser.add_argument("--last", default="", help=f"the most recent runs ({DEFAULT_LAST})")
    parser.add_argument("--since", default="", help="the runs created from this day, YYYY-MM-DD")
    options = parser.parse_args(arguments)
    try:
        branch, last, since = window(options.branch, options.last, options.since)
        catalogue = read_catalogue(known)
        reader = source if source is not None else GitHub()
        runs, failures = gather(reader, select(reader, branch, last, since))
    except (QueueError, TrackingError) as error:
        print(f"queue-report: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(report(runs, failures, catalogue, branch))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
