# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Hold each calculation WF-ARC-0010 names to one implementation, in its module of the core.

Usage: ``python -m wftools.implementations``.

WF-ARC-0010 asks that the repository hold one implementation of the state machine and of the
calculations of planning, of estimate and of indicators, which the API and the worker share. The
versioned table, ``tools/implementations.toml``, names for each file of the core that carries one
of these calculations the names it is called by: its functions that compute, and the constants that
fix its result. The module of the core that owns a name is the first directory under ``core/`` of
its file. The check reads the back that is delivered, ``backend/src/waterfall``, by the syntax tree
of its files, without importing them.

It holds the files that use the calculations without owning any: the API, the worker, and the other
entry points and the platform — every file outside ``core/`` and ``migrations/`` —, and the
portfolio, ``core/portfolio``, which sums what the other modules compute. It fails, naming the file
and the line:

- on a name of the table that one of them defines: a function of that name, at any depth, method
  included, or a name assigned at the level of the module. A copy is a second implementation,
  whatever it computes;
- on a name of the table that one of them imports (``from … import name``, an alias included, a
  relative import resolved) from elsewhere than the module of the core that owns it;
- on a file of the portfolio that the table says applies a formula of EP-10 to sums, and that does
  not import that formula or does not call it (WF-PTF-0020);
- on a name of the table its file no longer defines, and on a declaration of the table that no
  longer holds, so that the table does not age unnoticed.

What « defines none » observes is thus a definition by name, and what « imports it from there »
observes, the module an import names. A calculation written again under another name escapes it,
and is the review's to find. The names too common to designate a calculation, and the classes,
which the models generated from the contract repeat without computing anything, are left out of the
table, which says why. The other modules of the core are out of the check: several of them give a
name of the table to another thing of their own (``STATES`` of the risks, ``state_of`` of the
planning), and the migrations keep the values of their time. Two declarations of the table keep a
finding said without failing: a homonym, another calculation of a module of the core under a name
of the table, which may be imported from that module (the zone of a cell of the risk matrix,
``zone_of``); a known duplicate, a definition the check would refuse, said at each run with its
reason until it is gone, re-exports of it included. The generators of the fake back, under
``tools/``, are not delivered: they stay an independent calculation, out of the check.
"""

import ast
import sys
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

TABLE = REPOSITORY / "tools" / "implementations.toml"
"""The versioned table: for each calculation, the files of the core and the names of each."""
PACKAGE = REPOSITORY / "backend" / "src" / "waterfall"
"""The back that is delivered, whose files the check reads."""
ROOT = "waterfall"
"""The name of the package of the back."""
CALCULATIONS = frozenset({"state machine", "planning", "estimate", "indicators"})
"""The calculations WF-ARC-0010 names."""
PORTFOLIO = "core/portfolio/"
"""The one module of the core the check holds: it sums what the others compute."""
UNHELD = ("core/", "migrations/")
"""What the check leaves alone, the portfolio apart: the modules of the core, and the migrations."""


class TableError(ValueError):
    """The table is malformed: the check cannot judge the back by it."""


@dataclass(frozen=True, slots=True)
class Implementation:
    """A file of the core that carries a calculation, and the names it is called by."""

    calculation: str
    file: str
    names: tuple[str, ...]

    @property
    def owner(self) -> str:
        """Return the module of the core that owns the names: ``waterfall.core.indicators``."""
        return f"{ROOT}.core.{self.file.split('/')[1]}"


@dataclass(frozen=True, slots=True)
class Application:
    """A file of the portfolio that applies formulas of the core to sums."""

    file: str
    applies: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Declaration:
    """A name of the table in a place the check would refuse, and the reason it is kept.

    A homonym names a module of the core (``waterfall.core.risk_settings``), a duplicate a file of
    the back (``core/portfolio/aggregation/periods.py``).
    """

    name: str
    place: str
    reason: str


@dataclass(frozen=True, slots=True)
class Table:
    """The table read: the implementations, the applications, the homonyms and the duplicates."""

    implementations: tuple[Implementation, ...]
    applications: tuple[Application, ...]
    homonyms: tuple[Declaration, ...]
    duplicates: tuple[Declaration, ...]

    def owners(self) -> dict[str, Implementation]:
        """Return the implementation of each name of the table."""
        return {name: each for each in self.implementations for name in each.names}


def _strings(entry: dict[str, object], key: str) -> tuple[str, ...]:
    value = entry.get(key)
    if not isinstance(value, list) or not value:
        message = f"{key} must be a list of names, not {value!r}"
        raise TableError(message)
    names = cast("list[object]", value)
    if not all(isinstance(each, str) and each for each in names):
        message = f"{key} must hold names: {names!r}"
        raise TableError(message)
    return tuple(cast("list[str]", names))


def _string(entry: dict[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        message = f"{key} must be a text, not {value!r}"
        raise TableError(message)
    return value


def _entries(data: dict[str, object], key: str) -> list[dict[str, object]]:
    value = data.get(key, [])
    if not isinstance(value, list):
        message = f"[[{key}]] must be an array of tables"
        raise TableError(message)
    return cast("list[dict[str, object]]", value)


def _implementation(entry: dict[str, object], seen: dict[str, str]) -> Implementation:
    calculation, file = _string(entry, "calculation"), _string(entry, "file")
    if calculation not in CALCULATIONS:
        message = f"{file}: {calculation!r} is not a calculation WF-ARC-0010 names"
        raise TableError(message)
    if not file.startswith("core/") or file.startswith(PORTFOLIO) or "/" not in file[5:]:
        message = f"{file} is not a file of a module of the core that computes"
        raise TableError(message)
    names = _strings(entry, "names")
    for name in names:
        if name in seen:
            message = f"{name} has two owners: {seen[name]} and {file}"
            raise TableError(message)
        seen[name] = file
    return Implementation(calculation, file, names)


def parse(text: str) -> Table:
    """Read the table: no calculation WF-ARC-0010 does not name, no name with two owners."""
    data = tomllib.loads(text)
    seen: dict[str, str] = {}
    implementations = [_implementation(each, seen) for each in _entries(data, "implementation")]
    applications = [
        Application(_string(each, "file"), _strings(each, "applies"))
        for each in _entries(data, "application")
    ]
    homonyms = [
        Declaration(_string(each, "name"), _string(each, "module"), _string(each, "reason"))
        for each in _entries(data, "homonym")
    ]
    duplicates = [
        Declaration(_string(each, "name"), _string(each, "file"), _string(each, "reason"))
        for each in _entries(data, "duplicate")
    ]
    for each in (*homonyms, *duplicates):
        if each.name not in seen:
            message = f"{each.place}: {each.name} is not a name of the table"
            raise TableError(message)
    return Table(tuple(implementations), tuple(applications), tuple(homonyms), tuple(duplicates))


def held(file: str) -> bool:
    """Tell whether the check holds a file of the back: the portfolio, or outside the core."""
    return file.startswith(PORTFOLIO) or not file.startswith(UNHELD)


def module_of(file: str) -> str:
    """Return the dotted name of a file of the back: ``core/x/__init__.py`` is ``waterfall.core.x``.

    ``api/app.py`` is ``waterfall.api.app``.
    """
    parts = [ROOT, *file.removesuffix(".py").split("/")]
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def defined(tree: ast.Module) -> dict[str, int]:
    """Return the names a module defines, with the line of the first of each.

    Functions at any depth, methods included; names assigned at the level of the module.
    """
    found: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            found.setdefault(node.name, node.lineno)
    for statement in tree.body:
        targets: list[ast.expr] = []
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign | ast.AugAssign):
            targets = [statement.target]
        for target in targets:
            for node in ast.walk(target):
                if isinstance(node, ast.Name):
                    found.setdefault(node.id, statement.lineno)
    return found


def imports(tree: ast.Module, file: str) -> Iterator[tuple[str, str, int]]:
    """Yield each name a module imports by ``from … import``, the module it names, and the line.

    A relative import is resolved against the package of the file.
    """
    package = module_of(file).split(".")
    if not file.endswith("__init__.py"):
        package = package[:-1]
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        source = node.module or ""
        if node.level:
            base = package[: len(package) - node.level + 1]
            source = ".".join([*base, *([source] if source else [])])
        for alias in node.names:
            yield alias.name, source, node.lineno


def called(tree: ast.Module) -> set[str]:
    """Return the names a module calls directly: ``cost_index(…)``."""
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def within(module: str, package: str) -> bool:
    """Tell whether a module is a package or one of its modules, at any depth."""
    return module == package or module.startswith(f"{package}.")


class _Judge:
    """The judgement of the back against the table, its findings and its notes."""

    def __init__(self, table: Table, trees: dict[str, ast.Module]) -> None:
        self.table = table
        self.trees = trees
        self.owners = table.owners()
        self.defined = {file: defined(tree) for file, tree in trees.items()}
        self.duplicates = {(each.name, each.place): each for each in table.duplicates}
        self.homonyms = {(each.name, each.place) for each in table.homonyms}
        self.duplicate_modules = {(each.name, module_of(each.place)) for each in table.duplicates}
        self.findings: list[str] = []
        self.notes: list[str] = []

    def implementations(self) -> None:
        for each in self.table.implementations:
            names = self.defined.get(each.file)
            if names is None:
                self.findings.append(
                    f"{each.file}: no such file of the back, which the table names"
                )
                continue
            self.findings += [
                f"{each.file}: no longer defines {name}, which the table gives it"
                f" ({each.calculation})"
                for name in each.names
                if name not in names
            ]

    def definitions(self, file: str) -> None:
        for name, line in sorted(self.defined[file].items()):
            owner = self.owners.get(name)
            if owner is None:
                continue
            duplicate = self.duplicates.get((name, file))
            if duplicate is not None:
                self.notes.append(
                    f"{file}:{line}: defines {name}, a known duplicate: {duplicate.reason}"
                )
                continue
            self.findings.append(
                f"{file}:{line}: defines {name}, a second implementation of the {owner.calculation}"
                f" of {owner.file}: import it from {owner.owner}"
            )

    def imported(self, file: str) -> None:
        for name, source, line in imports(self.trees[file], file):
            owner = self.owners.get(name)
            if owner is None or within(source, owner.owner):
                continue
            if (name, source) in self.duplicate_modules or any(
                within(source, module) for each, module in self.homonyms if each == name
            ):
                continue
            self.findings.append(
                f"{file}:{line}: imports {name} from {source}, not from {owner.owner},"
                " the module of the core that owns it"
            )

    def applications(self) -> None:
        for each in self.table.applications:
            tree = self.trees.get(each.file)
            if tree is None:
                self.findings.append(
                    f"{each.file}: no such file of the back, which the table names"
                )
                continue
            imported = {
                name
                for name, source, _ in imports(tree, each.file)
                if name in self.owners and within(source, self.owners[name].owner)
            }
            calls = called(tree)
            self.findings += [
                f"{each.file}: does not apply {name} of {self.owners[name].file}: it must import"
                " it from the module that owns it and call it, never write it again"
                for name in each.applies
                if name not in self.owners or name not in imported or name not in calls
            ]

    def declarations(self) -> None:
        for name, file in self.duplicates:
            if not held(file):
                self.findings.append(f"{file}: the duplicate {name} is in a file the check leaves")
            elif name not in self.defined.get(file, {}):
                self.findings.append(
                    f"{file}: no longer defines {name}: remove its [[duplicate]] entry"
                )
        for name, module in sorted(self.homonyms):
            if not any(
                name in names
                for file, names in self.defined.items()
                if within(module_of(file), module)
            ):
                self.findings.append(
                    f"{module}: defines no {name} any more: remove its [[homonym]] entry"
                )


def check(table: Table, sources: dict[str, str]) -> tuple[list[str], list[str]]:
    """Judge the sources of the back, by their path under the package, against the table.

    Return the findings, which fail the check, and the known duplicates still there, which it says.
    """
    trees = {file: ast.parse(text, filename=file) for file, text in sources.items()}
    judge = _Judge(table, trees)
    judge.implementations()
    for file in sorted(trees):
        if held(file):
            judge.definitions(file)
            judge.imported(file)
    judge.applications()
    judge.declarations()
    return judge.findings, judge.notes


def read_sources(package: Path) -> dict[str, str]:
    """Return the text of each Python file of the back, by its path under the package."""
    return {
        path.relative_to(package).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(package.rglob("*.py"))
    }


def main() -> int:
    """Check the back against the table, and name each second implementation."""
    try:
        table = parse(TABLE.read_text(encoding="utf-8"))
    except (TableError, tomllib.TOMLDecodeError) as error:
        print(f"{TABLE.relative_to(REPOSITORY)}: {error}", file=sys.stderr)
        return 1
    sources = read_sources(PACKAGE)
    findings, notes = check(table, sources)
    for note in notes:
        print(note)
    for finding in findings:
        print(finding, file=sys.stderr)
    names = sum(len(each.names) for each in table.implementations)
    files = sum(1 for file in sources if held(file))
    print(
        f"{names} name(s) of {len(table.implementations)} file(s) of the core held against"
        f" {files} file(s) of the back: {len(findings)} finding(s), {len(notes)} known duplicate(s)"
    )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
