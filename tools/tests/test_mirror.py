# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mirror of the images of Docker Hub, and the jobs that pull from it (US-1900).

The criterion of US-1900 this lot closes — the pull of Docker Hub (« failed to fetch oauth token »)
no longer fails a run — is held here on what the repository says: no file pulls from Docker Hub,
the mirror is filled before the jobs that pull from it, and an image neither the mirror nor Docker
Hub gives fails the run naming the source. That the runs of the chain then pass when Docker Hub
does not answer is seen in the queue (``make queue-report``).
"""

import re
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, mirror
from wftools import registry as shared

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOWS = REPOSITORY / ".github" / "workflows"
DIGEST = "sha256:" + "a" * 64
INSPECTED = (0, f"Name: x\nMediaType: application/vnd.oci.image.index.v1+json\nDigest: {DIGEST}\n")
NOT_FOUND = (1, "ERROR: ghcr.io/waterfall-project/mirror/postgres: not found")
UNREACHABLE = (1, "ERROR: dial tcp: lookup ghcr.io: no such host")
POSTGRES = mirror.Mirrored("postgres", "18-trixie", DIGEST)
MAILPIT = mirror.Mirrored("axllent/mailpit", "v1.33.0", DIGEST)
# The registries a pinned image may name beside the mirror: those that are not Docker Hub.
OTHER_REGISTRIES = ("mcr.microsoft.com/", "ghcr.io/astral-sh/")
# A pinned image as a Compose file, a Dockerfile or a service names it.
PINNED = re.compile(r"^\s*(?:image:|FROM)\s+(?P<image>\S+@sha256:[0-9a-f]{64})", re.MULTILINE)
PULLING_JOBS = ("back", "front", "front-image", "keycloak", "production", "service")


class Registry:
    """A registry that answers each inspection in turn, and records the commands and the waits.

    ``copying`` is the code of the copy from Docker Hub: 0, or that of its failure.
    """

    def __init__(self, *answers: tuple[int, str], copying: int = 0) -> None:
        self.answers = list(answers)
        self.copying = copying
        self.commands: list[list[str]] = []
        self.waits: list[float] = []

    def read(self, command: list[str]) -> tuple[int, str]:
        self.commands.append(command)
        return self.answers.pop(0)

    def run(self, command: list[str]) -> int:
        self.commands.append(command)
        return self.copying

    def wait(self, seconds: float) -> None:
        self.waits.append(seconds)

    def ensure(self, images: list[mirror.Mirrored], *, push: bool = True) -> list[mirror.Mirrored]:
        """Make sure the mirror holds the images, through this registry, waiting for nothing."""
        return mirror.ensure(images, push=push, run=self.run, read=self.read, wait=self.wait)

    def main(self, root: Path, *arguments: str) -> int:
        """Play the tool on the files of a directory."""
        return mirror.main(list(arguments), self.run, self.read, self.wait, root)

    def verbs(self) -> list[str]:
        """Return the commands given, by their fourth word: inspect, create."""
        return [command[3] for command in self.commands]


def workflow(name: str) -> dict[Any, Any]:
    """Read a workflow."""
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def scanned() -> list[Path]:
    """Return the files the tool reads for the images of the mirror."""
    return sorted(
        {path for pattern in mirror.SCANNED for path in REPOSITORY.glob(pattern) if path.is_file()}
    )


def dockerfile(root: Path) -> Path:
    """Return the path of a Dockerfile of a directory standing for the repository."""
    (root / "backend").mkdir(exist_ok=True)
    return root / "backend" / "Dockerfile"


def logs_in(steps: list[dict[str, Any]]) -> bool:
    """Say whether a job logs in to the registry."""
    return any("docker/login-action" in step.get("uses", "") for step in steps)


# What the repository pulls, and from where.


def test_no_file_pulls_an_image_from_docker_hub() -> None:
    # A pinned image that names no registry is Docker Hub's: the Compose files, the Dockerfiles
    # and the services of the jobs name the mirror's, or another registry's, never that one.
    pulled = {
        f"{path.relative_to(REPOSITORY)}: {found['image']}"
        for path in scanned()
        for found in PINNED.finditer(path.read_text(encoding="utf-8"))
        if not found["image"].startswith((mirror.MIRROR, *OTHER_REGISTRIES))
    }
    assert not pulled


def test_every_image_of_docker_hub_the_files_name_is_pinned_by_a_digest() -> None:
    images = mirror.referenced()
    assert {image.path for image in images} == {
        "postgres",
        "redis",
        "caddy",
        "axllent/mailpit",
        "dxflrs/garage",
        "curlimages/curl",
        "node",
        "python",
        "debian",
        "maven",
        "adorsys/keycloak-config-cli",
        "keycloak/keycloak",
    }
    for image in images:
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", image.digest)


def test_a_reference_without_a_digest_is_not_one_of_the_mirror_images(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        f"FROM {mirror.MIRROR}/node:26-alpine\nFROM {mirror.MIRROR}/redis:8@{DIGEST}\n",
        encoding="utf-8",
    )
    assert mirror.referenced(tmp_path, ["Dockerfile"]) == [mirror.Mirrored("redis", "8", DIGEST)]


def test_an_image_is_copied_by_its_digest_from_docker_hub_to_a_tag_of_the_mirror() -> None:
    assert POSTGRES.source == f"docker.io/library/postgres@{DIGEST}"
    assert MAILPIT.source == f"docker.io/axllent/mailpit@{DIGEST}"
    assert POSTGRES.pinned == f"ghcr.io/waterfall-project/mirror/postgres@{DIGEST}"
    # Two digests of one tag of Docker Hub have two tags in the mirror: caddy has had two.
    other = mirror.Mirrored("postgres", "18-trixie", "sha256:" + "b" * 64)
    assert POSTGRES.tagged != other.tagged
    assert POSTGRES.tagged.endswith("18-trixie-aaaaaaaaaaaa")


# The workflows.


def test_the_jobs_that_pull_an_image_wait_for_the_mirror_and_may_read_it() -> None:
    chain = workflow("ci.yml")["jobs"]
    assert chain["mirror"]["permissions"]["packages"] == "write"
    for job in PULLING_JOBS:
        assert "mirror" in chain[job]["needs"], job
        assert chain[job]["permissions"]["packages"] == "read", job
    assert "mirror" in chain["gate"]["needs"]
    assert any(step.get("run") == "make mirror PUSH=yes" for step in chain["mirror"]["steps"])


def test_the_mirror_job_runs_whenever_a_job_that_pulls_from_it_does() -> None:
    # A job that needs a skipped one is skipped: the condition covers every family that pulls.
    chain = workflow("ci.yml")["jobs"]
    for job in PULLING_JOBS:
        assert f"needs.changes.outputs.{job} == 'true'" in chain["mirror"]["if"], job


@pytest.mark.parametrize("name", ["back.yml", "front.yml"])
def test_the_services_of_a_job_log_in_to_pull_the_mirror(name: str) -> None:
    jobs = workflow(name)["jobs"]
    services = [s for job in jobs.values() for s in job.get("services", {}).values()]
    assert services
    for service in services:
        assert service["image"].startswith(mirror.MIRROR)
        assert service["credentials"]["password"].endswith("secrets.GITHUB_TOKEN }}")
    assert workflow(name)["permissions"]["packages"] == "read"


def test_a_container_started_by_a_step_is_pulled_after_the_login() -> None:
    steps = workflow("back.yml")["jobs"]["tests"]["steps"]
    login = next(i for i, step in enumerate(steps) if "docker/login-action" in step.get("uses", ""))
    started = next(i for i, step in enumerate(steps) if "docker run" in step.get("run", ""))
    assert login < started


@pytest.mark.parametrize("name", ["front-image.yml", "keycloak.yml", "production.yml"])
def test_the_jobs_that_build_on_the_mirror_log_in_to_it(name: str) -> None:
    called = workflow(name)
    assert called["permissions"]["packages"] == "read"
    for job in called["jobs"].values():
        assert logs_in(job["steps"])


def test_images_yml_fills_the_mirror_and_reads_it_from_every_job() -> None:
    jobs = workflow("images.yml")["jobs"]
    assert any(step.get("run") == "make mirror PUSH=yes" for step in jobs["publish"]["steps"])
    assert jobs["cache"]["permissions"]["packages"] == "read"
    for job in ("publish", "trial", "cache"):
        assert logs_in(jobs[job]["steps"]), job


# The tool.


def test_an_image_the_mirror_holds_is_never_read_from_docker_hub() -> None:
    registry = Registry(INSPECTED, INSPECTED)
    assert registry.ensure([POSTGRES, MAILPIT]) == []
    assert registry.verbs() == ["inspect", "inspect"]
    assert all(command[-1].startswith(mirror.MIRROR) for command in registry.commands)


def test_an_image_the_mirror_lacks_is_copied_by_digest_then_checked() -> None:
    registry = Registry(NOT_FOUND, INSPECTED)
    assert registry.ensure([POSTGRES]) == [POSTGRES]
    assert registry.commands[1] == [
        "docker",
        "buildx",
        "imagetools",
        "create",
        "--tag",
        POSTGRES.tagged,
        POSTGRES.source,
    ]
    assert registry.verbs() == ["inspect", "create", "inspect"]


def test_a_package_not_yet_published_is_a_refusal_taken_for_a_missing_image() -> None:
    denied = (1, "requested access to the resource is denied")
    registry = Registry(denied, INSPECTED)
    assert registry.ensure([POSTGRES]) == [POSTGRES]


def test_docker_hub_that_does_not_give_an_image_fails_naming_it() -> None:
    registry = Registry(NOT_FOUND, copying=1)
    said = rf"^Docker Hub did not give docker\.io/library/postgres.*in {shared.ATTEMPTS} attempts"
    with pytest.raises(shared.ImageError, match=said):
        registry.ensure([POSTGRES])
    assert registry.verbs().count("create") == shared.ATTEMPTS
    assert registry.waits == [shared.PAUSE] * (shared.ATTEMPTS - 1)


def test_a_copy_that_does_not_keep_the_digest_is_said() -> None:
    registry = Registry(NOT_FOUND, NOT_FOUND)
    said = r"^ghcr\.io does not hold .* just copied from docker\.io"
    with pytest.raises(shared.ImageError, match=said):
        registry.ensure([POSTGRES])


def test_a_mirror_that_does_not_answer_fails_naming_ghcr_without_reading_docker_hub() -> None:
    registry = Registry(*[UNREACHABLE] * shared.ATTEMPTS)
    with pytest.raises(shared.ImageError, match=r"^ghcr\.io did not say whether it holds"):
        registry.ensure([POSTGRES])
    assert "create" not in registry.verbs()


def test_a_mirror_that_does_not_answer_once_is_asked_again() -> None:
    registry = Registry(UNREACHABLE, INSPECTED)
    assert registry.ensure([POSTGRES]) == []
    assert registry.waits == [shared.PAUSE]


def test_without_push_the_missing_images_are_said_and_nothing_is_copied() -> None:
    registry = Registry(NOT_FOUND)
    assert registry.ensure([POSTGRES], push=False) == [POSTGRES]
    assert registry.verbs() == ["inspect"]


def test_main_fills_the_mirror_of_the_files_it_reads(tmp_path: Path) -> None:
    dockerfile(tmp_path).write_text(
        f"FROM {mirror.MIRROR}/postgres:18-trixie@{DIGEST}\n", encoding="utf-8"
    )
    registry = Registry(NOT_FOUND, INSPECTED)
    assert registry.main(tmp_path, "--push") == 0
    assert registry.verbs() == ["inspect", "create", "inspect"]


def test_main_fails_on_a_missing_image_without_push_and_on_a_source_that_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dockerfile(tmp_path).write_text(
        f"FROM {mirror.MIRROR}/postgres:18-trixie@{DIGEST}\n", encoding="utf-8"
    )
    assert Registry(NOT_FOUND).main(tmp_path) == 1
    assert "make mirror PUSH=yes" in capsys.readouterr().err
    assert Registry(NOT_FOUND, copying=1).main(tmp_path, "--push") == 2
    assert "Docker Hub did not give" in capsys.readouterr().err


def test_main_fails_when_no_file_names_the_mirror(tmp_path: Path) -> None:
    assert Registry().main(tmp_path) == 2
