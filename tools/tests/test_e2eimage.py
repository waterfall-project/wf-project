# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work image of the end-to-end paths, and the chain that finds it or publishes it (US-1900).

The criterion of US-1900 this lot closes — no package of Ubuntu downloaded by a job of the paths,
which `archive.ubuntu.com` made fail six runs of the merge queue on 2026-11-11 (#2913), nor
Playwright's image pulled from its registry — is held here on what the repository says: the
workflows of the paths run in the work image or play in it, never install a package, and the image
carries the versions the repository asks for. That the chain then finds the image and plays the
paths in it is seen in its runs.
"""

import re
import tomllib
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, e2eimage

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOWS = REPOSITORY / ".github" / "workflows"
DOCKERFILE = e2eimage.CONTEXT / "Dockerfile"
DIGEST = "sha256:" + "a" * 64
INSPECTED = (
    0,
    f"Name: x\nMediaType: application/vnd.oci.image.index.v1+json\nDigest:    {DIGEST}\n",
)
NOT_FOUND = (1, "ERROR: ghcr.io/waterfall-project/e2e:0123: not found")
UNREACHABLE = (1, "ERROR: dial tcp: lookup ghcr.io: no such host")


def workflow(name: str) -> dict[Any, Any]:
    """Read a workflow."""
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def steps(name: str, job: str) -> list[dict[str, Any]]:
    """Return the steps of a job of a workflow."""
    return workflow(name)["jobs"][job]["steps"]


def dockerfile() -> str:
    """Read the Dockerfile of the image."""
    return DOCKERFILE.read_text(encoding="utf-8")


class Registry:
    """A registry that answers each inspection in turn, and records the commands it is given."""

    def __init__(self, *answers: tuple[int, str], failing: str | None = None) -> None:
        self.answers = list(answers)
        self.failing = failing
        self.commands: list[list[str]] = []

    def read(self, command: list[str]) -> tuple[int, str]:
        self.commands.append(command)
        return self.answers.pop(0)

    def run(self, command: list[str]) -> int:
        self.commands.append(command)
        return 1 if self.failing is not None and command[1] == self.failing else 0


# The workflows and the image.


def test_no_job_of_the_paths_installs_a_package_of_ubuntu() -> None:
    # The two ways #2913 failed: the package of make downloaded from archive.ubuntu.com, and the
    # system packages of the browser installed by make e2e-browsers.
    for name in ("e2e.yml", "service.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        for forbidden in ("archive.ubuntu.com", "apt-get", "dpkg", "e2e-browsers", "--with-deps"):
            assert forbidden not in text, f"{name} names {forbidden}"


def test_the_parts_of_the_paths_run_in_the_image_the_chain_found() -> None:
    chain = workflow("ci.yml")["jobs"]
    container = workflow("e2e.yml")["jobs"]["paths"]["container"]
    assert container["image"] == "${{ inputs.image }}"
    assert "credentials" in container
    for job in ("e2e", "service"):
        assert "e2e-image" in chain[job]["needs"]
        assert chain[job]["with"]["image"] == "${{ needs.e2e-image.outputs.image }}"
        assert chain[job]["permissions"]["packages"] == "read"


def test_the_image_is_found_or_published_before_the_paths_and_judged_by_the_gate() -> None:
    chain = workflow("ci.yml")["jobs"]
    job = chain["e2e-image"]
    assert job["permissions"]["packages"] == "write"
    assert any(step.get("run", "").startswith("make e2e-image PUSH=yes") for step in job["steps"])
    assert job["outputs"]["image"] == "${{ steps.image.outputs.image }}"
    # As the build of the front: whenever either kind of path runs.
    assert job["if"] == chain["front-build"]["if"]
    assert "e2e-image" in chain["gate"]["needs"]


def test_the_paths_against_the_service_play_in_the_image_pulled_first() -> None:
    found = steps("service.yml", "paths")
    pulled = next(i for i, step in enumerate(found) if "docker pull" in step.get("run", ""))
    played = next(i for i, step in enumerate(found) if step.get("run") == "make check-service")
    built = next(i for i, step in enumerate(found) if step.get("run") == "make build-keycloak")
    assert pulled < built < played
    assert found[played]["env"]["E2E_IMAGE"] == "${{ inputs.image }}"


def test_the_image_carries_the_python_of_the_tools() -> None:
    version = (REPOSITORY / "tools" / ".python-version").read_text(encoding="utf-8").strip()
    major_minor = ".".join(version.split(".")[:2])
    installed = re.findall(r"uv python install (\S+)", dockerfile())
    found = re.findall(r"uv python find --managed-python (\S+)\)", dockerfile())
    assert installed == [major_minor]
    assert found == [major_minor]


def test_the_image_carries_the_pnpm_the_front_names() -> None:
    package = (REPOSITORY / "frontend" / "package.json").read_text(encoding="utf-8")
    named = re.search(r'"packageManager":\s*"pnpm@([^"]+)"', package)
    assert named is not None
    assert re.findall(r"npm install --global pnpm@(\S+)", dockerfile()) == [named.group(1)]


def test_every_source_of_the_image_is_pinned() -> None:
    text = re.sub(r"\\\n", " ", dockerfile())
    for line in text.splitlines():
        if line.startswith("FROM "):
            assert re.search(r"@sha256:[0-9a-f]{64}\b", line), line
        if line.startswith("ADD ") and "://" in line:
            assert re.search(r"--checksum=sha256:[0-9a-f]{64}\b", line), line


def test_the_image_wakes_the_families_that_run_in_it() -> None:
    declaration = tomllib.loads((REPOSITORY / "tools" / "paths.toml").read_text(encoding="utf-8"))
    for family in ("front", "service"):
        paths = declaration["families"][family]["paths"]
        assert "deploy/e2e/**" in paths
        assert "tools/src/wftools/e2eimage.py" in paths


# The tag.


def test_the_tag_is_the_hash_of_the_directory(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
    first = e2eimage.tag(tmp_path)
    assert re.fullmatch(r"[0-9a-f]{16}", first)
    assert e2eimage.tag(tmp_path) == first
    (tmp_path / "Dockerfile").write_text("FROM y\n", encoding="utf-8")
    assert e2eimage.tag(tmp_path) != first


def test_a_file_added_to_the_directory_changes_the_tag(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
    first = e2eimage.tag(tmp_path)
    (tmp_path / "script.sh").write_text("", encoding="utf-8")
    assert e2eimage.tag(tmp_path) != first


def test_the_reference_names_the_image_of_the_organisation() -> None:
    assert e2eimage.reference().startswith("ghcr.io/waterfall-project/e2e:")


# Found, built, published.


def test_an_image_the_registry_holds_is_named_by_its_digest_and_not_built(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
    registry = Registry(INSPECTED)
    found = e2eimage.publish(push=True, run=registry.run, read=registry.read, context=tmp_path)
    assert found == f"{e2eimage.NAME}:{e2eimage.tag(tmp_path)}@{DIGEST}"
    assert [command[1] for command in registry.commands] == ["buildx"]


def test_a_missing_image_is_built_published_and_named_by_its_digest(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
    registry = Registry(NOT_FOUND, INSPECTED)
    found = e2eimage.publish(push=True, run=registry.run, read=registry.read, context=tmp_path)
    tagged = f"{e2eimage.NAME}:{e2eimage.tag(tmp_path)}"
    assert found == f"{tagged}@{DIGEST}"
    assert registry.commands[1] == ["docker", "build", "--tag", tagged, str(tmp_path)]
    assert registry.commands[2] == ["docker", "push", tagged]


def test_a_missing_image_built_without_push_is_named_by_its_tag(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
    registry = Registry(NOT_FOUND)
    found = e2eimage.publish(push=False, run=registry.run, read=registry.read, context=tmp_path)
    assert found == f"{e2eimage.NAME}:{e2eimage.tag(tmp_path)}"
    assert "push" not in [command[1] for command in registry.commands]


def test_a_package_the_registry_refuses_to_show_is_built_and_its_publication_says(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # ghcr.io answers 403 for a package it does not hold yet, which the first publication creates.
    refused = (1, "ERROR: failed to authorize: unexpected status from GET request: 403 Forbidden")
    registry = Registry(refused, failing="push")
    with pytest.raises(e2eimage.ImageError, match=r"publication of .* to ghcr\.io failed"):
        e2eimage.publish(push=True, run=registry.run, read=registry.read)
    assert [command[1] for command in registry.commands] == ["buildx", "build", "push"]
    assert "ghcr.io refused to show" in capsys.readouterr().err


def test_a_registry_that_does_not_answer_fails_naming_it() -> None:
    registry = Registry(UNREACHABLE)
    with pytest.raises(e2eimage.ImageError, match=r"^ghcr\.io did not say .*no such host"):
        e2eimage.publish(push=True, run=registry.run, read=registry.read)
    assert [command[1] for command in registry.commands] == ["buildx"]


@pytest.mark.parametrize(
    ("failing", "said"), [("build", "the build of"), ("push", "publication of .* to ghcr.io")]
)
def test_a_build_or_a_publication_that_fails_is_said(failing: str, said: str) -> None:
    registry = Registry(NOT_FOUND, failing=failing)
    with pytest.raises(e2eimage.ImageError, match=said):
        e2eimage.publish(push=True, run=registry.run, read=registry.read)


def test_a_publication_the_registry_does_not_then_hold_is_said() -> None:
    registry = Registry(NOT_FOUND, NOT_FOUND)
    with pytest.raises(e2eimage.ImageError, match=r"^ghcr\.io does not hold .*just published"):
        e2eimage.publish(push=True, run=registry.run, read=registry.read)


def test_a_registry_that_holds_the_tag_without_a_digest_is_said() -> None:
    registry = Registry((0, "Name: x\n"))
    with pytest.raises(e2eimage.ImageError, match="no digest"):
        e2eimage.publish(push=True, run=registry.run, read=registry.read)


def test_the_output_is_the_line_of_a_step(capsys: pytest.CaptureFixture[str]) -> None:
    registry = Registry(INSPECTED)
    assert e2eimage.main(["publish", "--push"], run=registry.run, read=registry.read) == 0
    assert capsys.readouterr().out == f"image={e2eimage.reference()}@{DIGEST}\n"


def test_a_failure_prints_nothing_on_the_output(capsys: pytest.CaptureFixture[str]) -> None:
    registry = Registry(UNREACHABLE)
    assert e2eimage.main(["publish", "--push"], run=registry.run, read=registry.read) == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert "ghcr.io did not say" in printed.err


# Played in the image.


def test_a_command_plays_in_the_image_on_the_network_of_the_host() -> None:
    directory = REPOSITORY / "frontend"
    command = e2eimage.run_command("image@sha256:x", ["pnpm", "exec", "playwright"], directory, {})
    assert command[:4] == ["docker", "run", "--rm", "--init"]
    assert command[command.index("--network") + 1] == "host"
    assert command[command.index("--ipc") + 1] == "host"
    assert command[command.index("--workdir") + 1] == str(directory)
    assert f"{REPOSITORY}:{REPOSITORY}" in command
    assert f"{e2eimage.SOCKET}:{e2eimage.SOCKET}" in command
    assert command[-4:] == ["image@sha256:x", "pnpm", "exec", "playwright"]


def test_the_variables_the_paths_read_are_passed_by_name_alone() -> None:
    environment = {
        "WATERFALL_REDIS_PASSWORD": "secret",
        "E2E_INSTALLATION_LINK": "https://x",
        "NODE_EXTRA_CA_CERTS": "/r/root.crt",
        "NEXT_TELEMETRY_DISABLED": "1",
        "CI": "true",
        "TZ": "UTC",
        "PATH": "/usr/bin",
        "HOME": "/home/runner",
        "PLAYWRIGHT_BROWSERS_PATH": "/elsewhere",
        "GITHUB_TOKEN": "token",
    }
    command = e2eimage.run_command("image", ["true"], REPOSITORY, environment)
    passed = [command[i + 1] for i, part in enumerate(command) if part == "--env"]
    assert passed == [
        "CI",
        "E2E_INSTALLATION_LINK",
        "NEXT_TELEMETRY_DISABLED",
        "NODE_EXTRA_CA_CERTS",
        "TZ",
        "WATERFALL_REDIS_PASSWORD",
    ]
    assert "secret" not in " ".join(command)


def test_a_directory_outside_the_checkout_is_refused(tmp_path: Path) -> None:
    with pytest.raises(e2eimage.ImageError, match="outside the checkout"):
        e2eimage.run_command("image", ["true"], tmp_path, {})


def test_main_plays_the_command_after_the_separator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(REPOSITORY / "frontend")
    played: list[list[str]] = []

    def play(command: list[str]) -> int:
        played.append(command)
        return 3

    code = e2eimage.main(
        ["run", "--image", "image", "--", "pnpm", "exec", "playwright", "test"],
        play=play,
        environment={"E2E_PART": "service"},
    )
    assert code == 3
    assert played[0][-5:] == ["image", "pnpm", "exec", "playwright", "test"]
    assert played[0][played[0].index("--env") :][:2] == ["--env", "E2E_PART"]


def test_main_without_a_command_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert e2eimage.main(["run", "--image", "image", "--"], play=lambda _: 0) == 2
    assert "no command" in capsys.readouterr().err
