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
PIN = re.compile(r"^(?P<action>[\w.-]+/[\w./-]+)@(?P<sha>[0-9a-f]{40})$")


def configuration() -> list[dict[str, Any]]:
    document = yaml.safe_load((GITHUB / "dependabot.yml").read_text(encoding="utf-8"))
    return cast("list[dict[str, Any]]", document["updates"])


def directories(ecosystem: str) -> list[str]:
    entry = next(update for update in configuration() if update["package-ecosystem"] == ecosystem)
    return list(entry.get("directories") or [entry["directory"]])


def uses(node: object) -> list[str]:
    """Give every `uses` of a workflow or of a local action: steps and reusable jobs alike."""
    if isinstance(node, dict):
        mapping = cast("dict[str, object]", node)
        own = mapping.get("uses")
        found = [own] if isinstance(own, str) else []
        return found + [use for value in mapping.values() for use in uses(value)]
    if isinstance(node, list):
        return [use for value in cast("list[object]", node) for use in uses(value)]
    return []


def pinned(document: object) -> dict[str, set[str]]:
    """Give the commits the `uses` of a document pin, by repository."""
    found: dict[str, set[str]] = {}
    for use in uses(document):
        if match := PIN.match(use):
            # An action with a path (`actions/cache/restore`) is pinned like its repository.
            repository = "/".join(match["action"].split("/")[:2])
            found.setdefault(repository, set()).add(match["sha"])
    return found


def pins() -> dict[str, dict[str, set[str]]]:
    """Give the commits each action is pinned at, by action, then by file."""
    found: dict[str, dict[str, set[str]]] = {}
    files = [
        *(path for ext in ("yml", "yaml") for path in WORKFLOWS.glob(f"*.{ext}")),
        *(path for ext in ("yml", "yaml") for path in GITHUB.glob(f"actions/*/action.{ext}")),
    ]
    for path in sorted(files):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for repository, shas in pinned(document).items():
            found.setdefault(repository, {})[str(path.relative_to(GITHUB))] = shas
    return found


@pytest.mark.story("US-2490")
def test_the_pins_are_read_quoted_and_in_reusable_jobs() -> None:
    sha = "a" * 40
    document = yaml.safe_load(
        f"""
jobs:
  call:
    uses: "x/y/.github/workflows/z.yml@{sha}"
  build:
    steps:
      - uses: 'x/w@{sha}'
      - uses: ./local
"""
    )
    assert pinned(document) == {"x/y": {sha}, "x/w": {sha}}


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
def test_dependabot_follows_the_images_by_their_manifest_and_no_compose_file() -> None:
    # It does not read a reference behind the prefix of the mirror (#3025): the manifest of the
    # images of Docker Hub, and the image of the paths, which has no prefix, are all it follows.
    assert (REPOSITORY / "deploy" / "images" / "Dockerfile").is_file()
    assert directories("docker") == ["/deploy/images", "/deploy/e2e"]
    ecosystems = [update["package-ecosystem"] for update in configuration()]
    assert "docker-compose" not in ecosystems


@pytest.mark.story("US-2490")
def test_every_directory_dependabot_follows_exists() -> None:
    for update in configuration():
        for directory in directories(update["package-ecosystem"]):
            pattern = directory.strip("/")
            matched = list(REPOSITORY.glob(pattern)) if pattern else [REPOSITORY]
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
    document = {
        "steps": [
            {"uses": f"actions/cache@{sha_a}"},
            {"uses": f"actions/cache/save@{sha_b}"},
        ]
    }
    assert pinned(document) == {"actions/cache": {sha_a, sha_b}}


def workflow(name: str) -> dict[Any, Any]:
    return cast("dict[Any, Any]", yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8")))


@pytest.mark.story("US-2490")
def test_front_cache_runs_when_a_lockfile_of_uv_changes_alone() -> None:
    # PyYAML reads the key `on` as True.
    paths = workflow("front-cache.yml")[True]["push"]["paths"]
    assert {"backend/uv.lock", "tools/uv.lock"} <= set(paths)
    # The cache of uv is keyed on exactly these two lockfiles.
    matrix = workflow("front-cache.yml")["jobs"]["uv"]["strategy"]["matrix"]["include"]
    keyed = {lock for entry in matrix for lock in entry["locks"].split()}
    assert keyed == {"backend/uv.lock", "tools/uv.lock"}


@pytest.mark.story("US-2490")
@pytest.mark.parametrize("name", ["service.yml", "e2e.yml"])
def test_a_path_that_fails_leaves_its_traces_for_seven_days(name: str) -> None:
    uploads = [
        step
        for job in workflow(name)["jobs"].values()
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    # One for each job: the matrix of the paths names it by its index, the job `browsers` (US-0290)
    # by its own name.
    assert len(uploads) == len(workflow(name)["jobs"])
    for upload in uploads:
        assert upload["if"] == "failure()"
        assert upload["with"]["path"] == "frontend/test-results/"
        assert upload["with"]["retention-days"] == 7
        assert (
            "strategy.job-index" in upload["with"]["name"]
            or upload["with"]["name"] == "test-results-e2e-browsers"
        )
    # The same commit as the other uploads of the chain.
    assert len(commits(pins()["actions/upload-artifact"])) == 1


@pytest.mark.story("US-2490")
def test_the_e2e_job_of_the_chain_runs_the_workflow_that_leaves_the_traces() -> None:
    # The job `e2e` of ci.yml is a call: its parts, and so their traces, are those of e2e.yml.
    assert workflow("ci.yml")["jobs"]["e2e"]["uses"] == "./.github/workflows/e2e.yml"
