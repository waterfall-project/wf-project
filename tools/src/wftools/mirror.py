# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mirror of the images of Docker Hub on ghcr.io, found or filled by digest (US-1900).

Usage: ``python -m wftools.mirror [--push]``.

The Compose files, the Dockerfiles and the services of the workflows name the third-party images
of Docker Hub — PostgreSQL, Redis, Caddy, Mailpit, Garage, curl, Node, Python, Debian, Maven,
Keycloak and its config CLI — under ``ghcr.io/waterfall-project/mirror/``, pinned by the digest
they had on Docker Hub: ``mirror/postgres:18-trixie@sha256:…`` is ``docker.io/library/postgres``
at that digest. A pull of Docker Hub failed three runs of ``keycloak / check`` and one of
``production / trial`` in a week (« failed to fetch oauth token »): the chain now reads Docker Hub
only to fill the mirror, once per digest, never to run.

The tool reads every reference to the mirror in those files and asks ghcr.io whether it holds the
digest. Held, nothing else is read: a run whose images are all in the mirror does not reach
Docker Hub. Missing, ``--push`` copies it, by digest — ``docker buildx imagetools create`` writes
the manifest of the source as it is, so that the copy has the digest the files pin, which is
checked after — under a tag of the tool's: the tag of the file and the first digits of the digest,
so that two digests one tag of Docker Hub has had live side by side. Without ``--push`` the tool
only says what is missing, and fails. The chain runs it with ``--push`` before every job that
pulls an image (the job ``mirror`` of ci.yml, and images.yml), so that the mirror exists before the
first run that needs it, on the pull request that adds an image or raises a digest: images.yml
runs after a merge, which is too late. A request is tried again (wftools.registry, #2530); an image
neither the mirror nor Docker Hub gives fails the run before any job starts, naming Docker Hub.

A package GitHub creates is private; the jobs that pull from the mirror ask for ``packages: read``
and log in, and a workstation that has not logged in pulls from it once the packages are made
public (docs/dev/README-fr.md, « La chaîne »).
"""

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wftools import REPOSITORY, registry
from wftools.registry import ATTEMPTS, REGISTRY, ImageError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from pathlib import Path

TOOL = "wftools.mirror"
"""The name the tool gives its messages."""

MIRROR = f"{REGISTRY}/waterfall-project/mirror"
"""Where the copies are: beside the images of Waterfall (wftools.images), under their own name."""

SOURCE = "Docker Hub"
"""The registry the mirror is filled from, which a failure names."""

SCANNED = (
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "deploy/**/Dockerfile",
    "deploy/**/*.Dockerfile",
    "deploy/compose/*.yaml",
    ".github/workflows/*.yml",
)
"""The files that name an image of the mirror: Dockerfiles, Compose files, the services of jobs."""

REFERENCE = re.compile(
    re.escape(MIRROR)
    + r"/(?P<path>[a-z0-9][a-z0-9_.-]*(?:/[a-z0-9][a-z0-9_.-]*)*)"
    + r":(?P<tag>[A-Za-z0-9_][A-Za-z0-9_.-]*)@(?P<digest>sha256:[0-9a-f]{64})"
)
DIGEST_DIGITS = 12
"""The digits of the digest the tag of a copy keeps."""


@dataclass(frozen=True, order=True)
class Mirrored:
    """An image of Docker Hub as the files pin it: its repository, its tag, its digest."""

    path: str
    tag: str
    digest: str

    @property
    def pinned(self) -> str:
        """Return the copy as the files name it: the name of the mirror, its digest."""
        return f"{MIRROR}/{self.path}@{self.digest}"

    @property
    def tagged(self) -> str:
        """Return the tag the copy is published under: the tag of the file, the digest's start."""
        start = self.digest.removeprefix("sha256:")[:DIGEST_DIGITS]
        return f"{MIRROR}/{self.path}:{self.tag}-{start}"

    @property
    def source(self) -> str:
        """Return the image on Docker Hub, by the same digest; an official image is in library."""
        repository = self.path if "/" in self.path else f"library/{self.path}"
        return f"docker.io/{repository}@{self.digest}"


def referenced(root: Path = REPOSITORY, patterns: Iterable[str] = SCANNED) -> list[Mirrored]:
    """Return the images the files name under the mirror, each once, in order."""
    found: set[Mirrored] = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if path.is_file():
                for match in REFERENCE.finditer(path.read_text(encoding="utf-8")):
                    found.add(Mirrored(match["path"], match["tag"], match["digest"]))
    return sorted(found)


def fill(
    image: Mirrored,
    *,
    run: Callable[[list[str]], int],
    read: Callable[[list[str]], tuple[int, str]],
    wait: Callable[[float], None],
) -> None:
    """Copy an image of Docker Hub to the mirror, by digest, and check the copy kept it."""
    command = ["docker", "buildx", "imagetools", "create", "--tag", image.tagged, image.source]
    if not registry.attempted(command, run, wait, tool=TOOL):
        message = (
            f"{SOURCE} did not give {image.source} to copy to {image.tagged}, "
            f"in {ATTEMPTS} attempts, and {REGISTRY} does not hold it"
        )
        raise ImageError(message)
    if registry.held_digest(image.pinned, read, wait, tool=TOOL) != image.digest:
        message = f"{REGISTRY} does not hold {image.pinned}, just copied from {image.source}"
        raise ImageError(message)


def ensure(
    images: Sequence[Mirrored],
    *,
    push: bool,
    run: Callable[[list[str]], int],
    read: Callable[[list[str]], tuple[int, str]],
    wait: Callable[[float], None] = time.sleep,
) -> list[Mirrored]:
    """Make sure the mirror holds each image; return those it did not hold, copied with ``push``.

    The mirror is asked first, by digest: an image it holds is never read from Docker Hub. The
    first image neither gives fails the run, naming the source.
    """
    missing: list[Mirrored] = []
    for image in images:
        if registry.held_digest(image.pinned, read, wait, tool=TOOL) is not None:
            continue
        missing.append(image)
        if push:
            print(f"{TOOL}: {image.pinned} is not in the mirror: copying it", file=sys.stderr)
            fill(image, run=run, read=read, wait=wait)
    return missing


def _run(command: list[str]) -> int:
    # What Docker prints goes to the error stream, as in wftools.e2eimage.
    return subprocess.run(command, cwd=REPOSITORY, stdout=sys.stderr, check=False).returncode


def _read(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return result.returncode, f"{result.stdout}{result.stderr}"


def main(
    arguments: Sequence[str],
    run: Callable[[list[str]], int] = _run,
    read: Callable[[list[str]], tuple[int, str]] = _read,
    wait: Callable[[float], None] = time.sleep,
    root: Path = REPOSITORY,
) -> int:
    """Check the mirror holds what the files name, and fill it with ``--push``."""
    parser = argparse.ArgumentParser(prog=TOOL, description="The mirror of Docker Hub's images.")
    parser.add_argument("--push", action="store_true", help="copy what the mirror does not hold")
    options = parser.parse_args(arguments)
    images = referenced(root)
    if not images:
        print(f"{TOOL}: no image of the mirror is named in the files", file=sys.stderr)
        return 2
    try:
        missing = ensure(images, push=options.push, run=run, read=read, wait=wait)
    except ImageError as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"{TOOL}: {error.filename or 'docker'} could not run: {error}", file=sys.stderr)
        return 2
    if missing and not options.push:
        for image in missing:
            print(f"{TOOL}: {image.pinned} is missing (make mirror PUSH=yes)", file=sys.stderr)
        return 1
    print(f"{TOOL}: {len(images)} images, {len(missing)} copied", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
