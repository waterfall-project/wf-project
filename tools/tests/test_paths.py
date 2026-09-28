# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the reader of tools/paths.toml."""

import pytest

from wftools import paths
from wftools.paths import DeclarationError

DECLARATION = """
shared = ["Makefile", ".github/workflows/**"]

[families.repo]
always = true
target = "check-repo"

[families.spec]
paths = ["docs/spec/**"]
target = "check-spec"

[families.contract]
paths = ["docs/api/**"]
target = "check-contract"

[[generated]]
paths = ["docs/api/INVENTORY.md", "**/uv.lock"]
by = "make inventory"

[tests]
paths = ["tools/tests/**", "frontend/**/*.test.ts"]
"""


@pytest.fixture
def declaration() -> paths.Declaration:
    """Read the sample declaration above."""
    return paths.parse(DECLARATION)


def names(families: tuple[paths.Family, ...]) -> list[str]:
    """Return the names of families, in order."""
    return [family.name for family in families]


def test_an_always_family_runs_on_any_change(declaration: paths.Declaration) -> None:
    assert names(declaration.touched(["README.md"])) == ["repo"]


def test_a_family_runs_when_its_paths_change(declaration: paths.Declaration) -> None:
    assert names(declaration.touched(["docs/api/paths/projects.yaml"])) == ["repo", "contract"]


def test_a_shared_path_runs_every_family(declaration: paths.Declaration) -> None:
    assert names(declaration.touched([".github/workflows/ci.yml"])) == ["repo", "spec", "contract"]


def test_no_change_still_runs_the_always_families(declaration: paths.Declaration) -> None:
    assert names(declaration.touched([])) == ["repo"]


@pytest.mark.parametrize(
    ("path", "generated"),
    [
        ("docs/api/INVENTORY.md", True),
        ("tools/uv.lock", True),
        ("uv.lock", True),
        ("docs/api/README.md", False),
    ],
)
def test_generated_paths(declaration: paths.Declaration, path: str, generated: bool) -> None:
    assert declaration.is_generated(path) is generated


@pytest.mark.parametrize(
    ("path", "test"),
    [
        ("tools/tests/test_paths.py", True),
        ("frontend/src/grid/grid.test.ts", True),
        ("frontend/src/grid/grid.ts", False),
        ("tools/src/wftools/paths.py", False),
    ],
)
def test_test_paths(declaration: paths.Declaration, path: str, test: bool) -> None:
    assert declaration.is_test(path) is test


def test_a_star_stays_within_a_directory() -> None:
    assert paths.matches("docs/spec/README.md", ["docs/spec/*"])
    assert not paths.matches("docs/spec/tools/build.py", ["docs/spec/*"])


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('[families.x]\ntarget = "t"\n', "either paths or always"),
        ('[families.x]\ntarget = "t"\nalways = true\npaths = ["a"]\n', "either paths or always"),
        ('[families.x]\npaths = ["a"]\n', "has no target"),
        ('[families.x]\ntarget = "t"\npaths = ["a"]\ncolour = "red"\n', r"unknown \['colour'\]"),
        ('[[generated]]\npaths = ["a"]\n', "needs paths and the command"),
        ('colour = "red"\n', r"unknown \['colour'\]"),
    ],
)
def test_a_malformed_declaration_is_refused(text: str, message: str) -> None:
    with pytest.raises(DeclarationError, match=message):
        paths.parse(text)


def test_the_declaration_of_the_repository_reads() -> None:
    declaration = paths.read()
    assert "repo" in names(declaration.families)
    assert declaration.is_generated("docs/spec/waterfall-spec.md")
    assert declaration.is_test("tools/tests/test_paths.py")


def test_an_excepted_path_is_named_with_its_reason() -> None:
    declaration = paths.parse('[[exceptions]]\npaths = ["legacy/**"]\nreason = "until #1"\n')
    assert declaration.is_excepted("legacy/old.py")
    assert not declaration.is_excepted("tools/new.py")


def test_an_exception_needs_a_reason() -> None:
    with pytest.raises(DeclarationError, match="the reason they are excepted"):
        paths.parse('[[exceptions]]\npaths = ["legacy/**"]\n')
