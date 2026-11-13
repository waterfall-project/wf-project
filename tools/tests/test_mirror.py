# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mirror of the images of Docker Hub, and the jobs that pull from it (US-1900).

The criterion of US-1900 this lot closes — the pull of Docker Hub (« failed to fetch oauth token »)
no longer fails a run — is held here on what the repository says: no file the chain pulls from
names an image of Docker Hub bare (outside the chain they stay Docker Hub's by default), the mirror
is filled before the jobs that pull from it, and an image neither the mirror nor Docker Hub gives
fails the run naming the source. That the runs of the chain then pass when Docker Hub does not
answer is seen in the queue (``make queue-report``).
"""

import re
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, images, mirror
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
# The families whose jobs pull from the mirror.
PULLING_JOBS = ("back", "front", "front-image", "keycloak", "production", "service")
# The workflows that build or run Compose on the mirror, and so pose its prefix.
BUILDING = (
    "back.yml",
    "front-image.yml",
    "keycloak.yml",
    "images.yml",
    "production.yml",
    "service.yml",
)


class Registry:
    """A registry that answers each inspection in turn, and records the commands and the waits.

    ``copying`` is the code of the copy from Docker Hub: 0, or that of its failure, with what the
    tool said in ``said``.
    """

    def __init__(self, *answers: tuple[int, str], copying: int = 0, said: str = "") -> None:
        self.answers = list(answers)
        self.copying = copying
        self.said = said
        self.commands: list[list[str]] = []
        self.waits: list[float] = []

    def read(self, command: list[str]) -> tuple[int, str]:
        self.commands.append(command)
        if command[3] == "create":
            return self.copying, self.said
        return self.answers.pop(0)

    def wait(self, seconds: float) -> None:
        self.waits.append(seconds)

    def ensure(self, images: list[mirror.Mirrored], *, push: bool = True) -> list[mirror.Mirrored]:
        """Make sure the mirror holds the images, through this registry, waiting for nothing."""
        return mirror.ensure(images, push=push, read=self.read, wait=self.wait)

    def main(self, root: Path, *arguments: str) -> int:
        """Play the tool on the files of a directory."""
        return mirror.main(list(arguments), self.read, self.wait, root)

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


def test_outside_the_chain_the_files_name_docker_hub_by_default() -> None:
    # Compose and the Dockerfiles read the mirror from WATERFALL_MIRROR, empty by default: the
    # workstation, production, the demonstration and Dependabot see Docker Hub's names.
    for path in scanned():
        text = path.read_text(encoding="utf-8")
        if path.parent.name == "workflows":
            continue
        name = str(path.relative_to(REPOSITORY))
        assert mirror.MIRROR not in text, name
        if "WATERFALL_MIRROR" in text and path.suffix == ".yaml":
            assert "${WATERFALL_MIRROR}" not in text, name
        elif "WATERFALL_MIRROR" in text:
            assert "\nARG WATERFALL_MIRROR=\n" in text, name
    # Production and the demonstration stay on Docker Hub too: the chain alone poses the variable.
    prod = (REPOSITORY / "deploy" / "compose" / "compose.prod.yaml").read_text(encoding="utf-8")
    assert "${WATERFALL_MIRROR:-}postgres:" in prod
    assert mirror.MIRROR not in prod
    demo = REPOSITORY / "deploy" / "compose" / "compose.demo.yaml"
    assert "MIRROR" not in demo.read_text(encoding="utf-8")


BARE = re.compile(
    r"^\s*(?:image:\s*|FROM\s+(?:--platform=\S+\s+)?)"
    r"(?![^/\s]*\.[^/\s]*/|\$\{WATERFALL_MIRROR|ghcr\.io/|\*|waterfall-|\$\{|[a-z-]+\s+AS\b)"
    r"(?P<name>[a-z0-9./_-]+:[^\s@]+@sha256:\S+)",
    re.MULTILINE,
)


def test_a_file_the_chain_pulls_from_names_no_image_of_docker_hub_bare() -> None:
    # A bare image added later would be pulled from Docker Hub by the chain: caught here.
    # compose.demo.yaml and the production files' defaults are not in the chain's reach.
    for path in scanned():
        if path.name == "compose.demo.yaml" or path.parent.name == "workflows":
            continue
        assert not BARE.findall(path.read_text(encoding="utf-8")), str(path.relative_to(REPOSITORY))


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
        "FROM ${WATERFALL_MIRROR}node:26-alpine\n"
        f"image: ${{WATERFALL_MIRROR:-}}redis:8@{DIGEST}\n",
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


@pytest.mark.parametrize("name", BUILDING)
def test_the_workflows_that_build_on_the_mirror_pose_it_and_log_in_to_it(name: str) -> None:
    called = workflow(name)
    assert called["env"]["WATERFALL_MIRROR"] == f"{mirror.MIRROR}/"
    assert any(logs_in(job["steps"]) for job in called["jobs"].values())


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


def test_a_copy_ghcr_refuses_is_not_blamed_on_docker_hub() -> None:
    said = "ERROR: failed to push ghcr.io/waterfall-project/mirror/postgres: denied"
    registry = Registry(NOT_FOUND, copying=1, said=said)
    with pytest.raises(shared.ImageError, match=r"^ghcr\.io refused to write"):
        registry.ensure([POSTGRES])
    assert registry.verbs().count("create") == 1


def test_main_without_a_login_says_ghcr_refused_to_answer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dockerfile(tmp_path).write_text(
        f"FROM {mirror.MIRROR}/postgres:18-trixie@{DIGEST}\n", encoding="utf-8"
    )
    assert Registry((1, "requested access to the resource is denied")).main(tmp_path) == 1
    assert "refused to answer" in capsys.readouterr().err


def test_main_fails_when_no_file_names_the_mirror(tmp_path: Path) -> None:
    assert Registry().main(tmp_path) == 2


def test_every_build_of_an_image_hands_the_registry_of_the_mirror_down() -> None:
    builds = images.builds("main", "a" * 40, "0.3.0")
    assert builds
    assert all("--build-arg" in command and "WATERFALL_MIRROR" in command for command in builds)
