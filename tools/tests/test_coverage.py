# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the report of requirement coverage by tests."""

from pathlib import Path

import pytest

from wftools import coverage, paths, projection
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
verification: "Vérif."
```
"""


def document(*requirements: tuple[str, str]) -> tuple[projection.Requirement, ...]:
    """Read a document made of these identifiers and flexibilities."""
    return projection.parse(
        "".join(BLOCK.format(identifier=i, flexibility=f) for i, f in requirements)
    )


def test_python_citations_come_from_marks_on_tests_classes_and_modules() -> None:
    found = coverage.python_citations("t.py", PYTHON)
    assert sorted((c.test, c.requirement) for c in found) == [
        ("t.py::TestExamples::test_one", "WF-QUA-0010-A"),
        ("t.py::TestExamples::test_one", "WF-QUA-0020-A"),
        ("t.py::TestExamples::test_one", "WF-QUA-0030-A"),
        ("t.py::TestExamples::test_two", "WF-QUA-0010-A"),
        ("t.py::TestExamples::test_two", "WF-QUA-0020-A"),
        ("t.py::test_boundaries", "WF-ARC-0010-A"),
        ("t.py::test_boundaries", "WF-QUA-0010-A"),
    ]


def test_typescript_citations_come_from_titles() -> None:
    source = 'describe("grid", () => {\n  it("reads a grid [WF-QUA-0050-A]", () => {});\n});\n'
    assert coverage.typescript_citations("g.test.ts", source) == [
        Citation("WF-QUA-0050-A", "g.test.ts:2")
    ]


def test_the_report_lists_every_f0_requirement_with_its_tests() -> None:
    requirements = document(
        ("WF-QUA-0010-A", "F0"), ("WF-QUA-0020-A", "F0"), ("WF-IHM-0090-A", "F1")
    )
    result = coverage.report(requirements, [Citation("WF-QUA-0010-A", "t.py::test_a")])
    assert result.covered == {"WF-QUA-0010-A": ["t.py::test_a"]}
    assert result.uncovered == ["WF-QUA-0020-A"]
    markdown = result.markdown([r for r in requirements if r.is_mandatory])
    assert "| `WF-QUA-0010-A` | Titre de WF-QUA-0010-A | `t.py::test_a` |" in markdown
    assert "| `WF-QUA-0020-A` | Titre de WF-QUA-0020-A | **non couverte** |" in markdown
    assert "WF-IHM-0090-A" not in markdown


def test_removing_a_test_uncovers_its_requirement() -> None:
    requirements = document(("WF-QUA-0010-A", "F0"))
    assert coverage.report(requirements, [Citation("WF-QUA-0010-A", "t")]).uncovered == []
    assert coverage.report(requirements, []).uncovered == ["WF-QUA-0010-A"]


def test_the_example_of_the_document_is_never_required() -> None:
    requirements = document((projection.EXAMPLE_IDENTIFIER, "F0"))
    assert coverage.report(requirements, []).uncovered == []


def test_an_unknown_or_outdated_citation_is_named() -> None:
    requirements = document(("WF-QUA-0010-B", "F0"))
    result = coverage.report(
        requirements, [Citation("WF-QUA-0010-A", "t::old"), Citation("WF-XXX-0010-A", "t::new")]
    )
    assert result.outdated == [(Citation("WF-QUA-0010-A", "t::old"), "WF-QUA-0010-B")]
    assert result.unknown == [Citation("WF-XXX-0010-A", "t::new")]


def test_a_release_with_an_uncovered_f0_requirement_fails_naming_it(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    def no_citation(_declaration: paths.Declaration) -> list[Citation]:
        return []

    monkeypatch.setattr(coverage, "citations", no_citation)
    monkeypatch.setattr(projection, "read", lambda: document(("WF-QUA-0010-A", "F0")))
    assert coverage.main([]) == 0
    assert coverage.main(["--release"]) == 1
    assert "not covered: WF-QUA-0010-A" in capsys.readouterr().err


def test_the_report_goes_to_the_job_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert coverage.main([]) == 0
    assert "## Couverture des exigences par les tests" in summary.read_text(encoding="utf-8")
