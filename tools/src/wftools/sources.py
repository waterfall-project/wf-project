# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Check the rules of source files that no linter holds on its own (US-0050).

Usage: ``python -m wftools.sources``.

A rule of lint, typing or format is never silenced in the code: a comment that turns a
tool off for a line or a file fails the chain, and an exception is written in the tool's
configuration instead, with its reason. A source file has 1,000 lines at most. Generated
files are left out, and so are the paths ``tools/paths.toml`` excepts, with their reason.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from wftools import REPOSITORY, paths

MAX_LINES = 1000
"""The largest number of lines a source file may have, blank lines and comments included."""

_HASH = frozenset({".py", ".sh"})
_SLASH = frozenset({".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"})
SOURCES = _HASH | _SLASH

# A suppression is recognised in a comment only, so that a string or a document that names
# one — this module, the guide — is not mistaken for one.
_HASH_SUPPRESSION = re.compile(
    r"#\s*(?:noqa\b|ruff:\s*noqa|type:\s*ignore|pyright:\s*(?:ignore|basic|standard)"
    r"|fmt:\s*(?:off|skip)|pragma:\s*no\s*cover|shellcheck\s+disable)",
)
_SLASH_SUPPRESSION = re.compile(
    r"(?://|/\*|\{/\*)\s*(?:eslint-disable|@ts-(?:ignore|expect-error|nocheck)"
    r"|prettier-ignore|(?:v8|c8|istanbul)\s+ignore)",
)
# Ruff holds the Python side (TD003, FIX001 to FIX004); ESLint has no equivalent, so the
# TypeScript side is held here, the same way: a to-do cites its issue, `TODO(#12): …`, and
# the other tags Ruff refuses are refused too — each is a to-do without an issue.
_SLASH_COMMENT = re.compile(r"(?://|/\*|\{/\*|^\s*\*)(?P<comment>.*)")
_TODO_WITHOUT_ISSUE = re.compile(r"\bTODO\b(?!\(#\d+\))")
_OTHER_TAGS = re.compile(r"\b(?:FIXME|XXX|HACK)\b")


@dataclass(frozen=True, slots=True)
class Breach:
    """A source file that breaks one of the rules, with where and why."""

    path: str
    line: int
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.reason}"


def breaches(path: str, text: str) -> list[Breach]:
    """Return the breaches of one source file, given its path and its content."""
    suffix = Path(path).suffix
    pattern = _HASH_SUPPRESSION if suffix in _HASH else _SLASH_SUPPRESSION
    lines = text.splitlines()
    found = [
        Breach(path, number, f"suppression comment: {match.group(0).strip()}")
        for number, line in enumerate(lines, start=1)
        if (match := pattern.search(line))
    ]
    if suffix in _SLASH:
        found.extend(_tags(path, lines))
    if len(lines) > MAX_LINES:
        found.append(Breach(path, len(lines), f"{len(lines)} lines, {MAX_LINES} at most"))
    return found


def _tags(path: str, lines: list[str]) -> list[Breach]:
    found: list[Breach] = []
    for number, line in enumerate(lines, start=1):
        comment = _SLASH_COMMENT.search(line)
        if comment is None:
            continue
        text = comment.group("comment")
        if _TODO_WITHOUT_ISSUE.search(text):
            found.append(Breach(path, number, "TODO without its issue: write TODO(#12): …"))
        if tag := _OTHER_TAGS.search(text):
            found.append(Breach(path, number, f"{tag.group(0)}: open an issue, cite it in a TODO"))
    return found


def sources(declaration: paths.Declaration) -> list[str]:
    """Return the source files of the repository the rules apply to, committed or not."""
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    output: str = listed.stdout or ""
    return [
        path
        for path in sorted(set(output.splitlines()))
        if Path(path).suffix in SOURCES
        and (REPOSITORY / path).is_file()
        and not declaration.is_generated(path)
        and not declaration.is_excepted(path)
    ]


def main() -> int:
    """Check every source file of the repository, and name each breach."""
    declaration = paths.read()
    checked = sources(declaration)
    found = [
        breach
        for path in checked
        for breach in breaches(path, (REPOSITORY / path).read_text(encoding="utf-8"))
    ]
    for breach in found:
        print(breach, file=sys.stderr)
    print(f"{len(checked)} source files, {len(found)} breach(es)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
