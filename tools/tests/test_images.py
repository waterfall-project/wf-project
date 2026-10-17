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
from collections.abc import Iterable, Mapping
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
# The options of a build that would hand it a value, in either form: `--build-arg X=…`,
# `--build-arg=X=…`.
SECRET_OPTIONS = ("--build-arg", "--secret", "--ssh", "--env")
NAMES = ("front", "waterfall", "keycloak")
NOT_FOUND = (1, "ERROR: ghcr.io/waterfall-project/front:0.1.0: not found")
FOUND = (0, "Name: ghcr.io/waterfall-project/front:0.1.0")
FORBIDDEN = (1, "ERROR: unexpected status: 403 Forbidden")


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
    # The trial of the production platform on the images published reads them alone (US-0430/L2).
    assert list(jobs) == ["publish", "trial"]
    assert jobs["trial"]["permissions"] == {"contents": "read", "packages": "read"}
    job = jobs["publish"]
    assert job["permissions"] == {"contents": "read", "packages": "write"}
    publish = job["steps"][-1]
    assert publish["run"] == "make images PUSH=yes"
    assert publish["env"] == {
        "IMAGE_BRANCH": "${{ github.ref_name }}",
        "IMAGE_COMMIT": "${{ github.sha }}",
    }


def test_every_action_of_the_workflow_is_pinned_by_the_digest_of_its_commit() -> None:
    jobs = workflow()["jobs"]
    for step in [*jobs["publish"]["steps"], *jobs["trial"]["steps"]]:
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


def test_every_build_comes_before_any_push() -> None:
    planned = images.commands("main", COMMIT, VERSION, push=True)
    kinds = [command[1] for command in planned]
    assert kinds == ["build"] * 3 + ["push"] * 9


def test_the_tags_of_the_commit_are_pushed_before_those_that_move() -> None:
    planned = images.commands("main", COMMIT, VERSION, push=True)
    pushed = [command[2] for command in planned if command[:2] == ["docker", "push"]]
    assert sorted(pushed) == sorted(tag for tags in built("main").values() for tag in tags)
    assert [reference.rsplit(":", 1)[1] for reference in pushed] == [COMMIT] * 3 + ["main"] * 3 + [
        VERSION
    ] * 3


@pytest.mark.parametrize("branch", ["lot/US-0430/L1", "feature", "mainline", "epic/"])
def test_nothing_is_published_from_a_branch_other_than_main_or_an_epic(branch: str) -> None:
    with pytest.raises(images.ImageError, match="main or epic"):
        images.commands(branch, COMMIT, VERSION, push=True)
    assert images.commands(branch, COMMIT, VERSION, push=False)


def secret_options(command: list[str]) -> list[str]:
    """Return the words of a command that would hand a build a value."""
    return [word for word in command if word.startswith(SECRET_OPTIONS)]


def environment_names(instruction: str) -> list[str]:
    """Return the names an instruction ENV sets, in its two forms: `ENV A=1 B=2`, `ENV A 1`."""
    words = instruction.split()[1:]
    if words and "=" not in words[0]:
        return [words[0]]
    return re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=", " ".join(words))


def test_no_image_receives_a_secret_at_its_build() -> None:
    for command in images.commands("main", COMMIT, VERSION, push=True):
        assert not secret_options(command)
    for dockerfile in dockerfiles():
        for stage in stages(dockerfile):
            for instruction in stage:
                keyword = instruction.split()[0].upper()
                assert keyword != "ARG", f"{dockerfile}: {instruction}"
                if keyword == "ENV":
                    names = environment_names(instruction)
                    assert not [name for name in names if SECRET_NAME.search(name)], instruction


@pytest.mark.parametrize(
    "command",
    [
        ["docker", "build", "--build-arg", "X=1", "."],
        ["docker", "build", "--build-arg=X=1", "."],
        ["docker", "build", "--secret=id=x,src=y", "."],
        ["docker", "build", "--ssh=default", "."],
    ],
)
def test_a_build_handed_a_value_is_seen_in_either_form(command: list[str]) -> None:
    assert secret_options(command)


@pytest.mark.parametrize(
    ("instruction", "names"),
    [
        ("ENV API_TOKEN abc", ["API_TOKEN"]),
        ("ENV A=1 API_TOKEN=abc", ["A", "API_TOKEN"]),
        ('ENV PATH="/app/.venv/bin:${PATH}"', ["PATH"]),
    ],
)
def test_the_names_an_env_sets_are_read_in_both_forms(instruction: str, names: list[str]) -> None:
    assert environment_names(instruction) == names


def test_the_token_that_publishes_is_given_to_the_login_alone() -> None:
    steps = workflow()["jobs"]["publish"]["steps"]
    holding = [step for step in steps if "secrets." in json.dumps(step)]
    assert [step["uses"].split("@")[0] for step in holding] == ["docker/login-action"]


def test_each_image_is_the_last_stage_of_its_dockerfile_and_never_runs_as_root() -> None:
    for dockerfile in dockerfiles():
        last = stages(dockerfile)[-1]
        assert last[0].endswith(f" AS {images.STAGE}"), dockerfile
        users = [line.split()[1] for line in last if line.upper().startswith("USER ")]
        assert users, f"{dockerfile}: the stage says not which user runs it"
        assert users[-1].split(":")[0] not in {"root", "0"}, dockerfile
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


@pytest.mark.parametrize(
    ("branch", "posed", "label"),
    [
        ("main", True, VERSION),
        # On main once the version is published, an image that does not take its tag says so.
        ("main", False, f"{VERSION}+main"),
        ("epic/EP-03", True, f"{VERSION}+epic-EP-03"),
    ],
)
def test_each_image_is_labelled_by_its_own_name_its_source_its_commit_and_its_version(
    branch: str, *, posed: bool, label: str
) -> None:
    builds = images.commands(branch, COMMIT, VERSION, push=False, posed=posed)
    for name, command in zip(NAMES, builds, strict=True):
        tags = [
            command[i + 1].rsplit(":", 1)[1] for i, word in enumerate(command) if word == "--tag"
        ]
        assert (VERSION in tags) == (label == VERSION)
        labels = dict(
            command[i + 1].split("=", 1) for i, word in enumerate(command) if word == "--label"
        )
        assert labels == {
            "org.opencontainers.image.title": name,
            "org.opencontainers.image.source": images.SOURCE,
            "org.opencontainers.image.url": images.SOURCE,
            "org.opencontainers.image.revision": COMMIT,
            "org.opencontainers.image.version": label,
        }


class Docker:
    """A Docker that records what it is asked, and answers as a test tells it.

    A build fails if its context is the one named; the registry answers image by image as told
    for the tag of a version, that it lacks for an image not named; the image of Keycloak holds the
    bytes given.
    """

    def __init__(
        self,
        *,
        failing: str = "",
        registry: Mapping[str, tuple[int, str]] | None = None,
        holding: bytes = b"",
    ) -> None:
        self.ran: list[list[str]] = []
        self.read_: list[list[str]] = []
        self.failing = failing
        self.registry = dict(registry or {})
        self.holding = holding

    def run(self, command: list[str]) -> int:
        self.ran.append(command)
        return 1 if self.failing and command[-1] == self.failing else 0

    def read(self, command: list[str]) -> tuple[int, str]:
        self.read_.append(command)
        name = command[-1].rsplit("/", 1)[1].split(":", 1)[0]
        return self.registry.get(name, NOT_FOUND)

    def contents(self, image: str) -> Iterable[bytes]:
        yield b"usr/bin/" + (self.holding if "/keycloak:" in image else b"")

    def pushed(self) -> list[str]:
        return [command[2] for command in self.ran if command[:2] == ["docker", "push"]]

    def main(self, branch: str = "epic/EP-03", *arguments: str) -> int:
        environment = {"IMAGE_BRANCH": branch, "IMAGE_COMMIT": COMMIT}
        return images.main(arguments, environment, self.run, self.read, self.contents)


@pytest.fixture
def checkout(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Stand for a checkout at COMMIT, clean unless a test says otherwise."""
    answers = {"rev-parse": COMMIT, "status": ""}

    def git(*arguments: str) -> str:
        return answers[arguments[0]]

    monkeypatch.setattr(images, "_git", git)
    return answers


@pytest.mark.usefixtures("checkout")
def test_the_images_are_built_from_the_branch_and_the_commit_the_chain_names(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Docker()
    assert docker.main("epic/EP-03", "--push") == 0
    assert docker.ran == images.commands("epic/EP-03", COMMIT, VERSION, push=True)
    assert docker.read_ == []
    assert f"--tag ghcr.io/waterfall-project/front:{COMMIT}" in capsys.readouterr().out


@pytest.mark.usefixtures("checkout")
def test_an_image_that_fails_to_build_stops_everything_before_any_push() -> None:
    docker = Docker(failing="deploy/keycloak")
    assert docker.main("main", "--push") == 1
    assert [command[-1] for command in docker.ran] == ["frontend", "backend", "deploy/keycloak"]
    assert docker.pushed() == []


@pytest.mark.usefixtures("checkout")
def test_a_new_version_is_posed_on_main() -> None:
    docker = Docker()
    assert docker.main("main", "--push") == 0
    assert [command[-1] for command in docker.read_] == [
        f"ghcr.io/waterfall-project/{name}:{VERSION}" for name in NAMES
    ]
    assert [f"ghcr.io/waterfall-project/{name}:{VERSION}" for name in NAMES] == docker.pushed()[-3:]


@pytest.mark.usefixtures("checkout")
@pytest.mark.parametrize(
    ("answer", "code", "said"),
    [
        (FOUND, 0, "the three images hold"),
        # ghcr answers 403 for a package it lacks or cannot read: it says nothing of the tag.
        (FORBIDDEN, 2, "did not say whether it holds"),
    ],
)
def test_a_version_published_already_is_never_posed_again(
    answer: tuple[int, str], code: int, said: str, capsys: pytest.CaptureFixture[str]
) -> None:
    docker = Docker(registry=dict.fromkeys(NAMES, answer))
    assert docker.main("main", "--push") == code
    assert_no_version_and_the_tags_of_the_commit_and_the_branch_pushed(docker)
    assert said in capsys.readouterr().out


def assert_no_version_and_the_tags_of_the_commit_and_the_branch_pushed(docker: Docker) -> None:
    """Hold that no image took the tag of the version, and that every other tag was pushed."""
    references = [word for command in docker.ran for word in command if word.startswith("ghcr.io")]
    assert not [reference for reference in references if reference.endswith(f":{VERSION}")]
    assert [reference.rsplit(":", 1)[1] for reference in docker.pushed()] == [COMMIT] * 3 + [
        "main"
    ] * 3


@pytest.mark.usefixtures("checkout")
@pytest.mark.parametrize(
    ("registry", "said"),
    [
        # A publication that failed after two images took the version: the next merge, of another
        # commit, must not complete it.
        ({"front": FOUND, "waterfall": FOUND}, "held by front, waterfall; lacking on keycloak"),
        ({"waterfall": FORBIDDEN}, "lacking on front, keycloak; unclear for waterfall"),
        (
            {"keycloak": FOUND, "front": FORBIDDEN},
            "held by keycloak; lacking on waterfall; unclear for front",
        ),
    ],
)
def test_a_version_the_registry_holds_for_some_images_alone_is_posed_on_none_and_fails(
    registry: dict[str, tuple[int, str]], said: str, capsys: pytest.CaptureFixture[str]
) -> None:
    docker = Docker(registry=registry)
    assert docker.main("main", "--push") == 2
    assert [command[-1] for command in docker.read_] == [
        f"ghcr.io/waterfall-project/{name}:{VERSION}" for name in NAMES
    ]
    assert_no_version_and_the_tags_of_the_commit_and_the_branch_pushed(docker)
    error = capsys.readouterr().err
    assert f"wftools.images: the version {VERSION} is posed on no image ({said})" in error


@pytest.mark.usefixtures("checkout")
def test_a_push_that_fails_is_said_before_the_version_left_unposed() -> None:
    docker = Docker(registry={"front": FOUND}, failing=f"ghcr.io/waterfall-project/front:{COMMIT}")
    assert docker.main("main", "--push") == 1
    assert docker.pushed() == [f"ghcr.io/waterfall-project/front:{COMMIT}"]


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("checkout")
def test_an_image_that_holds_a_value_of_the_development_is_not_pushed_and_it_is_named(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # « Une recherche des secrets connus dans le dépôt, les images publiées et les journaux ne les
    # trouve pas. » : for the images, in the file system of each one before it is published (#824).
    docker = Docker(holding=b"WATERFALL_REDIS_PASSWORD=chain-only-redis\n")
    assert docker.main("epic/EP-03", "--push") == 2
    assert docker.pushed() == []
    error = capsys.readouterr().err
    assert "keycloak holds WATERFALL_REDIS_PASSWORD (.github/workflows/keycloak.yml)" in error
    assert "chain-only-redis" not in error


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_value_is_found_across_two_chunks_of_an_image() -> None:
    values = {"mark": "development-only"}
    assert images.held([b"xx develop", b"ment-only yy"], values) == ["mark"]
    assert images.held([b"xx develop", b"ment yy"], values) == []


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_values_searched_are_the_secrets_of_the_chain_and_the_mark_of_the_development() -> None:
    values = images.development_values()
    job = yaml.safe_load(images.WORKSTATION_SECRETS.read_text(encoding="utf-8"))["jobs"]["check"]
    secrets = {value for name, value in job["env"].items() if SECRET_NAME.search(name)}
    assert len(secrets) == 11
    assert set(values.values()) == secrets | {images.DEVELOPMENT_MARK}


@pytest.mark.requirement("WF-SEC-0010-A")
def test_every_value_of_the_development_platform_carries_the_mark_searched() -> None:
    development = REPOSITORY / "deploy" / "keycloak" / "development"
    values = [
        value
        for path in sorted(development.glob("*.yaml"))
        for value in secrets_of(yaml.safe_load(path.read_text(encoding="utf-8")))
    ]
    ldif = (development / "directory.ldif").read_text(encoding="utf-8")
    values += re.findall(r"^userPassword:\s*(\S+)", ldif, re.MULTILINE)
    assert len(values) >= 4
    assert all(images.DEVELOPMENT_MARK in str(value) for value in values), values


@pytest.mark.parametrize(
    ("answers", "said"),
    [
        ({"rev-parse": "f" * 40, "status": ""}, "is not the checkout's"),
        ({"rev-parse": COMMIT, "status": "M frontend/Dockerfile\n?? backend/x.py"}, "not clean"),
    ],
)
def test_a_checkout_other_than_the_commit_named_or_not_clean_pushes_nothing(
    checkout: dict[str, str],
    answers: dict[str, str],
    said: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    checkout.update(answers)
    docker = Docker()
    assert docker.main("main", "--push") == 2
    assert docker.ran == []
    error = capsys.readouterr().err
    assert said in error
    if "clean" in said:
        assert "frontend/Dockerfile, backend/x.py" in error


@pytest.mark.parametrize(
    ("failure", "said"),
    [
        (
            subprocess.CalledProcessError(128, ["git", "rev-parse"], stderr="not a git repository"),
            "git rev-parse failed: not a git repository",
        ),
        (FileNotFoundError(2, "No such file or directory", "git"), "git could not run"),
    ],
)
def test_a_git_that_fails_or_is_missing_is_said_without_a_trace(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    said: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def git(*_arguments: str) -> str:
        raise failure

    monkeypatch.setattr(images, "_git", git)
    docker = Docker()
    assert images.main([], {}, docker.run, docker.read, docker.contents) == 2
    assert docker.ran == []
    assert f"wftools.images: {said}" in capsys.readouterr().err


def test_the_first_command_that_fails_stops_the_rest() -> None:
    docker = Docker(failing="frontend")
    assert docker.main("main") == 1
    assert len(docker.ran) == 1


def test_a_push_refused_says_why_and_runs_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    docker = Docker()
    assert docker.main("lot/US-0430/L1", "--push") == 2
    assert docker.ran == []
    assert "not from 'lot/US-0430/L1'" in capsys.readouterr().err


def test_without_the_chain_the_branch_and_the_commit_are_those_of_the_checkout() -> None:
    docker = Docker()
    assert images.main([], {}, docker.run, docker.read, docker.contents) == 0
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert len(docker.ran) == len(images.IMAGES)
    for command in docker.ran:
        assert command[command.index("--tag") + 1].endswith(f":{head}")
