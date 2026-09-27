# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Read ``tools/paths.toml``: the families of checks, the generated paths and the tests.

The chain, ``make check``, the size of a lot and the size limit of a source file all need
to know the same things about a path — which checks it wakes up, whether a tool wrote it,
whether it is a test. They read it here, from one declaration.
"""

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from wftools import REPOSITORY

DECLARATION = REPOSITORY / "tools" / "paths.toml"

_TOP = {"shared", "families", "generated", "tests"}
_FAMILY = {"paths", "always", "target"}
_GENERATED = {"paths", "by"}


class DeclarationError(ValueError):
    """The declaration does not have the shape this reader expects."""


def matches(path: str, patterns: Iterable[str]) -> bool:
    """Whether a repository-relative path matches one of the patterns."""
    candidate = PurePosixPath(path)
    return any(candidate.full_match(pattern) for pattern in patterns)


@dataclass(frozen=True, slots=True)
class Family:
    """A family of checks, run by one Makefile target and one workflow."""

    name: str
    target: str
    paths: tuple[str, ...]
    always: bool

    def is_touched_by(self, path: str) -> bool:
        """Whether a change to this path wakes this family up."""
        return self.always or matches(path, self.paths)


@dataclass(frozen=True, slots=True)
class Generated:
    """Paths that a tool writes, with the command that writes them."""

    paths: tuple[str, ...]
    by: str


@dataclass(frozen=True, slots=True)
class Declaration:
    """Everything ``tools/paths.toml`` declares."""

    shared: tuple[str, ...]
    families: tuple[Family, ...]
    generated: tuple[Generated, ...]
    tests: tuple[str, ...]

    def is_generated(self, path: str) -> bool:
        """Whether a tool writes this path."""
        return any(matches(path, entry.paths) for entry in self.generated)

    def is_test(self, path: str) -> bool:
        """Whether this path holds tests."""
        return matches(path, self.tests)

    def touched(self, changed: Iterable[str]) -> tuple[Family, ...]:
        """The families that a change to these paths wakes up, in declaration order."""
        paths = list(changed)
        if any(matches(path, self.shared) for path in paths):
            return self.families
        return tuple(
            family
            for family in self.families
            if family.always or any(family.is_touched_by(path) for path in paths)
        )


def parse(text: str) -> Declaration:
    """Read a declaration; raises DeclarationError on a key it does not know or lacks."""
    data = tomllib.loads(text)
    _only(data, _TOP, "the declaration")
    families = tuple(_family(name, entry) for name, entry in data.get("families", {}).items())
    generated = tuple(
        _generated(number, entry)
        for number, entry in enumerate(data.get("generated", []), start=1)
    )
    tests = data.get("tests", {})
    _only(tests, {"paths"}, "[tests]")
    return Declaration(
        shared=tuple(data.get("shared", ())),
        families=families,
        generated=generated,
        tests=tuple(tests.get("paths", ())),
    )


def read(path: Path = DECLARATION) -> Declaration:
    """Read the declaration file of the repository."""
    return parse(path.read_text(encoding="utf-8"))


def _family(name: str, entry: dict[str, Any]) -> Family:
    _only(entry, _FAMILY, f"family {name}")
    if "target" not in entry:
        message = f"family {name} has no target"
        raise DeclarationError(message)
    always = bool(entry.get("always", False))
    paths = tuple(entry.get("paths", ()))
    if always == bool(paths):
        message = f"family {name} needs either paths or always = true, not both"
        raise DeclarationError(message)
    return Family(name=name, target=entry["target"], paths=paths, always=always)


def _generated(number: int, entry: dict[str, Any]) -> Generated:
    where = f"generated entry {number}"
    _only(entry, _GENERATED, where)
    if not entry.get("paths") or not entry.get("by"):
        message = f"{where} needs paths and the command that writes them (by)"
        raise DeclarationError(message)
    return Generated(paths=tuple(entry["paths"]), by=entry["by"])


def _only(entry: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = entry.keys() - allowed
    if unknown:
        message = f"{where}: unknown {sorted(unknown)}"
        raise DeclarationError(message)
