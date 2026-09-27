# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Report which requirements the tests cover, by the identifier each test cites (WF-QUA-0010).

Usage: ``python -m wftools.coverage [--release]``.

A Python test cites a requirement with the marker ``@pytest.mark.requirement("WF-…-A")``, on
the test, its class, or the module (``pytestmark``); a TypeScript test — Vitest or
Playwright — cites it between brackets in its title: ``it("… [WF-QUA-0050-A]", …)``. The
citations are read from the test files themselves, without running them: removing a test
makes its requirement uncovered at once, and a failing test is the tests' own business.

The report lists every F0 requirement of the document with the tests that cover it, and is
added to the summary of the chain's job when it runs there. A citation of an unknown
identifier, or of a revision the document has moved past, always fails. With
``--release``, an F0 requirement no test covers fails too, and is named: a release is
refused while one is uncovered.
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

from wftools import REPOSITORY, paths, projection

_TITLE_CITATION = re.compile(r"\[(WF-[A-Z]+-\d{4}-[A-Z])\]")
_TYPESCRIPT = frozenset({".ts", ".tsx"})
_Test = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Citation:
    """A test that cites a requirement."""

    requirement: str
    test: str


def python_citations(path: str, source: str) -> list[Citation]:
    """Return the requirements the tests of a Python file cite, test by test."""
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
                    found.extend(Citation(requirement, test) for requirement in cited)
        elif _is_test(node):
            test = f"{path}::{node.name}"
            cited = module + _marked(node.decorator_list)
            found.extend(Citation(requirement, test) for requirement in cited)
    return found


def typescript_citations(path: str, source: str) -> list[Citation]:
    """Return the requirements the titles of a TypeScript test file cite."""
    return [
        Citation(match.group(1), f"{path}:{source.count(chr(10), 0, match.start()) + 1}")
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


def citations(declaration: paths.Declaration) -> list[Citation]:
    """Return every citation of the test files of the repository, committed or not."""
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    output: str = listed.stdout or ""
    found: list[Citation] = []
    for path in sorted(set(output.splitlines())):
        file = REPOSITORY / path
        if not declaration.is_test(path) or not file.is_file():
            continue
        suffix = Path(path).suffix
        if suffix == ".py":
            found.extend(python_citations(path, file.read_text(encoding="utf-8")))
        elif suffix in _TYPESCRIPT:
            found.extend(typescript_citations(path, file.read_text(encoding="utf-8")))
    return found


@dataclass(frozen=True, slots=True)
class Report:
    """What the citations cover, and what is wrong with them."""

    covered: dict[str, list[str]]
    uncovered: list[str]
    unknown: list[Citation]
    outdated: list[tuple[Citation, str]]

    def markdown(self, mandatory: list[projection.Requirement]) -> str:
        """Return the report, one line per F0 requirement."""
        lines = [
            "## Couverture des exigences par les tests",
            "",
            f"{len(mandatory) - len(self.uncovered)} exigences F0 couvertes sur {len(mandatory)}.",
            "",
            "| Exigence | Titre | Tests |",
            "|---|---|---|",
        ]
        for requirement in mandatory:
            tests = self.covered.get(requirement.identifier, [])
            cell = "<br>".join(f"`{test}`" for test in tests) if tests else "**non couverte**"
            lines.append(f"| `{requirement.identifier}` | {requirement.title} | {cell} |")
        return "\n".join(lines) + "\n"


def report(requirements: tuple[projection.Requirement, ...], found: list[Citation]) -> Report:
    """Confront the citations with the requirements of the document."""
    by_identifier = {requirement.identifier: requirement for requirement in requirements}
    by_key = {requirement.key: requirement for requirement in requirements}
    covered: dict[str, list[str]] = defaultdict(list)
    unknown: list[Citation] = []
    outdated: list[tuple[Citation, str]] = []
    for citation in found:
        if citation.requirement in by_identifier:
            covered[citation.requirement].append(citation.test)
        elif (current := by_key.get(citation.requirement[:-2])) is not None:
            outdated.append((citation, current.identifier))
        else:
            unknown.append(citation)
    uncovered = [
        requirement.identifier
        for requirement in requirements
        if requirement.is_mandatory and requirement.identifier not in covered
    ]
    return Report(dict(covered), uncovered, unknown, outdated)


def main(arguments: list[str]) -> int:
    """Print the coverage, add it to the job summary, and fail as the rules say."""
    parser = argparse.ArgumentParser(
        prog="wftools.coverage", description="Report the coverage of requirements by tests."
    )
    parser.add_argument("--release", action="store_true", help="fail on an uncovered F0")
    options = parser.parse_args(arguments)
    requirements = projection.read()
    result = report(requirements, citations(paths.read()))
    mandatory = [requirement for requirement in requirements if requirement.is_mandatory]
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(result.markdown(mandatory))
    for citation in result.unknown:
        print(f"{citation.test}: cites {citation.requirement}, unknown", file=sys.stderr)
    for citation, current in result.outdated:
        print(
            f"{citation.test}: cites {citation.requirement}, now {current}",
            file=sys.stderr,
        )
    print(f"{len(mandatory) - len(result.uncovered)} of {len(mandatory)} F0 requirements covered")
    failed = bool(result.unknown or result.outdated)
    if options.release and result.uncovered:
        for identifier in result.uncovered:
            print(f"not covered: {identifier}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
