# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the report of requirement coverage by tests."""

import subprocess
from pathlib import Path

import pytest

from wftools import coverage, paths, projection, roadmap
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
        ("backend/tests/examples/test_portfolio.py", "back"),
        ("tools/tests/test_coverage.py", "tools"),
        ("fixtures/api/volume/build.py", "tools"),
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
        "tools/tests/test_t.py": f'import pytest\n\n{MARK}("WF-QUA-0030-A")\ndef test_t(): ...\n',
        "frontend/src/g.ts": 'it("not a test file [WF-QUA-0020-A]", () => {});\n',
    }
    for path, source in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(source, encoding="utf-8")
    found = coverage.citations(DECLARATION, tmp_path)
    assert sorted((c.requirement, c.family) for c in found) == [
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


def test_the_front_closes_the_requirements_its_epic_closes_entirely() -> None:
    epics = (
        roadmap.parse_epic("EP-02", EPIC.format(epic="EP-02")),
        roadmap.parse_epic("EP-03", EPIC.format(epic="EP-03").replace("WF-IHM", "WF-ADM")),
    )
    assert coverage.closed_by_the_front(epics) == frozenset({"WF-IHM-0010-A"})


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
    monkeypatch.setattr(
        roadmap, "read", lambda: (roadmap.parse_epic("EP-02", EPIC.format(epic="EP-02")),)
    )
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
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert coverage.main([]) == 0
    text = summary.read_text(encoding="utf-8")
    assert "## Couverture des exigences par les tests" in text
    assert "| Exigence | Flex | Titre | Familles | Tests |" in text
