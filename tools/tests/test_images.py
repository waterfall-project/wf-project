# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The images the chain publishes, and what they must not hold (US-0430).

The criterion of US-0430 on the images — the chain builds and publishes those of the front, of the
API and the worker, one image of several commands, and that of Keycloak with its extension, on
ghcr.io, tagged by version and by commit of main, and by commit of an epic branch; no image holds a
secret — is held here on what the repository says: the workflow, the commands it runs, and the
Dockerfiles. The publication itself is seen in the registry, after a merge.
"""

import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, images

WORKFLOW = REPOSITORY / ".github" / "workflows" / "images.yml"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
VERSION = images.version()
# A name that says it holds a secret, in a build argument or a variable an image sets.
SECRET_NAME = re.compile(r"PASSWORD|SECRET|TOKEN|CREDENTIAL|KEY", re.IGNORECASE)
# The keys of the realm that hold a secret, whose value must come from the environment.
SECRET_KEYS = frozenset({"secret", "clientSecret", "bindCredential", "password", "value"})
SUBSTITUTED = re.compile(r"\$\(env:[A-Z0-9_]+\)")


def workflow() -> dict[Any, Any]:
    """Read the workflow of the images; YAML reads its key `on` as true."""
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def built(branch: str, *, push: bool = False) -> dict[str, list[str]]:
    """Return, by image, the references each build of a branch tags."""
    found: dict[str, list[str]] = {}
    for command in images.commands(branch, COMMIT, VERSION, push=push):
        if command[:2] == ["docker", "build"]:
            references = [command[i + 1] for i, word in enumerate(command) if word == "--tag"]
            found[command[-1]] = references
    return found


def stages(dockerfile: Path) -> list[list[str]]:
    """Return the instructions of each stage of a Dockerfile, continuation lines joined."""
    text = re.sub(r"\\\n", " ", dockerfile.read_text(encoding="utf-8"))
    found: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.upper().startswith("FROM "):
            found.append([])
        if found:
            found[-1].append(line.strip())
    return found


def dockerfiles() -> list[Path]:
    """Return the Dockerfile of each published image."""
    return [REPOSITORY / image.context / "Dockerfile" for image in images.IMAGES]


def test_the_chain_publishes_at_each_push_to_main_or_to_an_epic_branch_alone() -> None:
    triggers = workflow()[True]
    assert triggers == {"push": {"branches": ["main", "epic/**"]}}


def test_the_job_that_publishes_alone_writes_packages_and_runs_the_makefile() -> None:
    document = workflow()
    assert document["permissions"] == {"contents": "read"}
    jobs = document["jobs"]
    assert list(jobs) == ["publish"]
    job = jobs["publish"]
    assert job["permissions"] == {"contents": "read", "packages": "write"}
    publish = job["steps"][-1]
    assert publish["run"] == "make images PUSH=yes"
    assert publish["env"] == {
        "IMAGE_BRANCH": "${{ github.ref_name }}",
        "IMAGE_COMMIT": "${{ github.sha }}",
    }


def test_every_action_of_the_workflow_is_pinned_by_the_digest_of_its_commit() -> None:
    for step in workflow()["jobs"]["publish"]["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", step["uses"])


def test_main_publishes_the_three_images_by_commit_by_branch_and_by_version() -> None:
    assert built("main") == {
        context: [f"ghcr.io/waterfall-project/{name}:{tag}" for tag in (COMMIT, "main", VERSION)]
        for name, context in (
            ("front", "frontend"),
            ("waterfall", "backend"),
            ("keycloak", "deploy/keycloak"),
        )
    }


def test_an_epic_branch_publishes_them_by_commit_and_by_branch_never_by_version() -> None:
    for references in built("epic/EP-03").values():
        tags = [reference.rsplit(":", 1)[1] for reference in references]
        assert tags == [COMMIT, "epic-EP-03"]


def test_every_tag_of_every_image_is_pushed_after_its_build() -> None:
    planned = images.commands("main", COMMIT, VERSION, push=True)
    pushed = [command[2] for command in planned if command[:2] == ["docker", "push"]]
    assert pushed == [tag for references in built("main").values() for tag in references]
    assert planned[0][:2] == ["docker", "build"]
    assert planned[1][:2] == ["docker", "push"]


@pytest.mark.parametrize("branch", ["lot/US-0430/L1", "feature", "mainline", "epic/"])
def test_nothing_is_published_from_a_branch_other_than_main_or_an_epic(branch: str) -> None:
    with pytest.raises(images.ImageError, match="main or epic"):
        images.commands(branch, COMMIT, VERSION, push=True)
    assert images.commands(branch, COMMIT, VERSION, push=False)


def test_no_image_receives_a_secret_at_its_build() -> None:
    for command in images.commands("main", COMMIT, VERSION, push=True):
        assert not {"--build-arg", "--secret", "--ssh", "--env"} & set(command)
    for dockerfile in dockerfiles():
        for stage in stages(dockerfile):
            for instruction in stage:
                keyword, _, rest = instruction.partition(" ")
                assert keyword.upper() != "ARG", f"{dockerfile}: {instruction}"
                if keyword.upper() == "ENV":
                    names = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=", rest)
                    assert not [name for name in names if SECRET_NAME.search(name)]


def test_the_token_that_publishes_is_given_to_the_login_alone() -> None:
    steps = workflow()["jobs"]["publish"]["steps"]
    holding = [step for step in steps if "secrets." in json.dumps(step)]
    assert [step["uses"].split("@")[0] for step in holding] == ["docker/login-action"]


def test_each_image_is_the_last_stage_of_its_dockerfile_and_never_runs_as_root() -> None:
    for dockerfile in dockerfiles():
        last = stages(dockerfile)[-1]
        assert last[0].endswith(f" AS {images.STAGE}"), dockerfile
        users = [line.split()[1] for line in last if line.upper().startswith("USER ")]
        assert not [user for user in users if user.split(":")[0] in {"root", "0"}], dockerfile
    for context in ("frontend", "backend"):
        last = stages(REPOSITORY / context / "Dockerfile")[-1]
        assert [line for line in last if line.startswith("USER ")][-1] == "USER 1000:1000"


def test_nothing_of_the_workstation_enters_the_context_of_the_front_and_of_the_back() -> None:
    for context in ("frontend", "backend"):
        ignored = (REPOSITORY / context / ".dockerignore").read_text(encoding="utf-8").splitlines()
        assert ".env*" in ignored
        assert ".venv" in ignored or "node_modules" in ignored


def secrets_of(node: object, key: str = "") -> list[object]:
    """Return every value a key of the realm that names a secret holds, however deep."""
    if isinstance(node, dict):
        mapping = cast("dict[str, object]", node)
        return [found for name, value in mapping.items() for found in secrets_of(value, name)]
    if isinstance(node, list):
        return [found for item in cast("list[object]", node) for found in secrets_of(item, key)]
    return [node] if key in SECRET_KEYS else []


def test_the_realm_of_the_image_holds_no_secret_and_nothing_of_the_development_platform() -> None:
    keycloak = REPOSITORY / "deploy" / "keycloak"
    assert "development" in (keycloak / ".dockerignore").read_text(encoding="utf-8").splitlines()
    files = sorted((keycloak / "realm").glob("*.yaml"))
    assert [path.name for path in files] == ["waterfall.yaml"]
    text = files[0].read_text(encoding="utf-8")
    realm: dict[str, Any] = yaml.safe_load(text)
    secrets = secrets_of(realm)
    assert secrets
    assert all(isinstance(value, str) and SUBSTITUTED.fullmatch(value) for value in secrets)
    # No test account, no directory federated, no external provider: an installation connects its
    # own in the console; and nothing that names the services or the values of the development.
    assert not {"identityProviders", "components"} & set(realm)
    assert all("credentials" not in user for user in realm["users"])
    assert not re.search(r"mailpit|openldap|development|\.test\b", text, re.IGNORECASE)


def test_a_secret_written_in_the_realm_is_found() -> None:
    realm = {"clients": [{"secret": "development-only"}], "users": [{"credentials": ["x"]}]}
    assert secrets_of(realm) == ["development-only"]
    assert not SUBSTITUTED.fullmatch("development-only")


def test_the_front_carries_the_version_that_tags_a_release() -> None:
    package = json.loads((REPOSITORY / "frontend" / "package.json").read_text(encoding="utf-8"))
    with (REPOSITORY / "backend" / "pyproject.toml").open("rb") as file:
        assert package["version"] == tomllib.load(file)["project"]["version"] == VERSION


@pytest.mark.parametrize(
    ("branch", "tag"),
    [
        ("main", "main"),
        ("epic/EP-03", "epic-EP-03"),
        ("epic/EP-03+demo", "epic-EP-03-demo"),
        ("-x", "x"),
        ("a" * 200, "a" * 128),
    ],
)
def test_a_branch_is_made_a_valid_tag(branch: str, tag: str) -> None:
    assert images.branch_tag(branch) == tag


def test_a_branch_that_makes_no_tag_is_refused() -> None:
    with pytest.raises(images.ImageError, match="makes no tag"):
        images.branch_tag("-/.")


@pytest.mark.parametrize("commit", ["0123456", COMMIT.upper(), COMMIT + "0", ""])
def test_a_commit_other_than_a_full_hash_is_refused(commit: str) -> None:
    with pytest.raises(images.ImageError, match="full hash"):
        images.tags("main", commit, VERSION)


def test_a_version_that_makes_no_tag_is_refused() -> None:
    with pytest.raises(images.ImageError, match="version"):
        images.tags("main", COMMIT, "1.0.0+local")


def test_the_images_are_built_from_the_branch_and_the_commit_the_chain_names(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run: list[list[str]] = []
    environment = {"IMAGE_BRANCH": "epic/EP-03", "IMAGE_COMMIT": COMMIT}
    assert images.main(["--push"], environment, lambda command: run.append(command) or 0) == 0
    assert run == images.commands("epic/EP-03", COMMIT, VERSION, push=True)
    assert f"--tag ghcr.io/waterfall-project/front:{COMMIT}" in capsys.readouterr().out


def test_the_first_command_that_fails_stops_the_rest() -> None:
    run: list[list[str]] = []
    environment = {"IMAGE_BRANCH": "main", "IMAGE_COMMIT": COMMIT}
    assert images.main([], environment, lambda command: run.append(command) or 3) == 3
    assert len(run) == 1


def test_a_push_refused_says_why_and_runs_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    run: list[list[str]] = []
    environment = {"IMAGE_BRANCH": "lot/US-0430/L1", "IMAGE_COMMIT": COMMIT}
    assert images.main(["--push"], environment, lambda command: run.append(command) or 0) == 2
    assert run == []
    assert "not from 'lot/US-0430/L1'" in capsys.readouterr().err


def test_without_the_chain_the_branch_and_the_commit_are_those_of_the_checkout() -> None:
    run: list[list[str]] = []
    assert images.main([], {}, lambda command: run.append(command) or 0) == 0
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert len(run) == len(images.IMAGES)
    for command in run:
        assert command[command.index("--tag") + 1].endswith(f":{head}")
