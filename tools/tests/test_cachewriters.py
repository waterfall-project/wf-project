# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The caches of Actions are written by two workflows and read by the others (US-1910).

The criterion of US-1910 this lot closes — the cache of Actions holds under its quota of 10 GB,
without eviction or cold install, and `.next/cache` is kept from one run to the next — is held here
on what the workflows say: a pass of the merge queue, which sees its own caches and those of main,
saved its own copy of the store of pnpm (188 MB, 6.7 GB in all on 2026-11-13) and of every cache
of uv, of ESLint and of pandoc. The quota itself is read in the repository (`gh cache list`).
"""

from typing import Any

import yaml

from wftools import REPOSITORY

WORKFLOWS = REPOSITORY / ".github" / "workflows"
WRITERS = {"front-cache.yml", "images.yml"}


def documents() -> dict[str, dict[str, Any]]:
    return {
        (path.name if path.parent == WORKFLOWS else path.parent.name): yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
        for path in sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.parent.glob("actions/*/*.yml")])
    }


def steps(document: dict[str, Any]) -> list[dict[str, Any]]:
    if "jobs" not in document:
        return list(document["runs"].get("steps", []))
    return [step for job in document["jobs"].values() for step in job.get("steps", [])]


def test_no_workflow_but_the_two_writers_saves_a_cache() -> None:
    saving: list[str] = []
    for name, document in documents().items():
        if name in WRITERS:
            continue
        for step in steps(document):
            uses = step.get("uses", "")
            options = step.get("with") or {}
            if uses.startswith(("actions/cache@", "actions/cache/save@")):
                saving.append(f"{name}: {uses}")
            if uses.startswith("actions/setup-node@") and "cache" in options:
                saving.append(f"{name}: setup-node cache")
            if uses.startswith("astral-sh/setup-uv@") and (
                options.get("enable-cache") and options.get("save-cache") is not False
            ):
                saving.append(f"{name}: setup-uv saves")
    assert saving == []


def test_only_the_publication_of_the_caches_of_builds_writes_them() -> None:
    makefile = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
    assert makefile.count("build-cache-to,") == 3
    assert "--cache-to" not in (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    for name, document in documents().items():
        for step in steps(document):
            if "make build-cache" in step.get("run", ""):
                assert name == "images.yml"


def test_the_writers_write_on_the_branch_and_at_the_creation_of_an_epic_branch() -> None:
    triggers = documents()["front-cache.yml"][True]
    assert triggers["push"]["branches"] == ["main", "epic/**"]
    assert "create" in triggers
    assert "schedule" in triggers
    job = documents()["front-cache.yml"]["jobs"]["write"]
    assert "startsWith(github.event.ref, 'epic/')" in job["if"]


def test_next_cache_is_kept_by_front_cache_and_read_by_the_build_of_the_front() -> None:
    written = [step for step in steps(documents()["front-cache.yml"]) if "next" in str(step)]
    assert any(step.get("uses", "").startswith("actions/cache/save@") for step in written)
    reading = [
        step
        for step in steps(documents()["ci.yml"])
        if (step.get("with") or {}).get("path") == "frontend/.next/cache"
    ]
    assert [step["uses"].split("@")[0] for step in reading] == ["actions/cache/restore"]


def test_the_caches_of_a_deleted_branch_are_removed_with_the_right_to_delete_alone() -> None:
    document = documents()["cache-clean.yml"]
    assert list(document[True]) == ["delete"]
    assert document["permissions"] == {"actions": "write"}
    job = document["jobs"]["branch"]
    assert job["if"] == "github.event.ref_type == 'branch'"
    assert job["steps"][-1]["run"].startswith('gh cache delete --all --ref "$DELETED"')


def test_only_the_job_that_prunes_may_delete_in_the_writer() -> None:
    jobs = documents()["front-cache.yml"]["jobs"]
    assert "permissions" not in jobs["write"]
    assert jobs["prune"]["permissions"] == {"actions": "write"}
