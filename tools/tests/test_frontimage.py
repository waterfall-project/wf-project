# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The production image of the front, built and held at a pull request that changes it (US-0430).

The image itself is built and started by ``make check-front-image``; these tests hold what it
concludes from what Docker and the server answer, and when the chain asks for it. What a build of
the front prerendered is held without Docker too, on every change of the front
(``make prerendered-front``).
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from wftools import REPOSITORY, frontimage, paths

MANIFEST = json.dumps({"routes": {"/_global-error": {}, "/icon.svg": {}}, "dynamicRoutes": {}})
ADDRESS = "127.0.0.1:32768"


class Docker:
    """A Docker and a server that answer as a test tells them, and record what they are asked."""

    def __init__(
        self,
        *,
        manifest: str = MANIFEST,
        status: int | None = 200,
        stops: bool = True,
        says: bool = True,
    ) -> None:
        self.manifest = manifest
        self.status = status
        self.stops = stops
        self.says = says
        self.started: list[list[str]] = []
        self.removed: list[str] = []
        self.ran: list[list[str]] = []

    def run(self, command: list[str]) -> int:
        self.ran.append(command)
        return 0

    def environment(self, container: str) -> dict[str, str]:
        """Return the variables a container was started with."""
        command = self.started[int(container.removeprefix("container-")) - 1]
        pairs = [command[i + 1] for i, word in enumerate(command) if word == "-e"]
        return dict(pair.split("=", 1) for pair in pairs)

    def said(self, container: str) -> str:
        """Return what the server of a container writes to its logs."""
        environment = self.environment(container)
        if not self.says:
            return "Ready"
        if environment.get("WATERFALL_AUTH") == "mock":
            return f"Error: {frontimage.REFUSAL}"
        if missing := [name for name in frontimage.REQUIRED if name not in environment]:
            return f"Error: {', '.join(missing)} must be set"
        return "Ready"

    def read(self, command: list[str]) -> tuple[int, str]:
        if "--entrypoint" in command:
            return 0, self.manifest
        if command[:3] == ["docker", "run", "--detach"]:
            self.started.append(command)
            return 0, f"container-{len(self.started)}\n"
        if command[:2] == ["docker", "port"]:
            return 0, f"{ADDRESS}\n"
        if command[:2] == ["docker", "inspect"]:
            return 0, "false 1\n" if self.stops else "true 0\n"
        if command[:2] == ["docker", "logs"]:
            return 0, self.said(command[-1])
        if command[:3] == ["docker", "rm", "--force"]:
            self.removed.append(command[-1])
        return 0, ""

    def fetch(self, host: str, port: int) -> int | None:
        assert f"{host}:{port}" == ADDRESS
        return self.status


@pytest.mark.requirement("WF-SEC-0010-A")
def test_an_image_that_starts_with_its_settings_alone_and_refuses_the_fake_back_passes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Docker()
    assert frontimage.main([], docker.run, docker.read, docker.fetch) == 0
    assert docker.ran == [
        ["docker", "build", "--target", "production", "--tag", frontimage.IMAGE, "frontend"]
    ]
    started = [docker.environment(f"container-{i + 1}") for i in range(len(docker.started))]
    assert started[0] == frontimage.SETTINGS
    assert [set(frontimage.SETTINGS) - set(each) for each in started[1:-1]] == [
        {name} for name in frontimage.REQUIRED
    ]
    assert started[-1] == {**frontimage.SETTINGS, "WATERFALL_AUTH": "mock"}
    assert docker.removed == [f"container-{i + 1}" for i in range(len(docker.started))]
    output = capsys.readouterr().out
    assert "/ answers 200 with the settings of the production Compose" in output
    assert "without WATERFALL_REDIS_URL, the front stops naming it" in output
    assert "WATERFALL_AUTH=mock without WATERFALL_E2E is refused" in output


@pytest.mark.parametrize(
    ("docker", "said"),
    [
        (
            Docker(manifest=json.dumps({"routes": {"/icon.svg": {}, "/login": {}}})),
            "next build prerendered /login",
        ),
        (Docker(manifest="{"), "the prerender manifest does not read"),
        (Docker(status=500), "/ answered 500 with the settings of the production Compose"),
        (
            Docker(says=False),
            (
                "without WATERFALL_KEYCLOAK_ADDRESS: the front stopped (1) without saying "
                "WATERFALL_KEYCLOAK_ADDRESS"
            ),
        ),
    ],
)
def test_an_image_that_does_not_do_what_it_must_fails_naming_it(
    docker: Docker, said: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert frontimage.main([], docker.run, docker.read, docker.fetch) == 1
    assert said in capsys.readouterr().err
    assert len(docker.removed) == len(docker.started)


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_front_that_starts_without_a_secret_fails_the_check_and_its_container_is_removed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    docker = Docker(stops=False)
    with pytest.raises(frontimage.FrontImageError, match="did not stop within 0 s"):
        frontimage.stop(docker.read, {}, wait=0)
    assert docker.removed == ["container-1"]
    monkeypatch.setattr(frontimage, "WAIT", 0.0)
    assert frontimage.main([], docker.run, docker.read, docker.fetch) == 1
    said = "without WATERFALL_KEYCLOAK_ADDRESS: the front did not stop within 0 s"
    assert said in capsys.readouterr().err
    assert len(docker.removed) == len(docker.started)


def test_a_front_that_never_answers_fails_and_its_container_is_removed() -> None:
    docker = Docker(status=None)
    with pytest.raises(frontimage.FrontImageError, match="did not answer"):
        frontimage.answer(docker.read, docker.fetch, {}, wait=0)
    assert docker.removed == ["container-1"]


def test_a_build_that_fails_stops_the_check() -> None:
    docker = Docker()
    assert frontimage.main([], lambda _command: 2, docker.read, docker.fetch) == 2
    assert docker.started == []


@pytest.mark.parametrize(
    ("manifest", "code", "said"),
    [
        (MANIFEST, 0, "prerendered: /_global-error, /icon.svg alone"),
        (json.dumps({"routes": {"/icon.svg": {}, "/": {}}}), 1, "next build prerendered /"),
        (None, 1, "(No such file or directory): build the front first (make build-front)"),
    ],
)
def test_the_manifest_of_a_build_on_the_checkout_is_held_without_docker(
    tmp_path: Path,
    manifest: str | None,
    code: int,
    said: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    written = tmp_path / "prerender-manifest.json"
    if manifest is not None:
        written.write_text(manifest, encoding="utf-8")
    docker = Docker()
    assert (
        frontimage.main(["--manifest", str(written)], docker.run, docker.read, docker.fetch) == code
    )
    assert docker.ran == []
    assert docker.started == []
    output = capsys.readouterr()
    assert said in (output.out if code == 0 else output.err)


def dry_run(target: str, tier: str, *variables: str) -> list[str]:
    """Return the commands make would run for a target in a tier, without running them."""
    result = subprocess.run(
        ["make", "--dry-run", "--no-print-directory", target, f"TIER={tier}", *variables],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


@pytest.mark.parametrize(("tier", "build"), [("fast", "pnpm build"), ("full", "playwright test")])
def test_a_change_of_a_page_holds_what_the_build_of_the_front_prerendered(
    tier: str, build: str
) -> None:
    # The layout reads the cookies, which keeps every page from being prerendered: a change of it,
    # or of any page, wakes the front family, whose check holds the manifest after the build.
    families = paths.read().touched(["frontend/src/app/layout.tsx"])
    assert "check-front" in {family.target for family in families}
    commands = dry_run("check-front", tier)
    built = [i for i, command in enumerate(commands) if build in command]
    held = [i for i, command in enumerate(commands) if "frontimage --manifest" in command]
    assert built
    assert held
    assert held[0] > built[0]
    assert commands[held[0]].endswith("frontend/.next/prerender-manifest.json")


def test_a_part_of_the_paths_alone_builds_nothing_and_holds_no_manifest_left_behind() -> None:
    commands = dry_run("check-front-e2e", "full", "SHARD=1/3")
    assert any("playwright test --shard=1/3" in command for command in commands)
    assert not [command for command in commands if "frontimage --manifest" in command]


def test_the_chain_holds_what_the_build_of_the_measure_prerendered() -> None:
    workflow = yaml.safe_load((REPOSITORY / ".github" / "workflows" / "e2e.yml").read_text())
    measured = [
        step["run"]
        for step in workflow["jobs"]["paths"]["steps"]
        if step.get("if") == "matrix.part == 'measure'"
    ]
    assert measured == ["make e2e-measure", "make prerendered-front"]


def test_a_change_of_what_makes_the_image_wakes_its_check() -> None:
    declaration = paths.read()
    for changed in (
        "frontend/Dockerfile",
        "frontend/next.config.ts",
        "frontend/pnpm-lock.yaml",
        "frontend/src/instrumentation.ts",
        "frontend/src/startup.ts",
    ):
        assert "front-image" in {family.name for family in declaration.touched([changed])}


def test_the_chain_runs_the_check_and_the_gate_judges_it() -> None:
    chain = yaml.safe_load((REPOSITORY / ".github" / "workflows" / "ci.yml").read_text())
    job = chain["jobs"]["front-image"]
    assert job["if"] == "needs.changes.outputs.front-image == 'true'"
    assert "front-image" in chain["jobs"]["gate"]["needs"]
    workflow = yaml.safe_load(
        (REPOSITORY / ".github" / "workflows" / "front-image.yml").read_text()
    )
    assert workflow["jobs"]["check"]["steps"][-1] == {"run": "make check-front-image"}
