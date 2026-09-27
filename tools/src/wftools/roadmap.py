# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Confront the stories of ``docs/roadmap`` with the requirements of the document (US-0070).

Usage: ``python -m wftools.roadmap``.

It fails on what would let a requirement slip through the plan unnoticed:

- a table row or a story that cites an identifier the document does not have, or a
  revision the document has moved past;
- a requirement an epic's table lists but none of its stories cites — unless the epic is
  still ``à planifier``, its stories not yet written;
- a sentence of the Vérif field of a requirement a story cites, missing from the story or
  truncated in it: acceptance criteria take the Vérif word for word, as a criterion or as
  a deviation (« écart »), because they become the test cases;
- a requirement that no epic closes, or that more than one closes.

It lists, without failing, the F0 requirements no story cites yet — they are cited as the
stories of later epics are written — and the declared exceptions, with their reason. The
example of section 1.3.1 is not a requirement of the product, and is left out.
"""

import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY, projection

ROADMAP = REPOSITORY / "docs" / "roadmap"

EXCEPTIONS: dict[str, str] = {}
"""F0 requirements no story is meant to cite, each with its reason. None so far."""

TO_PLAN = "à planifier"

_FRONT_MATTER = re.compile(r"\A---\n(?P<fields>.*?)\n---\n", re.DOTALL)
_ROW = re.compile(
    r"^\| `(?P<id>WF-[A-Z]+-\d{4}-[A-Z])` \|[^|]*\| (?P<scope>[^|]+?) \|", re.MULTILINE
)
_STORY = re.compile(r"^## (?P<id>US-\d{4}) — .*?(?=^## US-\d{4} — |\Z)", re.MULTILINE | re.DOTALL)
_STORY_REQUIREMENTS = re.compile(r"^- \*\*exigences\*\* : (?P<cited>.*)$", re.MULTILINE)
_IDENTIFIER = re.compile(r"WF-[A-Z]+-\d{4}-[A-Z]")


@dataclass(frozen=True, slots=True)
class Row:
    """A requirement in the table of an epic, and whether this epic closes it."""

    requirement: str
    closes: bool


@dataclass(frozen=True, slots=True)
class Story:
    """A story: the requirements it cites, and its whole text."""

    identifier: str
    requirements: tuple[str, ...]
    text: str


@dataclass(frozen=True, slots=True)
class Epic:
    """An epic file: its status, its table, its stories."""

    identifier: str
    status: str
    rows: tuple[Row, ...]
    stories: tuple[Story, ...]


def parse_epic(name: str, text: str) -> Epic:
    """Read an epic file."""
    front = _FRONT_MATTER.match(text)
    lines = front.group("fields").splitlines() if front else []
    fields = {
        key.strip(): value.strip() for key, _, value in (line.partition(":") for line in lines)
    }
    rows = tuple(
        Row(match.group("id"), not match.group("scope").startswith("début"))
        for match in _ROW.finditer(text)
    )
    stories = tuple(_story(match.group("id"), match.group(0)) for match in _STORY.finditer(text))
    return Epic(fields.get("id", name), fields.get("statut", ""), rows, stories)


def _story(identifier: str, text: str) -> Story:
    cited = _STORY_REQUIREMENTS.search(text)
    requirements = tuple(_IDENTIFIER.findall(cited.group("cited"))) if cited else ()
    return Story(identifier, requirements, text)


def read(roadmap: Path = ROADMAP) -> tuple[Epic, ...]:
    """Read every epic file of the roadmap, in the order of their identifiers."""
    return tuple(
        parse_epic(path.stem, path.read_text(encoding="utf-8"))
        for path in sorted(roadmap.glob("EP-*.md"))
    )


@dataclass(frozen=True, slots=True)
class Findings:
    """What the confrontation fails on, and what it only lists."""

    problems: list[str]
    uncited: list[str]


def confront(epics: tuple[Epic, ...], requirements: tuple[projection.Requirement, ...]) -> Findings:
    """Confront the epics with the requirements of the document."""
    by_identifier = {r.identifier: r for r in requirements}
    by_key = {r.key: r for r in requirements}
    problems: list[str] = []

    def known(identifier: str, where: str) -> bool:
        if identifier in by_identifier:
            return True
        current = by_key.get(identifier[:-2])
        now = f", now {current.identifier}" if current else ", unknown"
        problems.append(f"{where}: cites {identifier}{now}")
        return False

    closures: dict[str, list[str]] = defaultdict(list)
    cited: set[str] = set()
    for epic in epics:
        for row in epic.rows:
            if known(row.requirement, f"{epic.identifier} table") and row.closes:
                closures[row.requirement].append(epic.identifier)
        for story in epic.stories:
            text = projection.normalize(story.text)
            for identifier in story.requirements:
                if not known(identifier, story.identifier):
                    continue
                cited.add(identifier)
                problems.extend(
                    f"{story.identifier}: {identifier}: missing or truncated: « {sentence} »"
                    for sentence in by_identifier[identifier].verification_sentences
                    if sentence not in text
                )
        if epic.status != TO_PLAN:
            in_stories = {i for story in epic.stories for i in story.requirements}
            problems.extend(
                f"{epic.identifier}: {row.requirement} is in the table but no story cites it"
                for row in epic.rows
                if row.requirement not in in_stories
            )
    for requirement in requirements:
        if requirement.is_example:
            continue
        closing = closures.get(requirement.identifier, [])
        if len(closing) != 1:
            by = ", ".join(closing) if closing else "no epic"
            problems.append(f"{requirement.identifier}: closed by {by}, and by one epic only")
    uncited = [
        r.identifier
        for r in requirements
        if r.is_mandatory and r.identifier not in cited and r.identifier not in EXCEPTIONS
    ]
    return Findings(problems, uncited)


def main() -> int:
    """Print the confrontation, and fail on a problem."""
    requirements = projection.read()
    findings = confront(read(), requirements)
    for problem in findings.problems:
        print(problem, file=sys.stderr)
    mandatory = sum(r.is_mandatory for r in requirements)
    print(f"{mandatory - len(findings.uncited)} of {mandatory} F0 requirements cited by a story")
    for identifier, reason in sorted(EXCEPTIONS.items()):
        print(f"  exception  {identifier}  {reason}")
    print(f"{len(findings.problems)} problem(s)")
    return 1 if findings.problems else 0


if __name__ == "__main__":
    sys.exit(main())
