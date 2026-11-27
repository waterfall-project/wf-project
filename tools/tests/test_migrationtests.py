# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tests of the back of the last published version, on the schema of the branch (US-2850).

``make migrations-tests`` runs them in the full tier of the chain (``make check-migrations``); these
tests hold what the tool decides by itself — which version is N, what of its tree it replaces and
what it leaves out, how its tests run — on a git and a tree played by fakes. They cite WF-DAT-0140-A
(its first sentence): the code of the version N runs on the schema the branch migrated.
"""

import io
import os
import tarfile
from typing import TYPE_CHECKING

import pytest

from wftools import migrationtests
from wftools.migrationreport import REPORT
from wftools.migrationtests import (
    PLUGIN,
    VERSIONS,
    MigrationTrialError,
    Version,
    extract,
    last_published,
    lay_migrations,
    own_tests,
    pytest_command,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.story("US-2850")


def tags(listed: str, code: int = 0) -> migrationtests.Read:
    """Return a git that lists the tags the base reaches."""

    def read(command: list[str]) -> tuple[int, str]:
        assert command == ["git", "tag", "--list", "v*", "--merged", "HEAD"]
        return code, listed

    return read


def archive(files: dict[str, str]) -> bytes:
    """Return a tar of the files named, as ``git archive`` writes one."""
    written = io.BytesIO()
    with tarfile.open(fileobj=written, mode="w") as tar:
        for name, text in files.items():
            data = text.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    return written.getvalue()


@pytest.mark.requirement("WF-DAT-0140-A")
def test_n_is_the_highest_published_version_by_its_numbers_not_by_its_text() -> None:
    found = last_published(tags("v0.9.0\nv0.10.0\nv0.3.0\nv1.0.0-rc1\nvnext\n"))
    assert found == Version("v0.10.0")
    assert found is not None
    assert found.tag == "0.10.0"


@pytest.mark.requirement("WF-DAT-0140-A")
def test_without_a_published_version_there_is_no_n() -> None:
    assert last_published(tags("v1.0.0-rc1\n")) is None


def test_tags_that_cannot_be_listed_stop_the_tool() -> None:
    with pytest.raises(MigrationTrialError, match="cannot be listed"):
        last_published(tags("fatal: not a git repository", code=128))


@pytest.mark.requirement("WF-DAT-0140-A")
def test_the_migrations_of_the_branch_replace_those_of_n_and_its_own_tests_are_left_out(
    tmp_path: Path,
) -> None:
    tree = tmp_path / "n"
    back = extract(
        archive(
            {
                f"{VERSIONS}/__init__.py": "",
                f"{VERSIONS}/0001_first.py": "n",
                f"{VERSIONS}/0002_second_of_n.py": "n",
                "backend/tests/test_migrations.py": "",
                "backend/tests/test_migration_partitions.py": "",
                "backend/tests/test_projects.py": "",
            }
        ),
        tree,
    )
    branch = tmp_path / "branch"
    (branch / VERSIONS).mkdir(parents=True)
    for name in ("__init__.py", "0001_first.py", "0002_second.py", "0003_third.py"):
        (branch / VERSIONS / name).write_text(f"branch {name}", encoding="utf-8")

    laid = lay_migrations(tree, branch)

    assert back == tree / "backend"
    assert laid == ["0001_first.py", "0002_second.py", "0003_third.py"]
    assert sorted(path.name for path in (tree / VERSIONS).iterdir()) == [
        "0001_first.py",
        "0002_second.py",
        "0003_third.py",
        "__init__.py",
    ]
    assert (tree / VERSIONS / "0001_first.py").read_text(encoding="utf-8") == "branch 0001_first.py"
    left_out = own_tests(back)
    assert left_out == ["tests/test_migration_partitions.py", "tests/test_migrations.py"]
    # Left out of the collection, not of the tree: another test may import them.
    assert (back / "tests" / "test_migrations.py").is_file()


def test_a_tree_without_migrations_is_refused(tmp_path: Path) -> None:
    with pytest.raises(MigrationTrialError, match="holds no"):
        extract(archive({"README.md": ""}), tmp_path)


@pytest.mark.requirement("WF-DAT-0140-A")
def test_the_tests_of_n_run_on_the_share_of_the_slot_without_its_own_tests_of_migrations() -> None:
    command = pytest_command(
        {"WATERFALL_PROCESSORS": "3", "SHARD": "2/4"}, ["tests/test_migrations.py"]
    )
    assert command[:5] == ["uv", "run", "--frozen", "--no-sync", "pytest"]
    assert command[command.index("-n") + 1] == "3"
    assert "--ignore=tests/test_migrations.py" in command
    assert command[-1] == "--shard=2/4"
    assert not any(word.startswith("--shard") for word in pytest_command({}, []))


def test_the_back_of_n_does_not_run_in_the_environment_of_the_tools_but_reaches_its_plugin(
    tmp_path: Path,
) -> None:
    report = tmp_path / "outcomes.jsonl"
    given = {"VIRTUAL_ENV": "/tools", "PATH": "/bin", "PYTHONPATH": "/mine"}
    assert migrationtests.child_environment(given, report) == {
        "PATH": "/bin",
        "PYTHONPATH": f"{migrationtests.TOOLS}{os.pathsep}/mine",
        REPORT: str(report),
    }
    command = pytest_command({}, [])
    assert command[command.index(PLUGIN) - 1] == "-p"


def test_without_a_published_version_the_tool_says_it_is_not_executed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(migrationtests, "_read", tags(""))
    assert migrationtests.main([], {"GITHUB_ACTIONS": "true"}) == 0
    said = capsys.readouterr().out
    assert said.startswith("::notice::wftools.migrationtests: not executed: no published version")
    assert "WF-DAT-0140-A is not held" in said
