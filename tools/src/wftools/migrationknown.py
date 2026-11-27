# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The known failures of the family ``migrations``, against which its outcomes are judged (US-2850).

Called by the two parts of the family, ``tests`` (``wftools.migrationtests``, ``make
migrations-tests``) and ``backup`` (``wftools.migrationbackup``, ``make migrations-backup``), on the
outcomes their run of pytest wrote (``wftools.migrationreport``).

WF-DAT-0140-A is tried against the last published version, N. A test of N that fails on the schema
the branch migrates, or a backup of N the branch does not take back whole, is an incompatibility:
a finding, settled before the next version is published, not in the lot that finds it. Decided on
2026-11-27 (#4961): an incompatibility already found does not stop the queue. Each failure the
family expects is written in ``tools/migrations-known.toml``, under the version it belongs to, with
the finding that follows it or the category of the tests of N that hold its own schema; the family
fails only on a failure that no entry recognises — a new one —, and on an entry that no longer
fails, so that the list empties as the findings are settled and no entry stays to hide a regression
of the test it names (an expected failure is strict, as ``xfail(strict=True)``). The entries of
another version are not judged: N moving to the next publication leaves them, which the tool says.

An entry recognises a failure by the tests it names — a node of pytest, or a whole file —, by a
pattern of its message, or by both. An entry without tests holds a cause shared by many tests, a
same error of their setting up: it recognises every failure whose message the pattern finds. An
entry is stale when, among the outcomes of the run, a test it names passed, or, without tests, when
it recognised nothing in a run of the whole suite; a test it names that this part did not run
(``SHARD``) is not judged, nor is an entry without tests, whose failures may all lie in another
part, and an entry ``intermittent`` — the collateral of another failure, which lands on whichever
test runs then — is never stale. A part where no test passed nor failed — all skipped, or none —
holds nothing: it fails.
"""

import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from wftools import REPOSITORY
from wftools.migrationreport import FAILED, PASSED, SKIPPED

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

TOOL = "wftools.migrationknown"
KNOWN = REPOSITORY / "tools" / "migrations-known.toml"
PARTS = ("tests", "backup")
CATEGORIES = ("frozen schema",)
"""The categories of an entry without a finding: a test of N that holds its own schema."""
FINDING = re.compile(r"#\d+")
JUDGED = (0, 1)
"""What pytest returns when it ran every test it collected: passed, or some failed."""
SHOWN = 20
"""The new failures written with their message; those past it are named alone."""
LINES = 40
"""The lines of the message of a new failure that are written, its end."""


def named(name: str, test: str) -> bool:
    """Say whether a name of an entry designates a test: its node, its file, or all its cases."""
    return test == name or test.startswith((f"{name}::", f"{name}["))


class KnownError(Exception):
    """A list of known failures, or a report, that cannot be read."""


@dataclass(frozen=True, slots=True)
class Outcome:
    """What one test of the run came to: its node, its status, and the text of its failure."""

    test: str
    status: str
    message: str = ""

    @property
    def failed(self) -> bool:
        """Say whether the test failed, in any of its phases."""
        return self.status == FAILED


@dataclass(frozen=True, slots=True)
class Known:
    """A failure the family expects: of which version and part, why, and how it is recognised."""

    version: str
    part: str
    reason: str
    cause: str
    tests: tuple[str, ...] = ()
    message: re.Pattern[str] | None = None
    intermittent: bool = False
    """A failure that a run may not give: the collateral of another, that lands on whichever test
    runs then. Such an entry is never stale."""

    def names(self, test: str) -> bool:
        """Say whether the entry names the test: no tests named, every test."""
        return not self.tests or any(named(each, test) for each in self.tests)

    def recognises(self, outcome: Outcome) -> bool:
        """Say whether the entry recognises a failure: its test named, its message found."""
        found = self.message is None or self.message.search(outcome.message) is not None
        return outcome.failed and self.names(outcome.test) and found


@dataclass(slots=True)
class Verdict:
    """The outcomes of a run judged against the known failures of its version and part."""

    new: list[Outcome] = field(default_factory=list[Outcome])
    recognised: dict[int, int] = field(default_factory=dict[int, int])
    """For each entry, by its index among those judged, the failures it recognised."""
    stale: list[tuple[Known, str]] = field(default_factory=list[tuple[Known, str]])
    """Each entry that no longer fails, with what says it."""

    @property
    def passed(self) -> bool:
        """Say whether the run holds: no new failure, no entry that no longer fails."""
        return not self.new and not self.stale


def load(text: str) -> list[Known]:
    """Read the known failures, refusing an entry that would recognise anything or nothing."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        message = f"the known failures do not read: {error}"
        raise KnownError(message) from error
    return [_entry(index, each) for index, each in enumerate(data.get("known", []), start=1)]


def _entry(index: int, data: dict[str, Any]) -> Known:
    if refused := _refusal(data):
        message = f"entry {index}: {refused}"
        raise KnownError(message)
    try:
        pattern = re.compile(data["message"]) if data.get("message") else None
    except re.error as error:
        message = f"entry {index}: its message is no pattern: {error}"
        raise KnownError(message) from error
    issue = data.get("issue")
    reason = str(issue if issue is not None else data["category"])
    tests = tuple(str(each) for each in data.get("tests", []))
    intermittent = data.get("intermittent", False) is True
    return Known(data["version"], data["part"], reason, data["cause"], tests, pattern, intermittent)


def _refusal(data: dict[str, Any]) -> str | None:
    """Say why an entry is refused, or None.

    Each says its version, its part, its reason, its cause, and how it recognises a failure.
    """
    version, issue, category = data.get("version"), data.get("issue"), data.get("category")
    cause, tests, message = data.get("cause"), data.get("tests", []), data.get("message")
    refusals = (
        (not isinstance(version, str) or not version.startswith("v"), "its version is vX.Y.Z"),
        (data.get("part") not in PARTS, f"its part is one of {', '.join(PARTS)}"),
        ((issue is None) == (category is None), "it names one of a finding (issue) and a category"),
        (
            issue is not None and not (isinstance(issue, str) and FINDING.fullmatch(issue)),
            "its issue is written #n",
        ),
        (
            category is not None and category not in CATEGORIES,
            f"its category is one of {', '.join(CATEGORIES)}",
        ),
        (not isinstance(cause, str) or not cause.strip(), "it says its cause"),
        (not _nodes(tests), "its tests are a list of nodes of pytest"),
        (message is not None and not isinstance(message, str), "its message is a pattern"),
        (not isinstance(data.get("intermittent", False), bool), "intermittent is true or false"),
        (not tests and not message, "it names its tests, or the message of their failure"),
    )
    return next((said for refused, said in refusals if refused), None)


def _nodes(value: object) -> bool:
    """Say whether a value is a list of names of tests, none empty."""
    if not isinstance(value, list):
        return False
    return all(isinstance(each, str) and each for each in cast("list[object]", value))


def outcomes(report: str) -> list[Outcome]:
    """Read the outcome of each test from what ``wftools.migrationreport`` wrote, a line each."""
    found: list[Outcome] = []
    for number, line in enumerate(report.splitlines(), start=1):
        try:
            data = json.loads(line)
            outcome = Outcome(str(data["test"]), str(data["status"]), str(data["message"]))
        except (ValueError, KeyError, TypeError) as error:
            message = f"line {number} of the report does not read: {error}"
            raise KnownError(message) from error
        if outcome.status not in (PASSED, FAILED, SKIPPED):
            message = f"line {number} of the report has no status of a test: {outcome.status}"
            raise KnownError(message)
        found.append(outcome)
    return found


def judge(run: Sequence[Outcome], known: Sequence[Known], *, whole: bool = True) -> Verdict:
    """Judge the outcomes of a run against the entries of its version and part.

    A failure belongs to the first entry that recognises it. An entry that names its tests is
    stale by each name whose tests ran, one of them at least passed, and none failed as the entry
    says; an entry without tests, when the run is of the whole suite (``whole``, no ``SHARD``) and
    it recognised none of its failures; an intermittent entry, never.
    """
    verdict = Verdict(recognised=dict.fromkeys(range(len(known)), 0))
    for outcome in run:
        if not outcome.failed:
            continue
        index = next((i for i, each in enumerate(known) if each.recognises(outcome)), None)
        if index is None:
            verdict.new.append(outcome)
        else:
            verdict.recognised[index] += 1
    for index, entry in enumerate(known):
        if entry.intermittent:
            continue
        if not entry.tests:
            if whole and run and not verdict.recognised[index]:
                verdict.stale.append((entry, "it recognised no failure"))
            continue
        for name in entry.tests:
            ran = [outcome for outcome in run if named(name, outcome.test)]
            passing = any(outcome.status == PASSED for outcome in ran)
            if passing and not any(entry.recognises(outcome) for outcome in ran):
                verdict.stale.append((entry, f"{name} passes"))
    return verdict


def report_of(verdict: Verdict, known: Sequence[Known], version: str, part: str) -> list[str]:
    """Write what the verdict says, entry by entry, then failure by failure.

    Each entry with what it recognised, then the new failures, the first ones with the end of their
    message, then the entries that no longer fail.
    """
    lines = [
        f"  known, {entry.reason}: {verdict.recognised[index]} failure(s) of {version} ({part})"
        for index, entry in enumerate(known)
    ]
    for number, outcome in enumerate(verdict.new):
        lines.append(f"  new failure: {outcome.test}")
        if number < SHOWN:
            lines += [f"    {line}" for line in outcome.message.splitlines()[-LINES:]]
    lines += [
        f"  no longer fails, {entry.reason}: {said}; its entry leaves {KNOWN.name}"
        for entry, said in verdict.stale
    ]
    return lines


def judged(version: str, part: str, report: Path, code: int, *, whole: bool = True) -> bool:
    """Judge the outcomes a run of a part wrote against the known failures of N, and say it.

    pytest that did not run its tests to their end — interrupted, a usage refused, nothing
    collected — fails whatever its report holds, which may miss the tests it did not run. So does a
    run where no test passed nor failed: its tests skipped, it proved nothing. ``whole`` says the
    run is of the whole suite, not of a part of it (``SHARD``).
    """
    if code not in JUDGED:
        print(
            f"{TOOL}: pytest did not run the tests of {part} to their end ({code})", file=sys.stderr
        )
        return False
    try:
        entries = load(KNOWN.read_text(encoding="utf-8"))
        run = outcomes(report.read_text(encoding="utf-8"))
    except (KnownError, OSError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return False
    if not any(each.status in (PASSED, FAILED) for each in run):
        said = f"{TOOL}: no test of {part} passed or failed: all skipped, or none run"
        print(said, file=sys.stderr)
        return False
    held = [each for each in entries if each.version == version and each.part == part]
    if others := sorted({each.version for each in entries if each.version != version}):
        print(f"  the known failures of {', '.join(others)} are not judged: N is {version}")
    verdict = judge(run, held, whole=whole)
    print("\n".join(report_of(verdict, held, version, part)), flush=True)
    if not verdict.passed:
        print(
            f"{TOOL}: {part}: {len(verdict.new)} new failure(s) of {version} on the schema of the "
            f"branch, {len(verdict.stale)} known failure(s) that no longer fail (US-2850)",
            file=sys.stderr,
        )
    return verdict.passed
