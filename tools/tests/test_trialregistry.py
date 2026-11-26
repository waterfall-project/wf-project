# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The registry of the trial of the production platform, and the images it runs from it (US-2800).

The Compose of production designates each image by its digest (#3726). An image built here and never
pushed has none a Docker of the classic store knows, and the commit of a pull request is not on
ghcr.io: the trial pushes the three images to a registry that lives for the run, reads the digest
each push says, and starts the platform from it by those digests.
"""

import os
import re
import shutil
import subprocess

import pytest
import yaml
from test_production import GIVEN, Docker, FakePlatform, platform_sender, realm_routes
from test_restoretest import STAND_IN
from test_supervision import GIVEN_DIGESTS, PUSHED, TAG

from wftools import REPOSITORY, images, production, trialregistry
from wftools.images import IMAGES

pytestmark = pytest.mark.story("US-2800")

ADDRESS = "localhost:32793"
LOCATION = f"{ADDRESS}/waterfall-project"
README = REPOSITORY / "deploy" / "compose" / "README.md"
EXPLOITATION = REPOSITORY / "docs" / "exploitation" / "postgresql-fourni.md"
IMAGES_WORKFLOW = REPOSITORY / ".github" / "workflows" / "images.yml"
RESTORE_TEST = REPOSITORY / "deploy" / "compose" / "compose.restore-test.yaml"
BUILT = {**GIVEN, **dict.fromkeys(GIVEN_DIGESTS, "")}


class Registry(Docker):
    """A Docker that also answers the registry of the trial: its port, and what each push says."""

    def __init__(self, *, refusing: str = "", said: str = "127.0.0.1:32793\n") -> None:
        super().__init__()
        self.refusing = refusing
        self.said = said

    def read(self, command: list[str]) -> tuple[int, str]:
        if command[:2] == ["docker", "tag"]:
            self.ran.append(command)
            return (1, "No such image") if self.refusing == "tag" else (0, "")
        if command[:2] == ["docker", "push"]:
            self.ran.append(command)
            name = command[-1].rsplit("/", 1)[1].split(":", 1)[0]
            if self.refusing == "push":
                return 1, "denied: requested access to the resource is denied\n"
            if self.refusing == "silence":
                return 0, "The push refers to repository\n"
            return 0, f"The push refers to repository\n{TAG}: digest: {PUSHED[name]} size: 856\n"
        if "port" in command:
            self.ran.append(command)
            return 0, self.said
        return super().read(command)

    def registry_commands(self) -> list[str]:
        """Return the verb of each command that concerns the registry of the trial."""
        found: list[str] = []
        for command in self.ran:
            if str(trialregistry.COMPOSE) in command:
                found.append(next(word for word in command if word in ("up", "port", "down")))
            elif command[:2] in (["docker", "tag"], ["docker", "push"]):
                found.append(command[1])
        return found


def test_the_registry_of_the_trial_is_a_service_reachable_from_the_machine_alone() -> None:
    service = yaml.safe_load(trialregistry.COMPOSE.read_text(encoding="utf-8"))["services"]
    registry = service["registry"]
    assert registry["ports"] == [f"127.0.0.1::{trialregistry.PORT}"]
    assert re.search(r"registry:[\d.]+@sha256:[0-9a-f]{64}$", registry["image"])
    assert registry["image"].startswith("${WATERFALL_MIRROR:-}")


def test_a_registry_started_gives_the_address_docker_reaches_it_at() -> None:
    docker = Registry()
    assert trialregistry.start(docker.run, docker.read) == ADDRESS
    assert docker.ran[0][-4:] == ["up", "--detach", "--wait", "--quiet-pull"]
    assert docker.ran[1][-3:] == ["port", "registry", "5000"]


@pytest.mark.parametrize("said", ["", "nothing here", "0.0.0.0:abc"])
def test_a_registry_that_gives_no_port_is_said(said: str) -> None:
    docker = Registry(said=said)
    with pytest.raises(trialregistry.RegistryError, match="gives no port"):
        trialregistry.start(docker.run, docker.read)


def test_a_registry_that_does_not_start_is_said() -> None:
    docker = Registry()
    docker.up = 1
    with pytest.raises(trialregistry.RegistryError, match="does not start"):
        trialregistry.start(docker.run, docker.read)


def test_each_image_of_the_tag_is_pushed_and_named_by_the_digest_its_push_says() -> None:
    docker = Registry()
    assert trialregistry.publish(TAG, ADDRESS, docker.read) == PUSHED
    assert docker.ran == [
        command
        for image in IMAGES
        for command in (
            [
                "docker",
                "tag",
                f"ghcr.io/waterfall-project/{image.name}:{TAG}",
                f"{LOCATION}/{image.name}:{TAG}",
            ],
            ["docker", "push", f"{LOCATION}/{image.name}:{TAG}"],
        )
    ]


def test_an_image_not_built_here_says_to_build_it_or_to_give_the_digests() -> None:
    docker = Registry(refusing="tag")
    with pytest.raises(trialregistry.RegistryError, match=r"not built here: make images first"):
        trialregistry.publish(TAG, ADDRESS, docker.read)


def test_a_push_the_registry_refuses_is_said_with_its_reason() -> None:
    docker = Registry(refusing="push")
    with pytest.raises(trialregistry.RegistryError, match=r"does not take .*/front:.*: denied"):
        trialregistry.publish(TAG, ADDRESS, docker.read)


def test_a_push_that_says_no_digest_is_said() -> None:
    docker = Registry(refusing="silence")
    with pytest.raises(trialregistry.RegistryError, match=r"does not take .*/front:"):
        trialregistry.publish(TAG, ADDRESS, docker.read)


def test_the_registry_is_removed_with_what_it_holds() -> None:
    docker = Registry()
    trialregistry.stop(docker.run)
    assert docker.ran[0][-2:] == ["down", "--volumes"]


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
@pytest.mark.unexecuted("skipped where docker is not installed")
def test_the_compose_reads_the_images_from_the_registry_the_trial_names_by_their_digests() -> None:
    # The same file, the registry of the trial in place of ghcr.io, each image still by its digest.
    docker = Registry()
    added, pushed = production.local_images(
        {"WATERFALL_IMAGE_TAG": TAG}, TAG, docker.run, docker.read
    )
    assert added == {"WATERFALL_REGISTRY": LOCATION}
    assert pushed == PUSHED
    found = {
        **STAND_IN,
        **added,
        "WATERFALL_DIGEST_WATERFALL": PUSHED["waterfall"],
        "WATERFALL_DIGEST_KEYCLOAK": PUSHED["keycloak"],
    }
    config = subprocess.run(
        [
            *("docker", "compose", "-f", str(RESTORE_TEST), "--profile", "restore-test"),
            *("config", "--images"),
        ],
        env={**os.environ, **found},
        capture_output=True,
        text=True,
        check=False,
    )
    assert config.returncode == 0, config.stderr
    named = set(config.stdout.split())
    for name in ("waterfall", "keycloak"):
        assert f"{LOCATION}/{name}@{PUSHED[name]}" in named
    assert not [line for line in named if line.startswith("ghcr.io/waterfall")]


def test_digests_given_leave_the_trial_to_ghcr_and_start_no_registry() -> None:
    docker = Registry()
    assert production.local_images(GIVEN, TAG, docker.run, docker.read) == ({}, {})
    assert docker.ran == []


def test_the_trial_on_images_built_here_runs_them_from_its_registry_and_removes_it() -> None:
    docker = Registry()
    fake = FakePlatform(realm_routes())
    assert production.main(BUILT, docker.run, docker.read, platform_sender(fake)) == 0
    assert docker.registry_commands() == ["up", "port", *["tag", "push"] * 3, "down"]
    up = next(
        index
        for index, command in enumerate(docker.ran)
        if command[-4:] == ["up", "--detach", "--wait", "--quiet-pull"]
        and str(production.FILES[0]) in command
    )
    # The registry is up before the platform and removed after it.
    assert str(trialregistry.COMPOSE) in docker.ran[0]
    assert str(trialregistry.COMPOSE) in docker.ran[-1]
    assert 0 < up < len(docker.ran) - 1


def test_a_push_refused_stops_the_trial_before_the_platform_and_removes_the_registry(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Registry(refusing="push")
    assert production.main(BUILT, docker.run, docker.read, platform_sender(FakePlatform({}))) == 1
    assert docker.registry_commands() == ["up", "port", "tag", "push", "down"]
    assert not [c for c in docker.ran if str(production.FILES[0]) in c]
    assert "does not take" in capsys.readouterr().err


def test_images_not_built_here_stop_the_trial_naming_the_remedy(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Registry(refusing="tag")
    assert production.main(BUILT, docker.run, docker.read, platform_sender(FakePlatform({}))) == 1
    assert docker.registry_commands() == ["up", "port", "tag", "down"]
    assert "make images first" in capsys.readouterr().err


def test_the_documentation_says_where_an_operator_finds_the_digests_of_a_version() -> None:
    # The artifact of the publication, which expires and asks for a session of GitHub, and else the
    # registry read by the tag of the version, once, to be checked: for the Compose and the chart.
    workflow = yaml.safe_load(IMAGES_WORKFLOW.read_text(encoding="utf-8"))
    kept = workflow["jobs"]["publish"]["steps"][-1]["with"]["name"]
    command = "docker buildx imagetools inspect ghcr.io/waterfall-project/$image:"
    for document, written in ((README, images.ENVIRONMENT), (EXPLOITATION, images.VALUES)):
        text = document.read_text(encoding="utf-8")
        assert f"`{kept}`" in text, document
        assert written in text, document
        assert "90 jours" in text, document
        assert command in text, document
        assert "--format '{{.Manifest.Digest}}'" in text, document
        assert "for image in front waterfall keycloak" in text, document
        assert "par l'étiquette" in text, document
    assert [image.name for image in IMAGES] == ["front", "waterfall", "keycloak"]


def test_the_documentation_says_what_a_volume_that_takes_no_group_asks_of_an_installation() -> None:
    text = EXPLOITATION.read_text(encoding="utf-8")
    for word in ("fsGroup", "OnRootMismatch", "hostPath", "local", "NFS", "chown -R 1000:1000"):
        assert word in text, word
