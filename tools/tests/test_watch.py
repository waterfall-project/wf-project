# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the chain pins is watched by Dependabot, and a failed path leaves its trace (US-2490).

Dependabot opens a pull request per directory it follows: an action pinned in a local action
(`.github/actions/*`) or an image pinned in `deploy/e2e` that no entry names keeps its flaws in
silence (PLC-09). A local action pinned at another commit than the workflows would also be
bumped on its own, and the chain would run two versions of one action.
"""

import re
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY

GITHUB = REPOSITORY / ".github"
WORKFLOWS = GITHUB / "workflows"
PIN = re.compile(
    r"^\s*(?:-\s+)?uses:\s*(?P<action>[\w.-]+/[\w./-]+)@(?P<sha>[0-9a-f]{40})\b", re.MULTILINE
)


def configuration() -> list[dict[str, Any]]:
    document = yaml.safe_load((GITHUB / "dependabot.yml").read_text(encoding="utf-8"))
    return cast("list[dict[str, Any]]", document["updates"])


def directories(ecosystem: str) -> list[str]:
    entry = next(update for update in configuration() if update["package-ecosystem"] == ecosystem)
    return list(entry.get("directories") or [entry["directory"]])


def pins() -> dict[str, dict[str, set[str]]]:
    """Give the commits each action is pinned at, by action, then by file."""
    found: dict[str, dict[str, set[str]]] = {}
    files = [*WORKFLOWS.glob("*.yml"), *GITHUB.glob("actions/*/action.yml")]
    for path in sorted(files):
        for match in PIN.finditer(path.read_text(encoding="utf-8")):
            # An action with a path (`actions/cache/restore`) is pinned like its repository.
            repository = "/".join(match["action"].split("/")[:2])
            name = str(path.relative_to(GITHUB))
            found.setdefault(repository, {}).setdefault(name, set()).add(match["sha"])
    return found


def commits(files: dict[str, set[str]]) -> set[str]:
    return {sha for shas in files.values() for sha in shas}


@pytest.mark.story("US-2490")
def test_dependabot_follows_the_workflows_and_the_local_actions() -> None:
    followed = directories("github-actions")
    assert "/" in followed
    assert "/.github/actions/*" in followed
    assert list(GITHUB.glob("actions/*/action.yml")), "a glob that matches nothing"


@pytest.mark.story("US-2490")
def test_dependabot_follows_the_image_of_the_paths() -> None:
    assert (REPOSITORY / "deploy" / "e2e" / "Dockerfile").is_file()
    assert "/deploy/e2e" in directories("docker")


@pytest.mark.story("US-2490")
def test_every_directory_dependabot_follows_exists() -> None:
    for update in configuration():
        for directory in directories(update["package-ecosystem"]):
            matched = list(REPOSITORY.glob(directory.lstrip("/")))
            assert matched, f"{update['package-ecosystem']}: {directory} matches nothing"


@pytest.mark.story("US-2490")
def test_an_action_is_pinned_at_one_commit_between_the_workflows_and_the_local_actions() -> None:
    differing = {action: files for action, files in pins().items() if len(commits(files)) > 1}
    assert not differing, f"actions pinned at several commits: {differing}"


@pytest.mark.story("US-2490")
def test_the_pins_are_read_in_the_workflows_and_in_the_local_actions() -> None:
    files = {name for by_file in pins().values() for name in by_file}
    assert any(name.startswith("workflows/") for name in files)
    assert any(name.startswith("actions/") for name in files)


@pytest.mark.story("US-2490")
def test_a_pin_is_read_by_action_and_by_commit() -> None:
    sha_a, sha_b = "a" * 40, "b" * 40
    texts = [f"- uses: actions/cache@{sha_a} # v1", f"  uses: actions/cache/save@{sha_b} # v2"]
    found = [(m["action"], m["sha"]) for text in texts for m in PIN.finditer(text)]
    assert found == [("actions/cache", sha_a), ("actions/cache/save", sha_b)]


def workflow(name: str) -> dict[Any, Any]:
    return cast("dict[Any, Any]", yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8")))


@pytest.mark.story("US-2490")
def test_front_cache_runs_when_a_lockfile_of_uv_changes_alone() -> None:
    # PyYAML reads the key `on` as True.
    paths = workflow("front-cache.yml")[True]["push"]["paths"]
    assert {"backend/uv.lock", "tools/uv.lock"} <= set(paths)


@pytest.mark.story("US-2490")
@pytest.mark.parametrize("name", ["service.yml", "e2e.yml"])
def test_a_path_that_fails_leaves_its_traces_for_seven_days(name: str) -> None:
    uploads = [
        step
        for job in workflow(name)["jobs"].values()
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    assert len(uploads) == 1
    (upload,) = uploads
    assert upload["if"] == "failure()"
    assert upload["with"]["path"] == "frontend/test-results/"
    assert upload["with"]["retention-days"] == 7
    assert "strategy.job-index" in upload["with"]["name"]
    # The same commit as the other uploads of the chain.
    assert len(commits(pins()["actions/upload-artifact"])) == 1
