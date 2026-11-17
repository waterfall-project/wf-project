# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the report of requirement coverage by tests."""

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from wftools import REPOSITORY, coverage, marks, paths, projection, roadmap
from wftools.coverage import Citation

pytestmark = pytest.mark.requirement("WF-QUA-0010-A")

MARK = "@pytest.mark.requirement"

PYTHON = f"""
import pytest

pytestmark = pytest.mark.requirement("WF-QUA-0010-A")


{MARK}("WF-ARC-0010-A")
def test_boundaries() -> None: ...


def helper() -> None: ...


{MARK}("WF-QUA-0020-A")
class TestExamples:
    {MARK}("WF-QUA-0030-A")
    def test_one(self) -> None: ...

    def test_two(self) -> None: ...
"""

BLOCK = """\
```yaml exigence
section: "4.7"
id: "{identifier}"
titre: "Titre de {identifier}"
flexibilite: "{flexibility}"
fbs: "FBS-4"
pbs: "PBS-5.2"
corps: "Corps."
motif: "Motif."
verification: "{verification}"
```
"""

EPIC = """\
---
id: {epic}
titre: Un EPIC d'essai
statut: en cours
famille: {family}
---

| Exigence | Titre | Portée | US |
|---|---|---|---|
| `WF-IHM-0010-A` | Navigation | entière | US-0090 |
| `WF-IHM-0060-A` | Lecture d'une grille | début — close en EP-03 | US-0110 |
"""

TS = 'describe("grid", () => {\n  it("reads a grid [WF-QUA-0050-A]", () => {});\n});\n'


def document(
    *requirements: tuple[str, str], verification: str = "Vérif."
) -> tuple[projection.Requirement, ...]:
    """Read a document made of these identifiers and flexibilities."""
    return projection.parse(
        "".join(
            BLOCK.format(identifier=i, flexibility=f, verification=verification)
            for i, f in requirements
        )
    )


DECLARATION = paths.read()
# Where the sources of the extension of Keycloak live, and their package.
EXTENSION = "deploy/keycloak/extension/src"
PACKAGE = "io/github/waterfallproject/keycloak"


def front(requirement: str, test: str = "frontend/src/a.test.ts:1") -> Citation:
    return Citation(requirement, test, "front")


def back(requirement: str, test: str = "backend/tests/test_a.py::test_a") -> Citation:
    return Citation(requirement, test, "back")


def test_python_citations_come_from_marks_on_tests_classes_and_modules() -> None:
    found = coverage.python_citations("backend/tests/t.py", PYTHON, "back")
    assert {c.family for c in found} == {"back"}
    assert sorted((c.test, c.requirement) for c in found) == [
        ("backend/tests/t.py::TestExamples::test_one", "WF-QUA-0010-A"),
        ("backend/tests/t.py::TestExamples::test_one", "WF-QUA-0020-A"),
        ("backend/tests/t.py::TestExamples::test_one", "WF-QUA-0030-A"),
        ("backend/tests/t.py::TestExamples::test_two", "WF-QUA-0010-A"),
        ("backend/tests/t.py::TestExamples::test_two", "WF-QUA-0020-A"),
        ("backend/tests/t.py::test_boundaries", "WF-ARC-0010-A"),
        ("backend/tests/t.py::test_boundaries", "WF-QUA-0010-A"),
    ]


def test_typescript_citations_come_from_titles() -> None:
    assert coverage.typescript_citations("frontend/src/g.test.ts", TS, "front") == [
        Citation("WF-QUA-0050-A", "frontend/src/g.test.ts:2", "front")
    ]


@pytest.mark.parametrize(
    ("path", "family"),
    [
        ("frontend/src/components/grid/grid.test.ts", "front"),
        ("frontend/src/components/grid/grid.dom.test.tsx", "front"),
        ("frontend/e2e/projects.spec.ts", "end-to-end"),
        ("frontend/e2e/service/sign-in.spec.ts", "end-to-end-service"),
        ("backend/tests/examples/test_portfolio.py", "back"),
        ("tools/tests/test_coverage.py", "tools"),
        ("fixtures/api/volume/build.py", "tools"),
        (f"{EXTENSION}/test/java/{PACKAGE}/NotLastNamePolicyProviderTest.java", "keycloak"),
        (f"{EXTENSION}/main/java/{PACKAGE}/NotLastNamePolicyProvider.java", None),
        ("docs/spec/tools/build.py", None),
        ("frontend/src/components/grid/grid.ts", None),
    ],
)
def test_the_repository_declares_the_family_of_each_test_path(
    path: str, family: str | None
) -> None:
    assert DECLARATION.test_family(path) == family


def test_the_front_families_are_declared_by_the_repository() -> None:
    assert coverage.FRONT_FAMILIES.issubset(DECLARATION.test_families)


def test_citations_of_a_tree_carry_the_family_of_each_file(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    files = {
        "backend/tests/test_a.py": f'import pytest\n\n{MARK}("WF-QUA-0010-A")\ndef test_a(): ...\n',
        "frontend/src/g.test.ts": TS,
        "frontend/e2e/g.spec.ts": 'test("walks [WF-QUA-0010-A]", () => {});\n',
        "frontend/e2e/service/s.spec.ts": 'test("signs in [WF-ARC-0030-A]", () => {});\n',
        "tools/tests/test_t.py": f'import pytest\n\n{MARK}("WF-QUA-0030-A")\ndef test_t(): ...\n',
        "frontend/src/g.ts": 'it("not a test file [WF-QUA-0020-A]", () => {});\n',
    }
    for path, source in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(source, encoding="utf-8")
    found = coverage.citations(DECLARATION, tmp_path)
    assert sorted((c.requirement, c.family) for c in found) == [
        ("WF-ARC-0030-A", "end-to-end-service"),
        ("WF-QUA-0010-A", "back"),
        ("WF-QUA-0010-A", "end-to-end"),
        ("WF-QUA-0030-A", "tools"),
        ("WF-QUA-0050-A", "front"),
    ]


def test_the_report_lists_every_f0_requirement_with_its_families_and_tests() -> None:
    requirements = document(
        ("WF-QUA-0010-A", "F0"), ("WF-QUA-0020-A", "F0"), ("WF-IHM-0090-A", "F1")
    )
    found = [back("WF-QUA-0010-A"), Citation("WF-QUA-0010-A", "tools/tests/t.py::t", "tools")]
    result = coverage.report(requirements, found, DECLARATION)
    assert result.covered == {"WF-QUA-0010-A": found}
    assert result.families("WF-QUA-0010-A") == ["back", "tools"]
    assert result.uncovered == ["WF-QUA-0020-A"]
    assert result.front_only == []
    markdown = result.markdown([r for r in requirements if not r.is_example])
    assert (
        "| `WF-QUA-0010-A` | F0 | Titre de WF-QUA-0010-A | back, tools "
        "| `backend/tests/test_a.py::test_a`<br>`tools/tests/t.py::t` |"
    ) in markdown
    assert "| `WF-QUA-0020-A` | F0 | Titre de WF-QUA-0020-A |  | **non couverte** |" in markdown
    assert "| `WF-IHM-0090-A` | F1 | Titre de WF-IHM-0090-A |  | non couverte |" in markdown
    assert "1 exigences F0 couvertes sur 2" in markdown


def test_removing_a_test_uncovers_its_requirement() -> None:
    requirements = document(("WF-QUA-0010-A", "F0"))
    assert coverage.report(requirements, [back("WF-QUA-0010-A")], DECLARATION).uncovered == []
    assert coverage.report(requirements, [], DECLARATION).uncovered == ["WF-QUA-0010-A"]


def test_a_requirement_the_front_alone_cites_is_counted_apart() -> None:
    requirements = document(("WF-RIS-0040-A", "F0"), ("WF-IHM-0010-A", "F0"))
    found = [
        front("WF-RIS-0040-A"),
        Citation("WF-RIS-0040-A", "frontend/e2e/r.spec.ts:3", "end-to-end"),
        front("WF-IHM-0010-A"),
    ]
    result = coverage.report(requirements, found, DECLARATION, frozenset({"WF-IHM-0010-A"}))
    assert result.front_only == ["WF-RIS-0040-A"]
    assert result.uncovered == []
    assert result.missing == ["WF-RIS-0040-A"]
    markdown = result.markdown(list(requirements))
    assert "1 exigences F0 couvertes sur 2 ; 1 couvertes par le front seul" in markdown
    assert "| end-to-end, front | **front seul** : `frontend/src/a.test.ts:1`<br>" in markdown
    assert "| `WF-IHM-0010-A` | F0 | Titre de WF-IHM-0010-A | front | `frontend/" in markdown


def test_a_citation_by_the_back_proves_what_the_front_alone_could_not() -> None:
    requirements = document(("WF-RIS-0040-A", "F0"))
    found = [back("WF-RIS-0040-A"), front("WF-RIS-0040-A")]
    result = coverage.report(requirements, found, DECLARATION)
    assert result.front_only == []
    assert result.families("WF-RIS-0040-A") == ["front", "back"]


def test_a_path_played_against_the_service_proves_what_the_back_closes() -> None:
    requirements = document(("WF-ARC-0030-A", "F0"))
    path = Citation("WF-ARC-0030-A", "frontend/e2e/service/s.spec.ts:3", "end-to-end-service")
    result = coverage.report(requirements, [front("WF-ARC-0030-A"), path], DECLARATION)
    assert result.front_only == []
    assert result.missing == []
    assert result.families("WF-ARC-0030-A") == ["end-to-end-service", "front"]


def epic(identifier: str, family: str) -> roadmap.Epic:
    """Read the sample epic under this identifier, declaring these families."""
    return roadmap.parse_epic(identifier, EPIC.format(epic=identifier, family=family))


def test_the_front_closes_the_requirements_its_epic_closes_entirely() -> None:
    other = EPIC.format(epic="EP-03", family="front, back").replace("WF-IHM", "WF-ADM")
    epics = (epic("EP-02", "front"), roadmap.parse_epic("EP-03", other))
    assert coverage.closed_by_the_front(epics) == frozenset({"WF-IHM-0010-A"})


def test_an_epic_is_the_fronts_by_its_family_alone() -> None:
    assert coverage.closed_by_the_front((epic("EP-02", "front, back"),)) == frozenset()
    assert coverage.closed_by_the_front((epic("EP-07", "front"),)) == frozenset({"WF-IHM-0010-A"})


def test_a_requirement_verified_at_acceptance_awaits_its_report() -> None:
    requirements = document(
        ("WF-EXP-0050-A", "F0"), verification="Vérifiée en recette. Une sauvegarde existe."
    )
    result = coverage.report(requirements, [], DECLARATION)
    assert result.acceptance == ["WF-EXP-0050-A"]
    assert result.uncovered == ["WF-EXP-0050-A"]
    cell = "| **non couverte** — vérifiée en recette, procès-verbal attendu |"
    assert cell in result.markdown(list(requirements))


def test_the_example_of_the_document_is_never_required() -> None:
    requirements = document((projection.EXAMPLE_IDENTIFIER, "F0"))
    assert coverage.report(requirements, [], DECLARATION).uncovered == []


def test_an_unknown_or_outdated_citation_is_named() -> None:
    requirements = document(("WF-QUA-0010-B", "F0"))
    old, new = back("WF-QUA-0010-A", "t::old"), back("WF-XXX-0010-A", "t::new")
    result = coverage.report(requirements, [old, new], DECLARATION)
    assert result.outdated == [(old, "WF-QUA-0010-B")]
    assert result.unknown == [new]


def test_a_release_with_an_uncovered_f0_requirement_fails_naming_it(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    def no_citation(_declaration: paths.Declaration, _repository: Path = Path()) -> list[Citation]:
        return []

    monkeypatch.setattr(coverage, "citations", no_citation)
    monkeypatch.setattr(roadmap, "read", lambda: ())
    monkeypatch.setattr(projection, "read", lambda: document(("WF-QUA-0010-A", "F0")))
    assert coverage.main([]) == 0
    assert coverage.main(["--release"]) == 1
    assert "not covered: WF-QUA-0010-A" in capsys.readouterr().err


def test_a_release_with_a_requirement_the_front_alone_covers_fails_naming_it(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    requirements = document(("WF-RIS-0040-A", "F0"), ("WF-IHM-0010-A", "F0"))

    def two_front_citations(
        _declaration: paths.Declaration, _repository: Path = Path()
    ) -> list[Citation]:
        return [front("WF-RIS-0040-A"), front("WF-IHM-0010-A")]

    monkeypatch.setattr(coverage, "citations", two_front_citations)
    monkeypatch.setattr(roadmap, "read", lambda: (epic("EP-02", "front"),))
    monkeypatch.setattr(projection, "read", lambda: requirements)
    assert coverage.main([]) == 0
    out = capsys.readouterr().out
    assert "WF-RIS-0040-A: front (front alone)" in out
    assert "WF-IHM-0010-A: front\n" in out
    assert "1 of 2 F0 requirements covered; 1 cited by the front alone" in out
    assert coverage.main(["--release"]) == 1
    assert "not covered: WF-RIS-0040-A (front alone)" in capsys.readouterr().err


def test_the_report_goes_to_the_job_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # On a document of its own: make requirements reports on the repository itself (#2157).
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    def one_citation(_declaration: paths.Declaration, _repository: Path = Path()) -> list[Citation]:
        return [back("WF-QUA-0010-A", "tests/test_x.py::test_y")]

    monkeypatch.setattr(coverage, "citations", one_citation)
    monkeypatch.setattr(roadmap, "read", lambda: ())
    monkeypatch.setattr(projection, "read", lambda: document(("WF-QUA-0010-A", "F0")))
    assert coverage.main([]) == 0
    text = summary.read_text(encoding="utf-8")
    assert "## Couverture des exigences par les tests" in text
    assert "| Exigence | Flex | Titre | Familles | Tests |" in text
    assert "WF-QUA-0010-A" in text


# US-2440: the report counts only what runs.

TS_RUN_AND_NOT = """\
// A comment cites nothing: [WF-QUA-0020-A].
/* Nor does a block [WF-QUA-0020-A]. */
test("reads a grid [WF-QUA-0050-A]", async () => {});
test.fixme("writes in a grid [WF-QUA-0050-A]", async () => {});
it.skip("sorts a grid [WF-QUA-0030-A]", () => {});
it.todo("filters a grid [WF-QUA-0040-A]");
"""


def test_a_typescript_test_declared_not_run_covers_nothing_and_a_comment_cites_nothing() -> None:
    found = coverage.typescript_citations("frontend/e2e/g.spec.ts", TS_RUN_AND_NOT, "end-to-end")
    assert [(c.requirement, c.test, c.executed) for c in found] == [
        ("WF-QUA-0050-A", "frontend/e2e/g.spec.ts:3", True),
        ("WF-QUA-0050-A", "frontend/e2e/g.spec.ts:4", False),
        ("WF-QUA-0030-A", "frontend/e2e/g.spec.ts:5", False),
        ("WF-QUA-0040-A", "frontend/e2e/g.spec.ts:6", False),
    ]
    requirements = document(("WF-QUA-0050-A", "F0"), ("WF-QUA-0030-A", "F0"))
    result = coverage.report(requirements, found, DECLARATION, frozenset({"WF-QUA-0050-A"}))
    assert [c.test for c in result.covered["WF-QUA-0050-A"]] == ["frontend/e2e/g.spec.ts:3"]
    assert result.uncovered == ["WF-QUA-0030-A"]
    markdown = result.markdown(list(requirements))
    assert "| `frontend/e2e/g.spec.ts:3`<br>`frontend/e2e/g.spec.ts:4` (non exécuté) |" in markdown
    assert "| **non couverte**<br>`frontend/e2e/g.spec.ts:5` (non exécuté) |" in markdown


def test_a_group_declared_not_run_holds_tests_that_do_not_run() -> None:
    source = """\
describe.skip("the grid [WF-QUA-0010-A]", () => {
  it("reads [WF-QUA-0020-A]", () => {});
});
test.describe.fixme("the plan", () => {
  test.describe("its rows [WF-QUA-0030-A]", () => {
    test("walks [WF-QUA-0040-A]", async () => {});
  });
});
describe("the board [WF-QUA-0050-A]", () => {
  it.skip("drags [WF-QUA-0060-A]", () => {});
  it("drops", () => {});
});
describe("the list [WF-QUA-0070-A]", () => {
  it.skip("scrolls", () => {});
});
"""
    found = coverage.typescript_citations("frontend/src/g.test.ts", source, "front")
    assert [(c.requirement, c.executed) for c in found] == [
        ("WF-QUA-0010-A", False),
        ("WF-QUA-0020-A", False),
        ("WF-QUA-0030-A", False),
        ("WF-QUA-0040-A", False),
        ("WF-QUA-0050-A", True),
        ("WF-QUA-0060-A", False),
        ("WF-QUA-0070-A", False),
    ]


@pytest.mark.story("US-2440")
def test_a_platform_skip_in_the_body_leaves_the_citation_executed_and_another_stops_it() -> None:
    source = """\
test("imports [WF-QUA-0010-A]", async ({ page }) => {
  test.skip(!inService, "the fake back keeps nothing");
});
test("exports [WF-QUA-0020-A]", async ({ page }) => {
  test.skip(true, "service only");
});
"""
    found = coverage.typescript_citations("frontend/e2e/i.spec.ts", source, "end-to-end")
    assert [(c.requirement, c.executed) for c in found] == [
        ("WF-QUA-0010-A", True),
        ("WF-QUA-0020-A", False),
    ]
    assert found[0] == Citation("WF-QUA-0010-A", "frontend/e2e/i.spec.ts:1", "end-to-end")


PYTHON_RUN_AND_NOT = f"""
import pytest


{MARK}("WF-QUA-0080-A")
def test_written() -> None: ...


{MARK}("WF-QUA-0080-A")
@pytest.mark.unexecuted("skipped without the schema")
def test_valid(schema: object) -> None: ...


@pytest.mark.unexecuted("skipped without docker")
class TestEntrypoint:
    {MARK}("WF-QUA-0010-A")
    def test_seeds(self) -> None: ...
"""


def test_a_python_test_marked_unexecuted_covers_nothing() -> None:
    found = coverage.python_citations("backend/tests/t.py", PYTHON_RUN_AND_NOT, "back")
    assert [(c.test, c.requirement, c.executed) for c in found] == [
        ("backend/tests/t.py::test_written", "WF-QUA-0080-A", True),
        ("backend/tests/t.py::test_valid", "WF-QUA-0080-A", False),
        ("backend/tests/t.py::TestEntrypoint::test_seeds", "WF-QUA-0010-A", False),
    ]
    module = 'import pytest\n\npytestmark = pytest.mark.unexecuted("no docker")\n'
    marked = coverage.python_citations("t.py", module + PYTHON_RUN_AND_NOT, "back")
    assert [c.executed for c in marked] == [False, False, False]
    requirements = document(("WF-QUA-0080-A", "F0"))
    result = coverage.report(requirements, found, DECLARATION)
    assert result.uncovered == []
    assert [c.test for c in result.covered["WF-QUA-0080-A"]] == ["backend/tests/t.py::test_written"]
    assert [c.test for c in result.unexecuted["WF-QUA-0080-A"]] == [
        "backend/tests/t.py::test_valid"
    ]


def test_a_release_with_an_f0_requirement_only_tests_not_run_cite_fails_naming_it(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    def skipped(_declaration: paths.Declaration, _repository: Path = Path()) -> list[Citation]:
        return [Citation("WF-QUA-0080-A", "backend/tests/t.py::test_valid", "back", executed=False)]

    monkeypatch.setattr(coverage, "citations", skipped)
    monkeypatch.setattr(roadmap, "read", lambda: ())
    monkeypatch.setattr(projection, "read", lambda: document(("WF-QUA-0080-A", "F0")))
    assert coverage.main([]) == 0
    assert "WF-QUA-0080-A: cited by tests not run alone" in capsys.readouterr().out
    assert coverage.main(["--release"]) == 1
    err = capsys.readouterr().err
    assert "not covered: WF-QUA-0080-A (cited by tests not run alone)" in err


def test_the_mark_the_report_reads_is_the_one_the_plugin_requires() -> None:
    skip = f"@pytest.mark.{marks.MARK}('r')"
    source = f"import pytest\n\n{MARK}('WF-QUA-0010-A')\n{skip}\ndef test_a(): ...\n"
    assert [c.executed for c in coverage.python_citations("t.py", source, "back")] == [False]


def test_the_mark_unexecuted_is_read_in_every_form_the_plugin_accepts() -> None:
    source = """
import pytest

REASON = "no docker"
CASES = [pytest.param(1, marks=pytest.mark.unexecuted("no schema")), 2]
pytestmark: list[object] = [pytest.mark.requirement("WF-QUA-0010-A")]


@pytest.mark.unexecuted(REASON)
def test_constant() -> None: ...


@pytest.mark.parametrize(
    "x", [pytest.param(1, marks=pytest.mark.unexecuted("no docker")), 2]
)
def test_param(x: int) -> None: ...


@pytest.mark.parametrize("x", CASES)
def test_cases_built_apart(x: int) -> None: ...


@pytest.mark.parametrize("x", [1, 2])
def test_run(x: int) -> None: ...
"""
    found = coverage.python_citations("backend/tests/t.py", source, "back")
    assert [(c.test.split("::")[1], c.executed) for c in found] == [
        ("test_constant", False),
        ("test_param", False),
        ("test_cases_built_apart", False),
        ("test_run", True),
    ]


# US-2440: a criterion of a story is cited by the story.

STORY_EPIC = roadmap.Epic("EP-02", "en cours", (), (roadmap.Story("US-2160", (), ""),), ("front",))


def test_a_story_cited_in_a_title_or_by_a_mark_is_listed_apart_from_the_requirements() -> None:
    source = """\
test("draws a chart [US-2160]", () => {});
test.fixme("draws it again [US-2160]", () => {});
test("walks [WF-QUA-0010-A] [US-2160]", () => {});
"""
    typescript = coverage.typescript_citations("frontend/src/a.test.tsx", source, "front")
    python = coverage.python_citations(
        "backend/tests/t.py",
        'import pytest\n\n@pytest.mark.story("US-2160")\ndef test_a(): ...\n',
        "back",
    )
    assert [(c.requirement, c.is_story, c.executed) for c in typescript] == [
        ("US-2160", True, True),
        ("US-2160", True, False),
        ("WF-QUA-0010-A", False, True),
        ("US-2160", True, True),
    ]
    assert [(c.requirement, c.is_story) for c in python] == [("US-2160", True)]
    requirements = document(("WF-QUA-0010-A", "F0"))
    result = coverage.report(
        requirements, [*typescript, *python], DECLARATION, known_stories=frozenset({"US-2160"})
    )
    assert result.unknown_stories == []
    assert result.unknown == []
    assert [c.test for c in result.covered["WF-QUA-0010-A"]] == ["frontend/src/a.test.tsx:3"]
    assert len(result.stories["US-2160"]) == 4
    text = result.markdown(list(requirements))
    assert "## Critères propres aux US" in text
    assert "`frontend/src/a.test.tsx:2` (non exécuté)" in text


def test_a_story_no_file_of_the_roadmap_holds_fails_the_report(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    def two_stories(_declaration: paths.Declaration, _repository: Path = Path()) -> list[Citation]:
        return [front("US-2160"), front("US-9999", "frontend/src/b.test.ts:4")]

    monkeypatch.setattr(coverage, "citations", two_stories)
    monkeypatch.setattr(roadmap, "read", lambda: (STORY_EPIC,))
    monkeypatch.setattr(projection, "read", lambda: document(("WF-QUA-0010-A", "F0")))
    assert coverage.main([]) == 1
    captured = capsys.readouterr()
    assert "frontend/src/b.test.ts:4: cites US-9999, a story no file of docs/roadmap holds" in (
        captured.err
    )
    assert "US-2160: own criteria of the story" in captured.out
    assert "US-2160" not in captured.err


def test_the_mark_story_is_declared_where_pytest_declares_its_marks() -> None:
    for package in ("backend", "tools"):
        text = (REPOSITORY / package / "pyproject.toml").read_text(encoding="utf-8")
        declared = tomllib.loads(text)["tool"]["pytest"]["ini_options"]["markers"]
        assert any(entry.startswith(f"{marks.STORY}(") for entry in declared), package


def test_a_mark_takes_only_the_kind_of_identifier_it_names() -> None:
    source = (
        "import pytest\n\n"
        '@pytest.mark.story("WF-QUA-0010-A")\ndef test_a(): ...\n\n'
        '@pytest.mark.requirement("US-2160")\ndef test_b(): ...\n'
    )
    found = coverage.python_citations("backend/tests/t.py", source, "back")
    result = coverage.report(
        document(("WF-QUA-0010-A", "F0")),
        found,
        DECLARATION,
        known_stories=frozenset({"US-2160"}),
    )
    assert [c.requirement for c in result.unknown] == ["WF-QUA-0010-A", "US-2160"]
    assert "WF-QUA-0010-A" not in result.covered
    assert result.unknown_stories == []
    messages = [coverage.unknown_message(c) for c in result.unknown]
    assert messages[0].endswith("unknown (a requirement goes under `requirement`, not `story`)")
    assert messages[1].endswith("unknown (a story goes under `story`, not `requirement`)")


def test_importing_the_report_does_not_load_pytest() -> None:
    # #3752: the names of the marks live in a module of their own, shared with the plugin.
    code = "import sys, wftools.coverage; sys.exit('pytest' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_a_pytestmark_in_the_body_of_a_class_is_read_as_its_decorators() -> None:
    source = """
import pytest


class TestAlone:
    pytestmark = pytest.mark.unexecuted("no schema")

    def test_a(self) -> None: ...


class TestListed:
    pytestmark = [pytest.mark.requirement("WF-QUA-0010-A"), pytest.mark.unexecuted("no")]

    def test_b(self) -> None: ...


class TestCited:
    pytestmark: list[object] = [pytest.mark.story("US-2160")]

    @pytest.mark.requirement("WF-QUA-0020-A")
    def test_c(self) -> None: ...


class TestPlain:
    @pytest.mark.requirement("WF-QUA-0030-A")
    def test_d(self) -> None: ...
"""
    found = coverage.python_citations("backend/tests/t.py", source, "back")
    assert [(c.test.split("::")[2], c.requirement, c.executed) for c in found] == [
        ("test_b", "WF-QUA-0010-A", False),
        ("test_c", "WF-QUA-0020-A", True),
        ("test_c", "US-2160", True),
        ("test_d", "WF-QUA-0030-A", True),
    ]
