# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The caches of Actions are written by two workflows and read by the others (US-1910).

The criterion of US-1910 this lot closes — the cache of Actions holds under its quota of 10 GB,
without eviction or cold install, and `.next/cache` is kept from one run to the next — is held here
on what the workflows say: a pass of the merge queue, which sees its own caches and those of main,
saved its own copy of the store of pnpm (188 MB, 6.7 GB in all on 2026-11-13) and of every cache
of uv, of ESLint and of pandoc. The quota itself is read in the repository (`gh cache list`).
"""

from pathlib import PurePosixPath
from typing import Any, cast

import yaml

from wftools import REPOSITORY

WORKFLOWS = REPOSITORY / ".github" / "workflows"
WRITERS = {"front-cache.yml", "images.yml"}
# Paths of the runner, which these tests only read in the workflows.
UV_PATH = PurePosixPath("/", "tmp", "setup-uv-cache").as_posix()
PNPM_PATH = PurePosixPath("/", "tmp", "pnpm-store").as_posix()


def documents() -> dict[str, dict[Any, Any]]:
    return {
        (path.name if path.parent == WORKFLOWS else path.parent.name): yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
        for path in sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.parent.glob("actions/*/*.yml")])
    }


def options(step: dict[str, Any]) -> dict[str, Any]:
    return cast("dict[str, Any]", step.get("with") or {})


def steps(document: dict[Any, Any]) -> list[dict[str, Any]]:
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
            given = options(step)
            if uses.startswith(("actions/cache@", "actions/cache/save@")):
                saving.append(f"{name}: {uses}")
            if uses.startswith("actions/setup-node@") and "cache" in given:
                saving.append(f"{name}: setup-node cache")
            if uses.startswith("astral-sh/setup-uv@") and (
                given.get("enable-cache") and given.get("save-cache") is not False
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
        if options(step).get("path") == "frontend/.next/cache"
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
    assert jobs["prune"]["permissions"] == {"actions": "write", "contents": "read"}


def uv_caches() -> dict[str, set[str]]:
    """Collect the caches of uv the workflows read or write, by the lockfiles they hash."""
    found: dict[str, set[str]] = {}
    for name, document in documents().items():
        for job in document.get("jobs", {}).values() or [document["runs"]]:
            matrix = job.get("strategy", {}).get("matrix", {}).get("include", [{"locks": ""}])
            for step in job.get("steps", []):
                given = options(step)
                if not (
                    step.get("uses", "").startswith("astral-sh/setup-uv@")
                    and given.get("enable-cache")
                ):
                    continue
                writes = given.get("save-cache") is not False
                for row in matrix:
                    glob = str(given["cache-dependency-glob"]).replace(
                        "${{ matrix.locks }}", row["locks"]
                    )
                    found.setdefault("\n".join(glob.split()), set()).add(
                        f"{name}:{'write' if writes else 'read'}"
                    )
    return found


def test_a_writer_saves_every_cache_of_uv_that_another_workflow_reads() -> None:
    caches = uv_caches()
    assert caches
    for glob, users in caches.items():
        assert "front-cache.yml:write" in users, glob
    writers = {user.split(":")[0] for users in caches.values() for user in users if "write" in user}
    assert writers == {"front-cache.yml"}


def test_every_cache_of_uv_is_at_the_same_path() -> None:
    paths = {
        options(step)["cache-local-path"]
        for document in documents().values()
        for step in steps(document)
        if step.get("uses", "").startswith("astral-sh/setup-uv@")
        and options(step).get("enable-cache")
    }
    assert paths == {UV_PATH}


def test_the_store_of_pnpm_has_one_path_and_one_key_for_the_writer_and_the_readers() -> None:
    documents_ = documents()
    reading = next(
        step for step in steps(documents_["pnpm-store"]) if "cache/restore@" in step.get("uses", "")
    )
    writing = next(
        step
        for step in steps(documents_["front-cache.yml"])
        if step.get("uses", "").startswith("actions/cache@")
        and "pnpm" in str(options(step).get("key"))
    )
    assert options(reading)["path"] == options(writing)["path"] == PNPM_PATH
    assert options(reading)["key"] == options(writing)["key"]
    assert options(reading)["restore-keys"] == options(writing)["restore-keys"]
    for document in (documents_["pnpm-store"], documents_["front-cache.yml"]):
        assert f"npm_config_store_dir={PNPM_PATH}" in str(steps(document))
    assert "cache" not in str(
        [
            options(s)
            for s in steps(documents_["front-cache.yml"])
            if "setup-node" in s.get("uses", "")
        ]
    )
