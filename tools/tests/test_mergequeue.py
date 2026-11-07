# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge queue of an epic's branch, created and checked (US-1370).

The tool runs as the Makefile runs it, ``python -m wftools.mergequeue``, with a fake ``gh`` first
on the ``PATH``: an executable that serves the rulesets kept in a directory and keeps what is
posted. No test reaches the real API.
"""

import json
import os
import stat
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

FAKE_GH = """\
#!{python}
import os, sys
directory = os.environ["FAKE_GH_DIR"]
arguments = sys.argv[1:]
with open(os.path.join(directory, "calls"), "a") as calls:
    calls.write(" ".join(arguments) + "\\n")
if arguments[:3] == ["api", "--method", "POST"]:
    if os.path.exists(os.path.join(directory, "fail-post")):
        sys.exit("HTTP 422 Validation Failed")
    with open(os.path.join(directory, "posted"), "w") as posted:
        posted.write(sys.stdin.read())
elif arguments[0] == "api" and arguments[-1].endswith("/rulesets"):
    with open(os.path.join(directory, "list")) as listed:
        print(listed.read())
elif arguments[0] == "api":
    name = arguments[1].rsplit("/", 1)[1]
    path = os.path.join(directory, f"ruleset-{{name}}.json")
    if not os.path.exists(path):
        sys.exit("HTTP 404")
    with open(path) as ruleset:
        print(ruleset.read())
else:
    sys.exit("unexpected call")
"""
BRANCH = "refs/heads/epic/EP-21"


def ruleset(
    identifier: int, branch: str = BRANCH, enforcement: str = "active", *, queue: bool = True
) -> dict[str, object]:
    """Return a ruleset as the API reads it."""
    rules: list[dict[str, object]] = [{"type": "non_fast_forward"}]
    if queue:
        rules.append({"type": "merge_queue", "parameters": {}})
    return {
        "id": identifier,
        "name": f"set {identifier}",
        "enforcement": enforcement,
        "conditions": {"ref_name": {"exclude": [], "include": [branch]}},
        "rules": rules,
    }


class Rulesets:
    """The fake ``gh`` of a test, and the rulesets it serves."""

    def __init__(self, directory: Path, sets: list[dict[str, object]], per_page: int = 30) -> None:
        self.directory = directory
        bin_directory = directory / "bin"
        bin_directory.mkdir()
        gh = bin_directory / "gh"
        gh.write_text(FAKE_GH.format(python=sys.executable))
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.bin = bin_directory
        summaries = [{"id": one["id"], "name": one["name"]} for one in sets]
        pages = [summaries[i : i + per_page] for i in range(0, len(summaries), per_page)]
        (directory / "list").write_text(json.dumps(pages or [[]]))
        for one in sets:
            (directory / f"ruleset-{one['id']}.json").write_text(json.dumps(one))

    @property
    def posted(self) -> dict[str, object] | None:
        """Return what the tool posted, or None when it posted nothing."""
        path = self.directory / "posted"
        return json.loads(path.read_text()) if path.exists() else None

    @property
    def calls(self) -> list[str]:
        """Return the calls of ``gh``, one per line."""
        path = self.directory / "calls"
        return path.read_text().splitlines() if path.exists() else []

    def run(self, *arguments: str) -> tuple[int, str, str]:
        """Run the tool; return its code, what it wrote and its error output."""
        process = subprocess.run(
            [sys.executable, "-m", "wftools.mergequeue", *arguments],
            env={
                **os.environ,
                "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                "FAKE_GH_DIR": str(self.directory),
            },
            cwd=REPOSITORY / "tools",
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        return process.returncode, process.stdout, process.stderr


def serving(tmp_path: Path, *sets: dict[str, object], per_page: int = 30) -> Rulesets:
    return Rulesets(tmp_path, list(sets), per_page)


def test_create_posts_the_model_with_the_name_and_the_branch_of_the_epic(tmp_path: Path) -> None:
    """US-1370: ``make merge-queue`` creates the ruleset « merge queue epic/EP-nn »."""
    fake = serving(tmp_path, ruleset(1, "refs/heads/epic/EP-04"))
    code, _, error = fake.run("create", "EP-21")
    assert (code, error) == (0, "")
    model = json.loads((REPOSITORY / ".github" / "rulesets" / "merge-queue.json").read_text())
    expected = {
        **model,
        "name": "merge queue epic/EP-21",
        "conditions": {"ref_name": {"exclude": [], "include": [BRANCH]}},
    }
    assert fake.posted == expected
    assert fake.calls[0] == "api --paginate --slurp repos/{owner}/{repo}/rulesets"
    assert fake.calls[-1] == "api --method POST repos/{owner}/{repo}/rulesets --input -"


def test_the_model_is_a_merge_queue_without_identifiers_or_dates() -> None:
    """US-1370: the model is the ruleset of EP-05 without its identifiers or its dates."""
    model = json.loads((REPOSITORY / ".github" / "rulesets" / "merge-queue.json").read_text())
    assert "merge_queue" in [rule["type"] for rule in model["rules"]]
    assert model["enforcement"] == "active"
    for key in ("id", "source", "source_type", "node_id", "_links", "created_at", "updated_at"):
        assert key not in model


def test_create_refuses_when_a_ruleset_already_targets_the_branch(tmp_path: Path) -> None:
    """US-1370: the creation is refused when a ruleset already targets the branch."""
    fake = serving(
        tmp_path, ruleset(1, "refs/heads/epic/EP-04"), ruleset(2, enforcement="disabled")
    )
    code, _, error = fake.run("create", "EP-21")
    assert code == 1
    assert error.startswith("merge-queue: ")
    assert BRANCH in error
    assert fake.posted is None


@pytest.mark.parametrize("epic", [[], [""], ["EP-"], ["ep-21"], ["21"], ["EP-21b"]])
def test_create_and_check_refuse_a_missing_or_malformed_epic(
    tmp_path: Path, epic: list[str]
) -> None:
    """US-1370: ``EPIC`` missing or not of the form ``EP-nn`` is refused, before any call."""
    fake = serving(tmp_path)
    for command in ("create", "check"):
        code, _, error = fake.run(command, *epic)
        assert code == 1
        assert "EP-nn" in error
        assert "Traceback" not in error
    assert fake.calls == []
    assert fake.posted is None


def test_check_passes_on_an_active_ruleset_with_a_merge_queue(tmp_path: Path) -> None:
    """US-1370: ``make merge-queue-check`` passes on an active ruleset with a merge_queue rule."""
    fake = serving(tmp_path, ruleset(1, "refs/heads/epic/EP-04"), ruleset(2))
    code, out, error = fake.run("check", "EP-21")
    assert (code, error) == (0, "")
    assert BRANCH in out
    assert fake.posted is None


def test_check_says_that_no_ruleset_targets_the_branch(tmp_path: Path) -> None:
    """US-1370: ``make merge-queue-check`` fails when there is no ruleset."""
    code, _, error = serving(tmp_path, ruleset(1, "refs/heads/epic/EP-04")).run("check", "EP-21")
    assert code == 1
    assert f"no ruleset targets {BRANCH}" in error
    assert "make merge-queue EPIC=EP-21" in error


def test_check_says_that_the_ruleset_has_no_merge_queue_rule(tmp_path: Path) -> None:
    """US-1370: ``make merge-queue-check`` fails when the ruleset has no queue rule."""
    code, _, error = serving(tmp_path, ruleset(2, queue=False)).run("check", "EP-21")
    assert code == 1
    assert "no merge_queue rule" in error
    assert "not active" not in error


def test_check_says_that_the_ruleset_is_not_active(tmp_path: Path) -> None:
    """US-1370: ``make merge-queue-check`` fails when the ruleset is not active."""
    code, _, error = serving(tmp_path, ruleset(2, enforcement="evaluate")).run("check", "EP-21")
    assert code == 1
    assert "evaluate, not active" in error
    assert "no merge_queue rule" not in error


def test_a_gh_that_fails_or_answers_badly_is_said_without_a_trace(tmp_path: Path) -> None:
    """US-1370: an unusable ``gh`` is a refusal, not a traceback."""
    fake = serving(tmp_path, ruleset(2))
    (tmp_path / "list").write_text("not json")
    code, _, error = fake.run("check", "EP-21")
    assert code == 1
    assert error.startswith("merge-queue: ")
    (tmp_path / "list").write_text(json.dumps([[{"id": 9}]]))
    code, _, error = fake.run("check", "EP-21")
    assert code == 1
    assert "failed: HTTP 404" in error
    assert "Traceback" not in error


def test_make_runs_the_two_targets(tmp_path: Path) -> None:
    """US-1370: the Makefile has ``merge-queue-check`` and ``merge-queue`` on ``EPIC``."""
    fake = serving(tmp_path, ruleset(2))
    environment = {
        **os.environ,
        "PATH": f"{fake.bin}{os.pathsep}{os.environ['PATH']}",
        "PYTHONPATH": str(REPOSITORY / "tools" / "src"),
        "FAKE_GH_DIR": str(tmp_path),
    }
    codes: list[int] = []
    errors: list[str] = []
    for target, epic in (
        ("merge-queue-check", "EP-21"),
        ("merge-queue", "EP-21"),
        ("merge-queue", ""),
    ):
        process = subprocess.run(
            [
                "make",
                "--no-print-directory",
                "-C",
                str(REPOSITORY),
                target,
                f"WFTOOLS={sys.executable} -m wftools",
                f"EPIC={epic}",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        codes.append(process.returncode)
        errors.append(process.stderr)
    assert codes == [0, 2, 2]
    assert errors[0] == ""
    assert "already targets" in errors[1]
    assert BRANCH in errors[1]
    assert "EP-nn" in errors[2]
    assert fake.posted is None


def test_a_ruleset_on_a_later_page_is_seen(tmp_path: Path) -> None:
    """US-1370: the list is read over all its pages, for ``create`` and for ``check``."""
    others = [ruleset(number, "refs/heads/epic/EP-04") for number in range(1, 4)]
    fake = serving(tmp_path, *others, ruleset(4), per_page=2)
    assert len(json.loads((tmp_path / "list").read_text())) == 2
    code, out, error = fake.run("check", "EP-21")
    assert (code, error) == (0, "")
    assert BRANCH in out
    code, _, error = fake.run("create", "EP-21")
    assert code == 1
    assert "already targets" in error
    assert fake.posted is None


def test_a_ruleset_that_excludes_the_branch_does_not_target_it(tmp_path: Path) -> None:
    """US-1370: a ruleset that includes and excludes the branch is not a queue on it."""
    both = ruleset(2)
    both["conditions"] = {"ref_name": {"exclude": [BRANCH], "include": [BRANCH]}}
    fake = serving(tmp_path, both)
    code, _, error = fake.run("check", "EP-21")
    assert code == 1
    assert f"no ruleset targets {BRANCH}" in error


def test_create_says_a_post_that_gh_refuses(tmp_path: Path) -> None:
    """US-1370: a failed ``POST`` is a refusal with the answer of GitHub, not a traceback."""
    fake = serving(tmp_path)
    (tmp_path / "fail-post").write_text("")
    code, out, error = fake.run("create", "EP-21")
    assert code == 1
    assert out == ""
    assert error.startswith("merge-queue: ")
    assert "HTTP 422 Validation Failed" in error
    assert "Traceback" not in error
    assert fake.posted is None
