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
- a requirement that no epic closes, or that more than one closes;
- a ``make`` command an agent reads — in ``.claude/agents/``, or in the guide, the common
  rules and the coding rules of ``docs/dev/`` that the agents follow — that the Makefile
  does not have: a target renamed would otherwise leave an agent calling a command that is
  gone (US-0280). Only the files git tracks are read.

It lists, without failing, the F0 requirements no story cites yet — they are cited as the
stories of later epics are written — and the declared exceptions, with their reason. The
example of section 1.3.1 is not a requirement of the product, and is left out.
"""

import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY, projection

ROADMAP = REPOSITORY / "docs" / "roadmap"
MAKEFILE = REPOSITORY / "Makefile"
AGENT_FILES = (".claude/agents/*.md", "docs/dev/*.md")

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
_TARGET = re.compile(r"^([a-z][a-z0-9-]*):", re.MULTILINE)
# A command is cited in code: an inline span or a fenced block. Within it, `make`, its options
# (`-C ..`, `-s`) and then the target, whatever variables come before or after.
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
# A target ends where the word ends: `make check-<famille>` is a pattern, not a command.
_CITED_COMMAND = re.compile(
    r"\bmake\s+(?:-C\s+\S+\s+|-[a-zA-Z]+\s+)*([a-z](?:[a-z0-9-]*[a-z0-9])?)(?=[\s`;&|)]|$)"
)


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


def targets(makefile: str) -> set[str]:
    """Return the targets a Makefile defines."""
    return set(_TARGET.findall(makefile))


def agent_texts(patterns: tuple[str, ...] = AGENT_FILES) -> dict[str, str]:
    """Return, by path, the text of the tracked files the agents read."""
    listed = subprocess.run(
        ["git", "ls-files", "--", *patterns],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    output: str = listed.stdout or ""
    return {
        path: (REPOSITORY / path).read_text(encoding="utf-8")
        for path in sorted(output.splitlines())
        if (REPOSITORY / path).is_file()
    }


def cited_targets(text: str) -> set[str]:
    """Return the Makefile targets a text cites in its code."""
    return {target for code in _CODE.findall(text) for target in _CITED_COMMAND.findall(code)}


def missing_commands(texts: dict[str, str], defined: set[str]) -> list[str]:
    """Return the ``make`` commands the agents cite that the Makefile does not define."""
    return [
        f"{path}: cites `make {target}`, which the Makefile does not define"
        for path, text in texts.items()
        for target in sorted(cited_targets(text))
        if target not in defined
    ]


def main() -> int:
    """Print the confrontation, and fail on a problem."""
    requirements = projection.read()
    findings = confront(read(), requirements)
    findings.problems.extend(
        missing_commands(agent_texts(), targets(MAKEFILE.read_text(encoding="utf-8")))
    )
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
