# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the selection of families from a change."""

import subprocess
from pathlib import Path

import pytest

from wftools import changes, paths

DECLARATION = """
shared = ["Makefile"]

[families.repo]
always = true
target = "check-repo"

[families.spec]
paths = ["docs/spec/**"]
target = "check-spec"
"""


def git(repository: Path, *arguments: str) -> None:
    """Run git in a repository, failing loudly."""
    subprocess.run(["git", *arguments], cwd=repository, check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a repository with one commit on main, and a branch that changes the specification."""
    git(tmp_path, "init", "--quiet", "--initial-branch=main")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "test")
    (tmp_path / "README.md").write_text("readme\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "--message=base")
    git(tmp_path, "switch", "--quiet", "--create", "change")
    (tmp_path / "docs" / "spec").mkdir(parents=True)
    (tmp_path / "docs" / "spec" / "a.md").write_text("a\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "--message=change")
    monkeypatch.setattr(changes, "REPOSITORY", tmp_path)
    monkeypatch.setattr(paths, "read", lambda: paths.parse(DECLARATION))
    return tmp_path


@pytest.mark.usefixtures("repository")
def test_changed_paths_are_those_the_branch_adds() -> None:
    assert changes.changed_paths("main", "HEAD") == ["docs/spec/a.md"]


def test_without_a_head_the_working_tree_counts(repository: Path) -> None:
    (repository / "README.md").write_text("changed\n")
    (repository / "new.txt").write_text("untracked\n")
    assert changes.changed_paths("main") == ["README.md", "docs/spec/a.md", "new.txt"]


def test_without_a_head_ignored_files_do_not_count(repository: Path) -> None:
    (repository / ".gitignore").write_text("*.log\n")
    (repository / "run.log").write_text("noise\n")
    assert changes.changed_paths("main") == [".gitignore", "docs/spec/a.md"]


@pytest.mark.usefixtures("repository")
def test_families_are_printed_for_github_actions(capsys: pytest.CaptureFixture[str]) -> None:
    assert changes.main(["main"]) == 0
    assert capsys.readouterr().out == "repo=true\nspec=true\n"


@pytest.mark.usefixtures("repository")
def test_targets_are_printed_for_make(capsys: pytest.CaptureFixture[str]) -> None:
    assert changes.main(["main", "HEAD", "--targets"]) == 0
    assert capsys.readouterr().out == "check-repo\ncheck-spec\n"


@pytest.mark.usefixtures("repository")
def test_an_untouched_family_is_false(capsys: pytest.CaptureFixture[str]) -> None:
    assert changes.main(["HEAD", "HEAD"]) == 0
    assert capsys.readouterr().out == "repo=true\nspec=false\n"
