# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The network sources of the chain that the first inventory of US-1900 left out (#2981, #3015).

The criterion of US-1900 this lot closes — the network dependencies the inventory omitted — is held
here on what the repository says: the binary of actionlint is built by the one job that lints the
workflows, the key of the PGDG repository is a file checked by its digest and never downloaded, no
job of the chain runs apt, and the images that do tell apt to try again. That the chain then passes
when one of those sources is silent is seen in its runs (`make queue-report`).
"""

import hashlib
import re
import shutil
import subprocess
import tomllib
from typing import Any

import yaml

from wftools import REPOSITORY

WORKFLOWS = REPOSITORY / ".github" / "workflows"
KEY = REPOSITORY / "backend" / "pgdg.asc"
PGDG_DIGEST = re.compile(r"echo \"([0-9a-f]{64})  /usr/share/keyrings/pgdg\.asc\"")


def text(path: str) -> str:
    """Read a file of the repository."""
    return (REPOSITORY / path).read_text(encoding="utf-8")


def run_steps() -> list[tuple[str, str]]:
    """Return every command a job of the chain runs, with the workflow and the job that run it."""
    commands: list[tuple[str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        jobs: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")).get("jobs", {})
        for name, job in jobs.items():
            commands.extend(
                (f"{path.name}:{name}", step["run"])
                for step in job.get("steps", [])
                if isinstance(step.get("run"), str)
            )
    return commands


def test_the_binary_of_actionlint_is_built_by_the_group_that_lints_the_workflows_alone() -> None:
    """The install of the tools does not need GitHub Releases; make lint-workflows does."""
    groups = tomllib.loads(text("tools/pyproject.toml"))["dependency-groups"]
    assert not any(name.startswith("actionlint") for name in groups["dev"])
    assert any(name.startswith("actionlint-py") for name in groups["workflows"])
    lint = re.search(r"^lint-workflows:.*\n\t@(.*)$", text("Makefile"), re.MULTILINE)
    assert lint is not None
    assert "--group workflows" in lint.group(1)
    assert "actionlint" in lint.group(1)


def test_the_lock_of_the_tools_keeps_actionlint_out_of_the_default_group() -> None:
    """A lock where the dev group names it would build it at every install of the tools."""
    package = next(
        entry
        for entry in tomllib.loads(text("tools/uv.lock"))["package"]
        if entry["name"] == "wftools"
    )
    assert "actionlint-py" not in [d["name"] for d in package["dev-dependencies"]["dev"]]
    assert "actionlint-py" in [d["name"] for d in package["dev-dependencies"]["workflows"]]


def test_the_key_of_the_pgdg_repository_is_the_file_the_dockerfile_checks() -> None:
    """The digest the build checks is the digest of the key in the repository, not a download."""
    dockerfile = text("backend/Dockerfile")
    found = PGDG_DIGEST.search(dockerfile)
    assert found is not None
    assert hashlib.sha256(KEY.read_bytes()).hexdigest() == found.group(1)
    assert "COPY --chmod=0644 pgdg.asc /usr/share/keyrings/pgdg.asc" in dockerfile
    assert "urlretrieve" not in dockerfile
    assert "postgresql.org/media" not in dockerfile


def test_no_job_of_the_chain_installs_a_package_with_apt() -> None:
    """The tests of the back ran apt-get against azure.archive.ubuntu.com; nothing now does.

    What a job runs is its ``run:`` steps, the shell scripts of the repository they may call and the
    recipes of the Makefile. The Dockerfiles are left out on purpose: they run apt, with its retries
    (the test below), and their layers are cached.
    """
    apt = re.compile(r"\bapt(?:-get)?\s+(?:install|update)\b")
    git = shutil.which("git")
    assert git is not None
    scripts = subprocess.run(
        [git, "ls-files", "*.sh"],
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    files = [(path, text(path)) for path in [*scripts, "Makefile"]]
    installing = [where for where, command in run_steps() if apt.search(command)]
    installing += [path for path, content in files if apt.search(content)]
    assert scripts
    assert installing == []


def test_back_tests_say_so_when_the_runner_image_drops_the_postgresql_client() -> None:
    """The job stops, naming the client, rather than installing it from a mirror."""
    commands = "\n".join(command for where, command in run_steps() if where == "back.yml:tests")
    assert "/usr/lib/postgresql/18/bin/$tool" in commands
    assert "no longer carries" in commands
    assert "(PostgreSQL) 18." in commands


def test_the_images_that_pull_apt_try_its_sources_again() -> None:
    """A source that fails once is asked again; one that stays silent fails the build, named."""
    for path in ("backend/Dockerfile", "deploy/openldap/Dockerfile"):
        dockerfile = text(path)
        assert "apt-get install" in dockerfile
        assert 'Acquire::Retries "5"' in dockerfile
        assert dockerfile.index('Acquire::Retries "5"') < dockerfile.index("apt-get update")


def test_the_layer_cache_that_spares_apt_is_still_written_after_each_merge() -> None:
    """images.yml keeps writing the cache of the layers, which most builds read instead of apt."""
    assert ("images.yml:cache", "make build-cache") in run_steps()
