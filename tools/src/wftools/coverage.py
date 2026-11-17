# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Report which requirements the tests cover, by the identifier each test cites (WF-QUA-0010).

Usage: ``python -m wftools.coverage [--release]``.

A Python test cites a requirement with the marker ``@pytest.mark.requirement("WF-…-A")``, on
the test, its class, or the module (``pytestmark``); a TypeScript test — Vitest or
Playwright — cites it between brackets in its title: ``it("… [WF-QUA-0050-A]", …)``, or in the
title of a ``describe`` that holds it. The citations are read from the test files themselves,
without running them: removing a test makes its requirement uncovered at once, and a failing test
is the tests' own business. A citation in a comment is no citation.

A test that carries a criterion of a story, not of a requirement, cites the story: ``[US-2160]`` in
the title of a TypeScript test, ``@pytest.mark.story("US-2160")`` in Python (US-2440). The report
lists these apart, under « Critères propres aux US », out of the count of the requirements, and
fails on a story no file of ``docs/roadmap`` holds, as on an unknown requirement.

A test that is not run proves nothing, and is told by what it declares (US-2440): a Python test
that can skip bears the mark ``@pytest.mark.unexecuted("<reason>")`` — on the test, its class, the
module, or a ``pytest.param`` of its ``parametrize`` —, which ``wftools.unexecuted`` makes
compulsory; any call of that mark counts, whatever its argument, as the plugin accepts any string. A
TypeScript test is declared ``.skip``, ``.fixme`` or ``.todo``, or sits in a ``describe.skip`` or
``describe.fixme``. Its citations are listed under their requirement, « non exécuté », and cover
nothing. A ``test.skip`` or ``test.fixme`` called in its body without a title leaves it run if its
first argument is ``inService`` or ``!inService``, and stops it otherwise (``test.skip(true, …)``,
any other condition). A skip by ``it.skipIf`` or ``it.runIf`` is not seen: the test counts as run. A
form of declaration that ``wftools.titles`` does not know fails the report, naming the file and the
line.

Each citation belongs to the family of its file — end-to-end against the service, end-to-end,
front, back or tools, as ``tools/paths.toml`` declares them — and the report says, for every
requirement, which families cite it. The front's tests cite requirements that other epics close,
by the Vérif sentence they try (#333); such a requirement is not proven until the family that
closes it cites it too. A path played against the real service traverses the back: it proves
what the back closes, as the back's own tests do (US-0340). The roadmap says which epic closes
each requirement, and the front matter of each epic its families: one cited by the front's
families alone, and closed by an epic that is not the front's alone, is listed apart and does
not count as covered.

The report lists every F0 requirement of the document with the tests that cover it, and is
added to the summary of the chain's job when it runs there. A citation of an unknown
identifier, or of a revision the document has moved past, always fails. With
``--release``, an F0 requirement no test covers — the front alone covers, or tests not run
alone cite — fails too, and is named: a release is refused while one is uncovered. A
requirement whose Vérif opens with « Vérifiée en recette » awaits an acceptance report; the
report says so, until the form of such a report is defined.
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

from wftools import REPOSITORY, paths, projection, roadmap, titles
from wftools.marks import MARK, STORY

ACCEPTANCE = "Vérifiée en recette"
"""What opens the Vérif field of a requirement an acceptance report covers (WF-QUA-0010)."""

FRONT_FAMILIES = frozenset({"front", "end-to-end"})
"""The families of ``tools/paths.toml`` whose tests run the front, against a fake back.

``end-to-end-service`` is not one of them: its paths run against the real service.
"""

_TITLE_CITATION = re.compile(r"\[(WF-[A-Z]+-\d{4}-[A-Z]|US-\d{4})\]")
_STORY_IDENTIFIER = re.compile(r"US-\d{4}")
_TYPESCRIPT = frozenset({".ts", ".tsx"})
_Test = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True, slots=True)
class Citation:
    """A test that cites a requirement, the family of tests it belongs to, and whether it runs.

    A test that does not run — skipped, or declared so — covers nothing (US-2440). A citation of
    a story (``US-nnnn``) is no requirement: it carries a criterion the story owns.
    """

    requirement: str
    test: str
    family: str
    executed: bool = True
    misplaced: bool = False

    @property
    def is_story(self) -> bool:
        """Tell a citation of a story (``US-nnnn``) from one of a requirement."""
        return not self.misplaced and _STORY_IDENTIFIER.fullmatch(self.requirement) is not None


def python_citations(path: str, source: str, kind: str) -> list[Citation]:
    """Return the requirements the tests of a Python file of this family cite, test by test."""
    tree = ast.parse(source)
    module = _marks_of(tree.body)
    names = _assigned(tree)
    found: list[Citation] = []

    def cite(test: str, marks: list[ast.expr]) -> None:
        executed = not _unexecuted(marks, names)
        # The mark, not the shape of the string, says what is cited: a story under `requirement`,
        # or a requirement under `story`, is no coverage and fails the report as unknown.
        for name in ("requirement", STORY):
            for identifier in _marked(marks, name):
                is_story_shaped = _STORY_IDENTIFIER.fullmatch(identifier) is not None
                misplaced = is_story_shaped != (name == STORY)
                found.append(Citation(identifier, test, kind, executed, misplaced))

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            held = module + node.decorator_list + _marks_of(node.body)
            for member in node.body:
                if _is_test(member):
                    marks = held + member.decorator_list
                    cite(f"{path}::{node.name}::{member.name}", marks)
        elif _is_test(node):
            cite(f"{path}::{node.name}", module + node.decorator_list)
    return found


def typescript_citations(path: str, source: str, kind: str) -> list[Citation]:
    """Return the requirements the titles of a TypeScript test file of this family cite.

    Each citation is placed at its line; it runs as the test, or the group, whose title holds it.
    """
    found: list[Citation] = []
    for title, runs in titles.declarations(source, jsx=path.endswith(".tsx"), path=path):
        for string in title.strings:
            for match in _TITLE_CITATION.finditer(string.text):
                line = source.count("\n", 0, string.start + match.start()) + 1
                found.append(Citation(match.group(1), f"{path}:{line}", kind, runs))
    return found


def _is_test(node: ast.stmt) -> TypeGuard[_Test]:
    return isinstance(node, _Test) and node.name.startswith("test")


def _marks_of(body: list[ast.stmt]) -> list[ast.expr]:
    """Return the marks a ``pytestmark`` in this module or class body gives, alone or in a list."""
    for node in body:
        targets, value = _assignment(node)
        if value is not None and any(
            isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets
        ):
            return list(value.elts) if isinstance(value, ast.List | ast.Tuple) else [value]
    return []


def _assignment(node: ast.stmt) -> tuple[list[ast.expr], ast.expr | None]:
    """Return the targets and the value of an assignment, annotated or not."""
    if isinstance(node, ast.Assign):
        return node.targets, node.value
    if isinstance(node, ast.AnnAssign):
        return [node.target], node.value
    return [], None


def _assigned(tree: ast.Module) -> dict[str, ast.expr]:
    """Return the value each name assigned at the top of the module holds."""
    return {
        target.id: value
        for node in tree.body
        for targets, value in [_assignment(node)]
        if value is not None
        for target in targets
        if isinstance(target, ast.Name)
    }


def _unexecuted(expressions: list[ast.expr], names: dict[str, ast.expr]) -> bool:
    """Tell whether any call of the mark ``unexecuted`` is in these decorators or marks.

    The mark counts whatever its argument is: ``@pytest.mark.unexecuted(REASON)`` skips as well as
    one with a string, the plugin taking any string at run time. It is looked for in the whole
    expression, which finds ``pytest.param(…, marks=pytest.mark.unexecuted(…))`` in a
    ``parametrize`` (a test with a case that may skip may not run), and in the module-level names
    the expression reads, a list of cases built apart. A name from another module is not seen.
    """
    seen: set[str] = set()
    pending = list(expressions)
    while pending:
        for node in ast.walk(pending.pop()):
            if isinstance(node, ast.Call) and _named(node.func, MARK):
                return True
            if isinstance(node, ast.Name) and node.id in names and node.id not in seen:
                seen.add(node.id)
                pending.append(names[node.id])
    return False


def _named(function: ast.expr, name: str) -> bool:
    return isinstance(function, ast.Attribute) and function.attr == name


def _marked(expressions: list[ast.expr], mark: str) -> list[str]:
    """Return the identifiers the marks of this name among decorators or marks give."""
    return [
        argument.value
        for expression in expressions
        if isinstance(expression, ast.Call) and _named(expression.func, mark)
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
    """What the citations cover, and what is wrong with them.

    ``covered`` holds the citations of the tests that run, ``unexecuted`` those of the tests that
    do not, which cover nothing: a requirement only they cite is uncovered. ``stories`` holds the
    citations of a story, apart from the requirements and out of their count, and
    ``unknown_stories`` those of a story no file of the roadmap holds.
    """

    order: tuple[str, ...]
    covered: dict[str, list[Citation]]
    uncovered: list[str]
    front_only: list[str]
    acceptance: list[str]
    unknown: list[Citation]
    outdated: list[tuple[Citation, str]]
    unexecuted: dict[str, list[Citation]]
    stories: dict[str, list[Citation]]
    unknown_stories: list[Citation]

    @property
    def missing(self) -> list[str]:
        """The F0 requirements a release refuses: uncovered, or covered by the front alone.

        A requirement only tests not run cite is uncovered.
        """
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
        if self.stories:
            lines += ["", "## Critères propres aux US", "", "| US | Tests |", "|---|---|"]
            lines.extend(
                f"| `{story}` | "
                + "<br>".join(
                    f"`{c.test}`" + ("" if c.executed else " (non exécuté)") for c in cited
                )
                + " |"
                for story, cited in sorted(self.stories.items())
            )
        return "\n".join(lines) + "\n"

    def _cell(self, requirement: projection.Requirement) -> str:
        identifier = requirement.identifier
        tests = self.covered.get(identifier, [])
        not_run = "".join(
            f"<br>`{citation.test}` (non exécuté)"
            for citation in self.unexecuted.get(identifier, [])
        )
        if identifier in self.front_only:
            listed = "<br>".join(f"`{c.test}`" for c in tests)
            return f"**front seul** : {listed}{not_run}"
        if tests:
            return "<br>".join(f"`{citation.test}`" for citation in tests) + not_run
        if identifier in self.acceptance:
            verdict = "**non couverte** — vérifiée en recette, procès-verbal attendu"
        else:
            verdict = "**non couverte**" if requirement.is_mandatory else "non couverte"
        return verdict + not_run


def unknown_message(citation: Citation) -> str:
    """Say why a citation matches nothing; a misplaced one says which mark to use."""
    message = f"{citation.test}: cites {citation.requirement}, unknown"
    if citation.misplaced:
        if _STORY_IDENTIFIER.fullmatch(citation.requirement):
            message += " (a story goes under `story`, not `requirement`)"
        else:
            message += " (a requirement goes under `requirement`, not `story`)"
    return message


def report(
    requirements: tuple[projection.Requirement, ...],
    found: list[Citation],
    declaration: paths.Declaration,
    front_closed: frozenset[str] = frozenset(),
    known_stories: frozenset[str] = frozenset(),
) -> Report:
    """Confront the citations with the requirements of the document.

    The declaration gives the families of tests and their order; ``front_closed`` names the
    requirements the front's epics close: for them, the front's families count; for the
    others, a citation by the front alone does not. A citation of a story is kept apart, and
    refused when ``known_stories`` does not hold the story.
    """
    by_identifier = {requirement.identifier: requirement for requirement in requirements}
    by_key = {requirement.key: requirement for requirement in requirements}
    covered: dict[str, list[Citation]] = defaultdict(list)
    unexecuted: dict[str, list[Citation]] = defaultdict(list)
    unknown: list[Citation] = []
    outdated: list[tuple[Citation, str]] = []
    stories: dict[str, list[Citation]] = defaultdict(list)
    unknown_stories: list[Citation] = []
    for citation in found:
        if citation.misplaced:
            unknown.append(citation)
        elif citation.is_story:
            stories[citation.requirement].append(citation)
            if citation.requirement not in known_stories:
                unknown_stories.append(citation)
        elif citation.requirement in by_identifier:
            (covered if citation.executed else unexecuted)[citation.requirement].append(citation)
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
        dict(unexecuted),
        dict(stories),
        unknown_stories,
    )


def _print(result: Report, mandatory: list[projection.Requirement]) -> None:
    """Print the families that cite each covered F0 requirement, then the count."""
    for requirement in mandatory:
        families = result.families(requirement.identifier)
        if families:
            note = " (front alone)" if requirement.identifier in result.front_only else ""
            print(f"{requirement.identifier}: {', '.join(families)}{note}")
        elif requirement.identifier in result.unexecuted:
            print(f"{requirement.identifier}: cited by tests not run alone")
    for story, cited in sorted(result.stories.items()):
        print(f"{story}: own criteria of the story, {len(cited)} test(s), not counted")
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
    if identifier in result.unexecuted:
        return " (cited by tests not run alone)"
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
    epics = roadmap.read()
    front_closed = closed_by_the_front(epics)
    try:
        found = citations(declaration)
    except titles.UnreadableError as unreadable:
        print(unreadable, file=sys.stderr)
        return 1
    known_stories = frozenset(story.identifier for epic in epics for story in epic.stories)
    result = report(requirements, found, declaration, front_closed, known_stories)
    mandatory = [requirement for requirement in requirements if requirement.is_mandatory]
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(result.markdown([r for r in requirements if not r.is_example]))
    for citation in result.unknown:
        print(unknown_message(citation), file=sys.stderr)
    for citation, current in result.outdated:
        print(
            f"{citation.test}: cites {citation.requirement}, now {current}",
            file=sys.stderr,
        )
    for citation in result.unknown_stories:
        print(
            f"{citation.test}: cites {citation.requirement}, a story no file of docs/roadmap holds",
            file=sys.stderr,
        )
    _print(result, mandatory)
    failed = bool(result.unknown or result.outdated or result.unknown_stories)
    if options.release and result.missing:
        for identifier in result.missing:
            print(f"not covered: {identifier}{_reason(result, identifier)}", file=sys.stderr)
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
