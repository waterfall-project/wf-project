# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the measure of a lot."""

import subprocess
from pathlib import Path

import pytest

from wftools import lotsize, paths

DECLARATION = paths.parse(
    """
[[generated]]
paths = ["**/uv.lock", "frontend/src/api/generated/**"]
by = "tools"

[tests]
paths = ["tools/tests/**", "frontend/**/*.test.ts"]
"""
)


def test_lines_are_sorted_by_kind() -> None:
    numstat = """\
40\t10\ttools/src/wftools/lotsize.py
30\t0\ttools/tests/test_lotsize.py
12\t3\tfrontend/src/grid.ts
5\t0\tfrontend/src/grid.test.ts
900\t100\tfrontend/src/api/generated/schema.d.ts
200\t50\ttools/uv.lock
20\t2\tdocs/dev/README.md
-\t-\tdocs/assets/logo.png
"""
    size = lotsize.measure(numstat, DECLARATION)
    assert (size.production, size.tests, size.other) == (65, 35, 22)
    assert size.total == 122
    assert size.generated == 1250
    assert size.binary == ["docs/assets/logo.png"]


def test_an_empty_diff_measures_nothing() -> None:
    assert lotsize.measure("", DECLARATION).total == 0


def git(repository: Path, *arguments: str) -> None:
    """Run git in a repository, failing loudly."""
    subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with an epic branch and a lot branch that adds code and a test."""
    git(tmp_path, "init", "--quiet", "--initial-branch=epic")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    (tmp_path / "README.md").write_text("readme\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "--message=epic")
    git(tmp_path, "switch", "--quiet", "--create", "lot")
    (tmp_path / "tools" / "tests").mkdir(parents=True)
    (tmp_path / "tools" / "a.py").write_text("x = 1\ny = 2\n")
    (tmp_path / "tools" / "tests" / "test_a.py").write_text("def test_a() -> None: ...\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "--message=lot")
    monkeypatch.setattr(lotsize, "REPOSITORY", tmp_path)
    monkeypatch.setattr(paths, "read", lambda: DECLARATION)
    return tmp_path


@pytest.mark.usefixtures("repository")
def test_a_lot_is_measured_against_its_epic(capsys: pytest.CaptureFixture[str]) -> None:
    assert lotsize.main(["epic", "HEAD"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "3 lines — production 2, tests 1, other 0"


def test_uncommitted_work_counts_on_a_workstation(
    repository: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repository / "tools" / "a.py").write_text("x = 1\ny = 2\nz = 3\n")
    assert lotsize.main(["epic"]) == 0
    assert capsys.readouterr().out.startswith("4 lines — production 3")


def test_an_overrun_never_fails() -> None:
    size = lotsize.measure("5000\t0\ttools/src/big.py", DECLARATION)
    assert size.production == 5000
