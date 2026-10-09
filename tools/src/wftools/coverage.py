# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Report which requirements the tests cover, by the identifier each test cites (WF-QUA-0010).

Usage: ``python -m wftools.coverage [--release]``.

A Python test cites a requirement with the marker ``@pytest.mark.requirement("WF-…-A")``, on
the test, its class, or the module (``pytestmark``); a TypeScript test — Vitest or
Playwright — cites it between brackets in its title: ``it("… [WF-QUA-0050-A]", …)``. The
citations are read from the test files themselves, without running them: removing a test
makes its requirement uncovered at once, and a failing test is the tests' own business.

Each citation belongs to the family of its file — front, end-to-end, back or tools, as
``tools/paths.toml`` declares them — and the report says, for every requirement, which
families cite it. The front's tests cite requirements that other epics close, by the Vérif
sentence they try (#333); such a requirement is not proven until the family that closes it
cites it too. The roadmap says which epic closes each requirement, and the front matter of
each epic its families: one cited by the front's families alone, and closed by an epic that
is not the front's alone, is listed apart and does not count as covered.

The report lists every F0 requirement of the document with the tests that cover it, and is
added to the summary of the chain's job when it runs there. A citation of an unknown
identifier, or of a revision the document has moved past, always fails. With
``--release``, an F0 requirement no test covers — or the front alone covers — fails too,
and is named: a release is refused while one is uncovered. A requirement whose Vérif opens
with « Vérifiée en recette » awaits an acceptance report; the report says so, until the
form of such a report is defined.
"""

import argparse
import ast
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

from wftools import REPOSITORY, paths, projection, roadmap

ACCEPTANCE = "Vérifiée en recette"
"""What opens the Vérif field of a requirement an acceptance report covers (WF-QUA-0010)."""

FRONT_FAMILIES = frozenset({"front", "end-to-end"})
"""The families of ``tools/paths.toml`` whose tests run the front, against a fake back."""

_TITLE_CITATION = re.compile(r"\[(WF-[A-Z]+-\d{4}-[A-Z])\]")
_TYPESCRIPT = frozenset({".ts", ".tsx"})
_Test = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Citation:
    """A test that cites a requirement, and the family of tests it belongs to."""

    requirement: str
    test: str
    family: str


def python_citations(path: str, source: str, kind: str) -> list[Citation]:
    """Return the requirements the tests of a Python file of this family cite, test by test."""
    tree = ast.parse(source)
    module = _marked(_module_marks(tree))
    found: list[Citation] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            inherited = module + _marked(node.decorator_list)
            for member in node.body:
                if _is_test(member):
                    test = f"{path}::{node.name}::{member.name}"
                    cited = inherited + _marked(member.decorator_list)
                    found.extend(Citation(requirement, test, kind) for requirement in cited)
        elif _is_test(node):
            test = f"{path}::{node.name}"
            cited = module + _marked(node.decorator_list)
            found.extend(Citation(requirement, test, kind) for requirement in cited)
    return found


def typescript_citations(path: str, source: str, kind: str) -> list[Citation]:
    """Return the requirements the titles of a TypeScript test file of this family cite."""
    return [
        Citation(match.group(1), f"{path}:{source.count(chr(10), 0, match.start()) + 1}", kind)
        for match in _TITLE_CITATION.finditer(source)
    ]


def _is_test(node: ast.stmt) -> TypeGuard[_Test]:
    return isinstance(node, _Test) and node.name.startswith("test")


def _module_marks(tree: ast.Module) -> list[ast.expr]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "pytestmark" for target in node.targets
        ):
            value = node.value
            return list(value.elts) if isinstance(value, ast.List | ast.Tuple) else [value]
    return []


def _marked(expressions: list[ast.expr]) -> list[str]:
    """Return the identifiers of the ``requirement`` marks among decorators or marks."""
    return [
        argument.value
        for expression in expressions
        if isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "requirement"
        for argument in expression.args
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
    ]


def citations(declaration: paths.Declaration, repository: Path = REPOSITORY) -> list[Citation]:
    """Return every citation of the test files of the repository, committed or not."""
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
    )
    output: str = listed.stdout or ""
    found: list[Citation] = []
    for path in sorted(set(output.splitlines())):
        file = repository / path
        kind = declaration.test_family(path)
        if kind is None or not file.is_file():
            continue
        suffix = Path(path).suffix
        if suffix == ".py":
            found.extend(python_citations(path, file.read_text(encoding="utf-8"), kind))
        elif suffix in _TYPESCRIPT:
            found.extend(typescript_citations(path, file.read_text(encoding="utf-8"), kind))
    return found


def closed_by_the_front(epics: tuple[roadmap.Epic, ...]) -> frozenset[str]:
    """Return the requirements the front's epics close, from the tables of the roadmap.

    An epic of the front declares the front as its only family: its whole work is the
    front, and a requirement it closes is proven by the front's tests. Every other epic
    closes its requirements with the back or the platform too, and the front's citations
    of them only say that a screen shows what the back will compute.
    """
    return frozenset(
        row.requirement
        for epic in epics
        if epic.families == (roadmap.FRONT,)
        for row in epic.rows
        if row.closes
    )


@dataclass(frozen=True, slots=True)
class Report:
    """What the citations cover, and what is wrong with them."""

    order: tuple[str, ...]
    covered: dict[str, list[Citation]]
    uncovered: list[str]
    front_only: list[str]
    acceptance: list[str]
    unknown: list[Citation]
    outdated: list[tuple[Citation, str]]

    @property
    def missing(self) -> list[str]:
        """The F0 requirements a release refuses: uncovered, or covered by the front alone."""
        return self.uncovered + self.front_only

    def families(self, identifier: str) -> list[str]:
        """Return the families whose tests cite this requirement, in declaration order."""
        cited = {citation.family for citation in self.covered.get(identifier, [])}
        return [name for name in self.order if name in cited]

    def markdown(self, requirements: list[projection.Requirement]) -> str:
        """Return the report: every product requirement, only the F0 ones counting."""
        mandatory = sum(requirement.is_mandatory for requirement in requirements)
        lines = [
            "## Couverture des exigences par les tests",
            "",
            (
                f"{mandatory - len(self.missing)} exigences F0 couvertes sur {mandatory} ; "
                f"{len(self.front_only)} couvertes par le front seul, closes par un autre "
                "EPIC, ne comptent pas ; "
                f"les {len(requirements) - mandatory} exigences F1 et F2 figurent sans "
                "compter dans l'échec (WF-QUA-0010)."
            ),
            "",
            "| Exigence | Flex | Titre | Familles | Tests |",
            "|---|---|---|---|---|",
        ]
        lines.extend(
            f"| `{requirement.identifier}` | {requirement.flexibility} "
            f"| {requirement.title} | {', '.join(self.families(requirement.identifier))} "
            f"| {self._cell(requirement)} |"
            for requirement in requirements
        )
        return "\n".join(lines) + "\n"

    def _cell(self, requirement: projection.Requirement) -> str:
        identifier = requirement.identifier
        tests = self.covered.get(identifier, [])
        if identifier in self.front_only:
            return "**front seul** : " + "<br>".join(f"`{c.test}`" for c in tests)
        if tests:
            return "<br>".join(f"`{citation.test}`" for citation in tests)
        if identifier in self.acceptance:
            return "**non couverte** — vérifiée en recette, procès-verbal attendu"
        return "**non couverte**" if requirement.is_mandatory else "non couverte"


def report(
    requirements: tuple[projection.Requirement, ...],
    found: list[Citation],
    declaration: paths.Declaration,
    front_closed: frozenset[str] = frozenset(),
) -> Report:
    """Confront the citations with the requirements of the document.

    The declaration gives the families of tests and their order; ``front_closed`` names the
    requirements the front's epics close: for them, the front's families count; for the
    others, a citation by the front alone does not.
    """
    by_identifier = {requirement.identifier: requirement for requirement in requirements}
    by_key = {requirement.key: requirement for requirement in requirements}
    covered: dict[str, list[Citation]] = defaultdict(list)
    unknown: list[Citation] = []
    outdated: list[tuple[Citation, str]] = []
    for citation in found:
        if citation.requirement in by_identifier:
            covered[citation.requirement].append(citation)
        elif (current := by_key.get(citation.requirement[:-2])) is not None:
            outdated.append((citation, current.identifier))
        else:
            unknown.append(citation)
    mandatory = [requirement for requirement in requirements if requirement.is_mandatory]
    uncovered = [r.identifier for r in mandatory if r.identifier not in covered]
    front_only = [
        requirement.identifier
        for requirement in mandatory
        if requirement.identifier in covered
        and requirement.identifier not in front_closed
        and {c.family for c in covered[requirement.identifier]} <= FRONT_FAMILIES
    ]
    acceptance = [
        requirement.identifier
        for requirement in mandatory
        if projection.normalize(requirement.verification).startswith(ACCEPTANCE)
    ]
    return Report(
        declaration.test_families,
        dict(covered),
        uncovered,
        front_only,
        acceptance,
        unknown,
        outdated,
    )


def _print(result: Report, mandatory: list[projection.Requirement]) -> None:
    """Print the families that cite each covered F0 requirement, then the count."""
    for requirement in mandatory:
        families = result.families(requirement.identifier)
        if families:
            note = " (front alone)" if requirement.identifier in result.front_only else ""
            print(f"{requirement.identifier}: {', '.join(families)}{note}")
    print(
        f"{len(mandatory) - len(result.missing)} of {len(mandatory)} F0 requirements covered; "
        f"{len(result.front_only)} cited by the front alone and closed by another epic, "
        "not counted"
    )


def _reason(result: Report, identifier: str) -> str:
    if identifier in result.front_only:
        return " (front alone)"
    if identifier in result.acceptance:
        return " (verified at acceptance: no report yet)"
    return ""


def main(arguments: list[str]) -> int:
    """Print the coverage, add it to the job summary, and fail as the rules say."""
    parser = argparse.ArgumentParser(
        prog="wftools.coverage", description="Report the coverage of requirements by tests."
    )
    parser.add_argument("--release", action="store_true", help="fail on an uncovered F0")
    options = parser.parse_args(arguments)
    requirements = projection.read()
    declaration = paths.read()
    front_closed = closed_by_the_front(roadmap.read())
    result = report(requirements, citations(declaration), declaration, front_closed)
    mandatory = [requirement for requirement in requirements if requirement.is_mandatory]
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(result.markdown([r for r in requirements if not r.is_example]))
    for citation in result.unknown:
        print(f"{citation.test}: cites {citation.requirement}, unknown", file=sys.stderr)
    for citation, current in result.outdated:
        print(
            f"{citation.test}: cites {citation.requirement}, now {current}",
            file=sys.stderr,
        )
    _print(result, mandatory)
    failed = bool(result.unknown or result.outdated)
    if options.release and result.missing:
        for identifier in result.missing:
            print(f"not covered: {identifier}{_reason(result, identifier)}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
