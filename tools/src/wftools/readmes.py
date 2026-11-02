# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Hold the English READMEs of ``docs/`` in step with their French originals.

Usage: ``python -m wftools.readmes``.

Each directory of ``docs/`` has its README in English, ``README.md``, next to its French
original, ``README-fr.md``, which prevails where they differ. A change to the original carries
the same change to the translation, in the same pull request (docs/dev/README-fr.md, « Branches,
lots et pull requests »). The check cannot judge a translation; it proves that its structure
follows: it reads the state of the repository, not a diff, and fails, naming the file:

- on a ``README-fr.md`` without its ``README.md``, or a ``README.md`` without its original;
- on a pair whose headings differ, one for one: in number, or in level at some rank.

Headings are the ATX headings of Markdown, ``#`` to ``######``, outside fenced code blocks.
"""

import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY

DOCS = REPOSITORY / "docs"
"""The directories whose READMEs are held in pairs, one level below it."""
ORIGINAL = "README-fr.md"
"""The French original, which prevails."""
TRANSLATION = "README.md"
"""The English translation, which follows it."""

_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*#*[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


@dataclass(frozen=True, slots=True)
class Heading:
    """A heading of a README: its line, its level and its text."""

    line: int
    level: int
    text: str


@dataclass(frozen=True, slots=True)
class Finding:
    """A pair of READMEs out of step, with the reason."""

    path: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


def _closes(line: str, fence: str) -> bool:
    """Tell whether a line closes the code block a fence opened.

    It does with the character of the fence, as many times at least, and nothing after it.
    """
    marker = line.strip()
    return set(marker) == {fence[0]} and len(marker) >= len(fence)


def headings(text: str) -> list[Heading]:
    """Return the headings of a Markdown text, in order, those of fenced code blocks left out."""
    found: list[Heading] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if opened := _FENCE.match(line):
            marker = opened.group(1)
            if fence is None:
                fence = marker
            elif _closes(line, fence):
                fence = None
            continue
        if fence is None and (heading := _HEADING.match(line)):
            found.append(Heading(number, len(heading.group(1)), (heading.group(2) or "").strip()))
    return found


def compare(original: str, translation: str, path: str) -> Iterator[Finding]:
    """Yield what makes the headings of a translation differ from those of its original."""
    ours, theirs = headings(original), headings(translation)
    for rank, (source, target) in enumerate(zip(ours, theirs, strict=False), start=1):
        if source.level != target.level:
            yield Finding(
                path,
                f"heading {rank} is of level {target.level} at line {target.line}, "
                f"where {ORIGINAL} has level {source.level} at line {source.line} "
                f"({source.text!r})",
            )
            return
    if len(ours) != len(theirs):
        rank = min(len(ours), len(theirs))
        missing = (
            f"{ORIGINAL} goes on with {ours[rank].text!r} at line {ours[rank].line}"
            if len(ours) > rank
            else f"it goes on with {theirs[rank].text!r} at line {theirs[rank].line}"
        )
        yield Finding(
            path,
            f"{len(theirs)} heading(s), where {ORIGINAL} has {len(ours)}; "
            f"they agree up to heading {rank}, then {missing}",
        )


def check(docs: Path) -> list[Finding]:
    """Check every pair of READMEs of the directories directly under ``docs``."""
    findings: list[Finding] = []
    for directory in sorted(path for path in docs.iterdir() if path.is_dir()):
        original, translation = directory / ORIGINAL, directory / TRANSLATION
        shown = translation.relative_to(docs.parent).as_posix()
        if not original.is_file() and not translation.is_file():
            continue
        if not original.is_file():
            findings.append(Finding(shown, f"no French original {ORIGINAL} next to it"))
        elif not translation.is_file():
            findings.append(
                Finding(
                    original.relative_to(docs.parent).as_posix(),
                    f"no English {TRANSLATION} next to it",
                )
            )
        else:
            findings += compare(
                original.read_text(encoding="utf-8"),
                translation.read_text(encoding="utf-8"),
                shown,
            )
    return findings


def main() -> int:
    """Check the READMEs of the repository, and name each pair out of step."""
    findings = check(DOCS)
    for finding in findings:
        print(finding, file=sys.stderr)
    pairs = len(list(DOCS.glob(f"*/{ORIGINAL}")))
    print(f"{pairs} pair(s) of READMEs under docs/, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
