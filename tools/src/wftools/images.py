# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Build the images of Waterfall, and publish them from main or an epic branch (US-0430).

Usage: ``python -m wftools.images [--push]``.

Three images, each the stage ``production`` of its Dockerfile: ``front``, ``waterfall`` — the API,
the worker, its schedule and the migrations, commands of one distribution — and ``keycloak``, with
the extension and the realm. Each is tagged by the full hash of the commit it is built from and by
its branch, made a valid tag (``epic/EP-03`` gives ``epic-EP-03``); on ``main``, by the version of
the distribution of the back besides, which the API and the worker report and a backup will carry.
The tag of a version is immutable: once in the registry it is never posed again, and a merge into
main that does not raise the version publishes the tags of its commit and of its branch alone. It
is decided for the three images together, so that a version never gathers images of two commits:
the three take it if the registry holds it for none, none takes it if it holds it for all three;
anything else — some hold it, or the registry does not say — publishes the tags of the commit and
of the branch, poses the version on none, and fails naming the images. An epic branch never takes
it — a demonstration would pass for the release —, and the label of the version of an image that
does not take it says so (``0.1.0+epic-EP-03``, ``0.1.0+main``).

The branch and the commit are those of the checkout, unless ``IMAGE_BRANCH`` and ``IMAGE_COMMIT``
name them, as the chain does. Nothing is passed to a build but its context: no build argument, no
build secret — the images read every secret from the environment of their container (WF-SEC-0010).

``--push`` publishes them: from ``main`` or a branch ``epic/…`` alone, never from a lot or a pull
request; from a checkout that is the commit named and is clean in the contexts of the images. The
three images are built first, then searched for the known values of the development, and pushed
only if all three were built and none holds one: every tag of the commit first, then the tags that
move, so that a tag of a branch or of a version never names images of two commits.
"""

import argparse
import enum
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from wftools import REPOSITORY

REGISTRY = "ghcr.io/waterfall-project"
"""Where the images are published: the packages of the organisation on GitHub."""

SOURCE = "https://github.com/waterfall-project/wf-project"
"""The repository the images come from, which GitHub links each package to."""

STAGE = "production"
"""The stage of each Dockerfile that is the published image."""

RELEASE_BRANCH = "main"
EPIC_BRANCH = re.compile(r"epic/.+")
COMMIT = re.compile(r"[0-9a-f]{40}")
# A tag of the registry: a word character first, 128 characters at most.
TAG = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}")
NOT_IN_TAG = re.compile(r"[^A-Za-z0-9_.-]")

DEVELOPMENT_MARK = "development-only"
"""What every value of the development platform carries (``deploy/keycloak/development/``)."""

WORKSTATION_SECRETS = REPOSITORY / ".github" / "workflows" / "keycloak.yml"
"""The workflow whose secrets, values of a workstation, the chain starts the platform with."""

# A secret of the platform the workflow sets, one per line: `WATERFALL_…_PASSWORD: value`.
WORKSTATION_SECRET = re.compile(
    r"^\s+(WATERFALL_[A-Z_]*(?:PASSWORD|SECRET)):\s*(\S+)\s*$", re.MULTILINE
)
# What the registry answers for a tag it does not hold.
UNKNOWN_TAG = re.compile(r"not found|manifest unknown", re.IGNORECASE)
CHUNK = 1 << 20


@dataclass(frozen=True, slots=True)
class Image:
    """An image the chain publishes: its name in the registry and its build context."""

    name: str
    context: str


IMAGES = (
    Image("front", "frontend"),
    Image("waterfall", "backend"),
    Image("keycloak", "deploy/keycloak"),
)


def cache_source(name: str) -> list[str]:
    """Return the options that read the cache of the builds of an image on GitHub Actions.

    Written after a merge, under the name of the image (``make build-cache``); Docker leaves it out
    where the runtime of GitHub Actions is not given to it, as on a workstation.
    """
    return ["--cache-from", f"type=gha,scope={name}"]


class ImageError(Exception):
    """A branch, a commit or a version that cannot tag an image, or a push refused."""


class Holding(enum.Enum):
    """What the registry says of the tag of a version, for one image."""

    HELD = "held by"
    LACKING = "lacking on"
    UNCLEAR = "unclear for"


def version() -> str:
    """Return the version of the distribution of the back, which tags a release."""
    with (REPOSITORY / "backend" / "pyproject.toml").open("rb") as file:
        project: dict[str, object] = tomllib.load(file)["project"]
    return str(project["version"])


def branch_tag(branch: str) -> str:
    """Make a branch a tag: every character a tag refuses becomes ``-``."""
    tag = NOT_IN_TAG.sub("-", branch).lstrip(".-")[:128]
    if not TAG.fullmatch(tag):
        message = f"the branch {branch!r} makes no tag"
        raise ImageError(message)
    return tag


def tags(branch: str, commit: str, release: str, *, posed: bool = True) -> list[str]:
    """Return the tags of an image built from a commit of a branch; the release's, if posed."""
    if not COMMIT.fullmatch(commit):
        message = f"not the full hash of a commit: {commit!r}"
        raise ImageError(message)
    if not TAG.fullmatch(release):
        message = f"the version {release!r} makes no tag"
        raise ImageError(message)
    found = [commit, branch_tag(branch)]
    if takes_version(branch, posed=posed):
        found.append(release)
    return found


def takes_version(branch: str, *, posed: bool) -> bool:
    """Tell whether the images of a branch take the tag of the version: on main, if posed."""
    return branch == RELEASE_BRANCH and posed


def publishable(branch: str) -> bool:
    """Tell whether images built from this branch may be published: main and epic branches."""
    return branch == RELEASE_BRANCH or EPIC_BRANCH.fullmatch(branch) is not None


def check_branch(branch: str) -> None:
    """Refuse to publish images built from a branch other than main or an epic branch."""
    if not publishable(branch):
        message = f"the images are published from main or epic/… alone, not from {branch!r}"
        raise ImageError(message)


def reference(image: Image, tag: str) -> str:
    """Return the reference of an image under a tag, in the registry."""
    return f"{REGISTRY}/{image.name}:{tag}"


def labels(
    image: Image, branch: str, commit: str, release: str, *, posed: bool = True
) -> dict[str, str]:
    """Return the labels of an image: what it is, where it comes from, which version it is.

    They replace those of the base image, which name its own project — that of Keycloak does.
    The version is bare on an image that takes its tag alone; on any other — outside main, or on
    main once the version is published —, it says the branch the image is built from.
    """
    return {
        "org.opencontainers.image.title": image.name,
        "org.opencontainers.image.source": SOURCE,
        "org.opencontainers.image.url": SOURCE,
        "org.opencontainers.image.revision": commit,
        "org.opencontainers.image.version": (
            release if takes_version(branch, posed=posed) else f"{release}+{branch_tag(branch)}"
        ),
    }


def builds(branch: str, commit: str, release: str, *, posed: bool = True) -> list[list[str]]:
    """Return the command that builds each image, under every tag it takes."""
    found: list[list[str]] = []
    for image in IMAGES:
        build = ["docker", "build", "--target", STAGE, *cache_source(image.name)]
        for key, value in labels(image, branch, commit, release, posed=posed).items():
            build += ["--label", f"{key}={value}"]
        for tag in tags(branch, commit, release, posed=posed):
            build += ["--tag", reference(image, tag)]
        found.append([*build, image.context])
    return found


def pushes(branch: str, commit: str, release: str, *, posed: bool = True) -> list[list[str]]:
    """Return the pushes of every tag: those of the commit first, then those that move."""
    check_branch(branch)
    return [
        ["docker", "push", reference(image, tag)]
        for tag in tags(branch, commit, release, posed=posed)
        for image in IMAGES
    ]


def commands(
    branch: str, commit: str, release: str, *, push: bool, posed: bool = True
) -> list[list[str]]:
    """Return the commands that build the three images, then push every tag of each if asked."""
    planned = pushes(branch, commit, release, posed=posed) if push else []
    return builds(branch, commit, release, posed=posed) + planned


def development_values() -> dict[str, str]:
    """Return, by name, the values of the development that no image may hold.

    The mark every value of ``deploy/keycloak/development/`` carries, and the secrets the chain
    starts the service platform with, which a workstation reuses.
    """
    found = {f"{DEVELOPMENT_MARK} (deploy/keycloak/development/)": DEVELOPMENT_MARK}
    source = WORKSTATION_SECRETS.relative_to(REPOSITORY)
    for name, value in WORKSTATION_SECRET.findall(WORKSTATION_SECRETS.read_text(encoding="utf-8")):
        found[f"{name} ({source})"] = value
    return found


def held(contents: Iterable[bytes], values: Mapping[str, str]) -> list[str]:
    """Return the names of the values the contents hold, read in chunks, one across two too."""
    needles = {name: value.encode() for name, value in values.items()}
    overlap = max((len(needle) for needle in needles.values()), default=1) - 1
    found: set[str] = set()
    tail = b""
    for chunk in contents:
        window = tail + chunk
        found |= {name for name, needle in needles.items() if needle in window}
        tail = window[-overlap:] if overlap else b""
    return sorted(found)


def registry_answers(
    release: str, read: Callable[[list[str]], tuple[int, str]]
) -> dict[str, Holding]:
    """Ask the registry, image by image, whether it holds the tag of this version."""
    found: dict[str, Holding] = {}
    for image in IMAGES:
        tagged = reference(image, release)
        code, answer = read(["docker", "buildx", "imagetools", "inspect", tagged])
        if code == 0:
            found[image.name] = Holding.HELD
        elif UNKNOWN_TAG.search(answer):
            found[image.name] = Holding.LACKING
        else:
            said = (answer.strip().splitlines() or ["nothing"])[-1]
            print(f"wftools.images: the registry did not say whether it holds {tagged} ({said})")
            found[image.name] = Holding.UNCLEAR
    return found


def version_decision(release: str, answers: Mapping[str, Holding]) -> tuple[bool, str]:
    """Decide the version for the three images together: whether they take it, and what fails.

    None holds it: the three take it. All three do: none takes it again, the case of a merge that
    does not raise the version. Anything else poses it on none, and fails the publication once the
    tags of the commit and of the branch are pushed, naming the images: a version is posed once,
    on the images of one commit.
    """
    holdings = set(answers.values())
    if holdings == {Holding.LACKING}:
        return True, ""
    if holdings == {Holding.HELD}:
        print(f"wftools.images: the three images hold {release} already: it is not posed again")
        return False, ""
    said = "; ".join(
        f"{holding.value} {', '.join(name for name, found in answers.items() if found is holding)}"
        for holding in Holding
        if holding in holdings
    )
    return False, f"the version {release} is posed on no image ({said})"


def check_checkout(commit: str) -> None:
    """Refuse a push from a checkout that is not the commit named, or not clean where it builds."""
    head = _git("rev-parse", "HEAD")
    if commit != head:
        message = f"the commit named, {commit}, is not the checkout's, {head}: nothing is pushed"
        raise ImageError(message)
    if dirty := _git("status", "--porcelain", "--", *(image.context for image in IMAGES)):
        changed = ", ".join(line.split(maxsplit=1)[-1] for line in dirty.splitlines())
        message = f"the contexts of the images are not clean ({changed}): nothing is pushed"
        raise ImageError(message)


def check_contents(commit: str, contents: Callable[[str], Iterable[bytes]]) -> None:
    """Refuse a push if a built image holds a known value of the development, naming it."""
    values = development_values()
    for image in IMAGES:
        if found := held(contents(reference(image, commit)), values):
            message = f"the image {image.name} holds {', '.join(found)}: nothing is pushed"
            raise ImageError(message)


def _contents(image: str) -> Iterator[bytes]:
    """Read the file system of an image, as the archive Docker exports of a container of it."""
    container = subprocess.run(
        ["docker", "create", image], capture_output=True, text=True, check=True
    ).stdout.strip()
    try:
        with subprocess.Popen(["docker", "export", container], stdout=subprocess.PIPE) as export:
            stream = export.stdout
            while stream is not None and (chunk := stream.read(CHUNK)):
                yield chunk
        if export.returncode != 0:
            message = f"the file system of {image} could not be read"
            raise ImageError(message)
    finally:
        subprocess.run(["docker", "rm", container], capture_output=True, check=False)


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=REPOSITORY, capture_output=True, text=True, check=True
    )
    return (result.stdout or "").strip()


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPOSITORY, check=False).returncode


def _read(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return result.returncode, f"{result.stdout}{result.stderr}"


def _execute(commands: list[list[str]], run: Callable[[list[str]], int]) -> int:
    """Run commands in order, each shown first; stop at the first that fails."""
    for command in commands:
        print(f"  {' '.join(command)}", flush=True)
        if (code := run(command)) != 0:
            return code
    return 0


def _failure(error: OSError | subprocess.CalledProcessError) -> str:
    """Say which command could not run, or failed, and why."""
    if isinstance(error, subprocess.CalledProcessError):
        command = " ".join(map(str, error.cmd))
        return f"{command} failed: {str(error.stderr or '').strip() or f'exit {error.returncode}'}"
    return f"{error.filename or 'a command'} could not run: {error.strerror or error}"


def main(
    arguments: Sequence[str],
    environment: Mapping[str, str] = os.environ,
    run: Callable[[list[str]], int] = _run,
    read: Callable[[list[str]], tuple[int, str]] = _read,
    contents: Callable[[str], Iterable[bytes]] = _contents,
) -> int:
    """Build the images, and push them with ``--push``; stop at the first command that fails."""
    parser = argparse.ArgumentParser(prog="wftools.images", description="Build the images.")
    parser.add_argument("--push", action="store_true", help="publish every tag of each image")
    options = parser.parse_args(arguments)
    try:
        branch = environment.get("IMAGE_BRANCH") or _git("rev-parse", "--abbrev-ref", "HEAD")
        commit = environment.get("IMAGE_COMMIT") or _git("rev-parse", "HEAD")
        release = version()
        posed, failed = True, ""
        if options.push:
            check_branch(branch)
            check_checkout(commit)
            if branch == RELEASE_BRANCH:
                posed, failed = version_decision(release, registry_answers(release, read))
        if code := _execute(builds(branch, commit, release, posed=posed), run):
            return code
        if not options.push:
            return 0
        check_contents(commit, contents)
        code = _execute(pushes(branch, commit, release, posed=posed), run)
        if code or not failed:
            return code
        print(f"wftools.images: {failed}", file=sys.stderr)
    except ImageError as error:
        print(f"wftools.images: {error}", file=sys.stderr)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"wftools.images: {_failure(error)}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
