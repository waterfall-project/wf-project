# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Build the images of Waterfall, and publish them from main or an epic branch (US-0430).

Usage: ``python -m wftools.images [--push]``.

Three images, each the stage ``production`` of its Dockerfile: ``front``, ``waterfall`` — the API,
the worker, its schedule and the migrations, commands of one distribution — and ``keycloak``, with
the extension and the realm. Each is tagged by the full hash of the commit it is built from and by
its branch, made a valid tag (``epic/EP-03`` gives ``epic-EP-03``); on ``main``, by the version of
the distribution of the back besides, which the API and the worker report and a backup will carry.
An epic branch does not take it: the version moves with ``main`` alone, and a demonstration would
overwrite the tag of the release.

The branch and the commit are those of the checkout, unless ``IMAGE_BRANCH`` and ``IMAGE_COMMIT``
name them, as the chain does. Nothing is passed to a build but its context: no build argument, no
build secret — the images read every secret from the environment of their container (WF-SEC-0010).
``--push`` publishes them, from ``main`` or a branch ``epic/…`` alone: never from a lot or a pull
request.
"""

import argparse
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping, Sequence
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


class ImageError(Exception):
    """A branch, a commit or a version that cannot tag an image, or a push refused."""


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


def tags(branch: str, commit: str, release: str) -> list[str]:
    """Return the tags of an image built from a commit of a branch, the release's on main."""
    if not COMMIT.fullmatch(commit):
        message = f"not the full hash of a commit: {commit!r}"
        raise ImageError(message)
    if not TAG.fullmatch(release):
        message = f"the version {release!r} makes no tag"
        raise ImageError(message)
    found = [commit, branch_tag(branch)]
    if branch == RELEASE_BRANCH:
        found.append(release)
    return found


def publishable(branch: str) -> bool:
    """Tell whether images built from this branch may be published: main and epic branches."""
    return branch == RELEASE_BRANCH or EPIC_BRANCH.fullmatch(branch) is not None


def commands(branch: str, commit: str, release: str, *, push: bool) -> list[list[str]]:
    """Return the commands that build the images, and push every tag of each if asked."""
    if push and not publishable(branch):
        message = f"the images are published from main or epic/… alone, not from {branch!r}"
        raise ImageError(message)
    found: list[list[str]] = []
    labels = {
        "org.opencontainers.image.source": SOURCE,
        "org.opencontainers.image.revision": commit,
        "org.opencontainers.image.version": release,
    }
    for image in IMAGES:
        references = [f"{REGISTRY}/{image.name}:{tag}" for tag in tags(branch, commit, release)]
        build = ["docker", "build", "--target", STAGE]
        build += [word for key, value in labels.items() for word in ("--label", f"{key}={value}")]
        build += [option for reference in references for option in ("--tag", reference)]
        found.append([*build, image.context])
        if push:
            found.extend(["docker", "push", reference] for reference in references)
    return found


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=REPOSITORY, capture_output=True, text=True, check=True
    )
    return (result.stdout or "").strip()


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPOSITORY, check=False).returncode


def main(
    arguments: Sequence[str],
    environment: Mapping[str, str] = os.environ,
    run: Callable[[list[str]], int] = _run,
) -> int:
    """Build the images, and push them with ``--push``; stop at the first command that fails."""
    parser = argparse.ArgumentParser(prog="wftools.images", description="Build the images.")
    parser.add_argument("--push", action="store_true", help="publish every tag of each image")
    options = parser.parse_args(arguments)
    branch = environment.get("IMAGE_BRANCH") or _git("rev-parse", "--abbrev-ref", "HEAD")
    commit = environment.get("IMAGE_COMMIT") or _git("rev-parse", "HEAD")
    try:
        planned = commands(branch, commit, version(), push=options.push)
    except ImageError as error:
        print(f"wftools.images: {error}", file=sys.stderr)
        return 2
    for command in planned:
        print(f"  {' '.join(command)}", flush=True)
        if (code := run(command)) != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
