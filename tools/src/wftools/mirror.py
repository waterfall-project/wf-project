# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mirror of the images of Docker Hub on ghcr.io, found or filled by digest, and its manifest.

Usage: ``python -m wftools.mirror [--push]``, ``python -m wftools.mirror sync``.

The Compose files and the Dockerfiles name the third-party images of Docker Hub — PostgreSQL,
Redis, Caddy, Mailpit, Garage, curl, k6, Node, Python, Debian, Maven, Keycloak and its config CLI —
by the digest they have there, behind ``${WATERFALL_MIRROR:-}`` (``ARG WATERFALL_MIRROR=`` in a
Dockerfile): empty, they are Docker Hub's, on the workstation, in production and for Dependabot; the
chain poses ``ghcr.io/waterfall-project/mirror/``, and ``mirror/postgres:18-trixie@sha256:…`` is
``docker.io/library/postgres`` at that digest. The services of the workflows name the mirror itself.
A pull of Docker Hub failed three runs of ``keycloak / check`` and one of ``production / trial``
in a week (« failed to fetch oauth token »): the chain now reads Docker Hub
only to fill the mirror, once per digest, never to run (US-1900).

Dependabot does not read a prefixed reference — ``FROM ${WATERFALL_MIRROR}…`` nor
``${WATERFALL_MIRROR:-}…`` —: it follows the manifest, ``deploy/images/Dockerfile``, which no build
reads, one bare line ``FROM <image>:<tag>@sha256:…`` per image of Docker Hub the repository pins
(US-2490, #3025). ``drift`` says each reference of the files that is not the manifest's, tag and
digest, and each image of the manifest nothing uses; ``sync`` copies the manifest into the
references, the prefix kept, YAML anchors included. A raise by Dependabot changes the manifest
alone, and its chain fails on that until a person runs ``make mirror-sync``, then
``make mirror PUSH=yes``, and pushes to the branch of its pull request.

The tool reads every reference to the mirror in those files and asks ghcr.io whether it holds the
digest. Held, nothing else is read: a run whose images are all in the mirror does not reach
Docker Hub. Missing, ``--push`` copies it, by digest — ``docker buildx imagetools create`` writes
the manifest of the source as it is, so that the copy has the digest the files pin, which is
checked after — under a tag of the tool's: the tag of the file and the first digits of the digest,
so that two digests one tag of Docker Hub has had live side by side. Without ``--push`` the tool
only says what is missing, and fails. The chain runs it with ``--push`` before every job that
pulls an image (the job ``mirror`` of ci.yml, and images.yml), so that the mirror exists before the
first run that needs it, on the pull request that adds an image or raises a digest: images.yml
runs after a merge, which is too late. A request is tried again (wftools.registry, #2530), and a
copy ghcr.io refuses once (#3028); an image neither the mirror nor Docker Hub gives fails the run
before any job starts, naming Docker Hub.

A package GitHub creates is private: the jobs that pull from the mirror ask for ``packages: read``
and log in, and nothing outside the chain reads it (docs/dev/README-fr.md, « Chaîne »).
"""

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wftools import REPOSITORY, registry
from wftools.registry import ATTEMPTS, REFUSED, REGISTRY, UNKNOWN_TAG, ImageError

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
"""The files that name an image of Docker Hub: Dockerfiles, Compose files, services of jobs."""

MANIFEST = "deploy/images/Dockerfile"
"""The manifest Dependabot follows: one bare line per image of Docker Hub, built by nothing."""

REMEDY = (
    f"make mirror-sync copies the manifest ({MANIFEST}) into the files, then make mirror PUSH=yes "
    f"copies the new digests to the mirror; a person pushes both to the branch of the pull request"
)
"""The two gestures of a raise, which every drift names."""

# An image of Docker Hub pinned by digest, where a word starts: behind the registry of the mirror
# (the services of the workflows), behind the variable the chain poses (WATERFALL_MIRROR, the
# mirror and a slash, empty on the workstation), or bare. A name whose first part is a host
# (mcr.microsoft.com/…, ghcr.io/astral-sh/…) is another registry's, and not one.
PINNED = re.compile(
    r"(?<![\w./:@{}$-])(?P<prefix>"
    + re.escape(MIRROR)
    + r"/|\$\{WATERFALL_MIRROR(?::-)?\})?"
    + r"(?![a-z0-9-]+(?:\.[a-z0-9-]+)+(?::\d+)?/|localhost[:/])"
    + r"(?P<path>[a-z0-9][a-z0-9_.-]*(?:/[a-z0-9][a-z0-9_.-]*)*)"
    + r":(?P<tag>[A-Za-z0-9_][A-Za-z0-9_.-]*)@(?P<digest>sha256:[0-9a-f]{64})"
)
# A line of the manifest: FROM and the image, nothing else.
LINE = re.compile(r"^FROM\s+(?P<reference>.*?)\s*$", re.MULTILINE)
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

    @property
    def named(self) -> str:
        """Return the image as Docker Hub names it, which the manifest and the files write."""
        return f"{self.path}:{self.tag}@{self.digest}"


def _image(match: re.Match[str]) -> Mirrored:
    return Mirrored(match["path"], match["tag"], match["digest"])


def scanned(root: Path = REPOSITORY, patterns: Iterable[str] = SCANNED) -> list[Path]:
    """Return the files that name images of Docker Hub, the manifest aside, each once, in order."""
    manifest = root / MANIFEST
    return sorted(
        {
            path
            for pattern in patterns
            for path in root.glob(pattern)
            if path.is_file() and path != manifest
        }
    )


def referenced(root: Path = REPOSITORY, patterns: Iterable[str] = SCANNED) -> list[Mirrored]:
    """Return the images the files name under the mirror, each once, in order."""
    found: set[Mirrored] = set()
    for path in scanned(root, patterns):
        for match in PINNED.finditer(path.read_text(encoding="utf-8")):
            if match["prefix"]:
                found.add(_image(match))
    return sorted(found)


def manifest(root: Path = REPOSITORY) -> tuple[dict[str, Mirrored], list[str]]:
    """Return the images of the manifest by repository, and what is wrong with its lines."""
    images: dict[str, Mirrored] = {}
    wrong: list[str] = []
    path = root / MANIFEST
    if not path.is_file():
        return images, [f"{MANIFEST} is missing"]
    for line in LINE.finditer(path.read_text(encoding="utf-8")):
        match = PINNED.fullmatch(line["reference"])
        if match is None or match["prefix"]:
            reference = line["reference"]
            wrong.append(f"{MANIFEST}: FROM {reference} is not <image>:<tag>@sha256:…, bare")
        elif match["path"] in images:
            wrong.append(f"{MANIFEST}: {match['path']} is named twice")
        else:
            images[match["path"]] = _image(match)
    return images, wrong


def drift(root: Path = REPOSITORY, patterns: Iterable[str] = SCANNED) -> list[str]:
    """Say each reference that is not the manifest's, and each image of it nothing uses (US-2490).

    A reference is compared whatever its prefix — the mirror, its variable, none —, tag and digest.
    """
    images, wrong = manifest(root)
    used: set[str] = set()
    for path in scanned(root, patterns):
        text = path.read_text(encoding="utf-8")
        for match in PINNED.finditer(text):
            found = _image(match)
            used.add(found.path)
            where = f"{path.relative_to(root)}:{text.count(chr(10), 0, match.start()) + 1}"
            pinned = images.get(found.path)
            if pinned is None:
                wrong.append(f"{where}: {found.named} is not in {MANIFEST}")
            elif pinned != found:
                wrong.append(f"{where}: {found.named}, where {MANIFEST} has {pinned.named}")
    wrong.extend(
        f"{MANIFEST}: {image.named} is used by no file"
        for name, image in sorted(images.items())
        if name not in used
    )
    return wrong


def drifted(root: Path = REPOSITORY, patterns: Iterable[str] = SCANNED) -> str | None:
    """Return what drifts from the manifest and the two gestures that end it, None if nothing."""
    wrong = drift(root, patterns)
    return "\n".join([*wrong, REMEDY]) if wrong else None


def sync(root: Path = REPOSITORY, patterns: Iterable[str] = SCANNED) -> list[Path]:
    """Copy the manifest into the references of the files, their prefix kept; return those changed.

    An image the manifest does not name is left as it is: ``drift`` says it.
    """
    images, _ = manifest(root)

    def follow(match: re.Match[str]) -> str:
        pinned = images.get(match["path"])
        return f"{match['prefix'] or ''}{pinned.named}" if pinned else match[0]

    changed: list[Path] = []
    for path in scanned(root, patterns):
        text = path.read_text(encoding="utf-8")
        followed = PINNED.sub(follow, text)
        if followed != text:
            path.write_text(followed, encoding="utf-8")
            changed.append(path)
    return changed


def fill(
    image: Mirrored,
    *,
    read: Callable[[list[str]], tuple[int, str]],
    wait: Callable[[float], None],
) -> None:
    """Copy an image of Docker Hub to the mirror, by digest, and check the copy kept it.

    A copy that fails says who failed: ghcr.io when it refuses the write (``denied``, ``403``, in a
    message that names it), Docker Hub otherwise. ghcr.io has refused once the creation of a package
    it took on the next run (#3028): a refusal is tried again once, a second one fails.
    """
    command = ["docker", "buildx", "imagetools", "create", "--tag", image.tagged, image.source]
    said = ""
    refusals = 0
    for attempt in range(1, ATTEMPTS + 1):
        code, said = read(command)
        print(said, end="", file=sys.stderr)
        if code == 0:
            break
        if REFUSED.search(said) and REGISTRY in said:
            refusals += 1
            last = said.strip().splitlines()[-1]
            if refusals > 1 or attempt == ATTEMPTS:
                message = (
                    f"{REGISTRY} refused to write {image.tagged} ({last}): "
                    f"log in to {REGISTRY} with a token that writes packages"
                )
                raise ImageError(message)
            registry.again(attempt, f"{REGISTRY} refused to write {image.tagged}", wait, tool=TOOL)
            continue
        registry.again(attempt, "docker buildx failed", wait, tool=TOOL)
    else:
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
            fill(image, read=read, wait=wait)
    return missing


def _read(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return result.returncode, f"{result.stdout}{result.stderr}"


def main(
    arguments: Sequence[str],
    read: Callable[[list[str]], tuple[int, str]] = _read,
    wait: Callable[[float], None] = time.sleep,
    root: Path = REPOSITORY,
) -> int:
    """Check the mirror holds what the files name, and fill it with ``--push``; or ``sync``."""
    parser = argparse.ArgumentParser(prog=TOOL, description="The mirror of Docker Hub's images.")
    parser.add_argument(
        "action",
        nargs="?",
        choices=("ensure", "sync"),
        default="ensure",
        help="ensure the mirror holds the images (by default), or copy the manifest into the files",
    )
    parser.add_argument("--push", action="store_true", help="copy what the mirror does not hold")
    options = parser.parse_args(arguments)
    if options.action == "sync":
        if options.push:
            parser.error("--push does not go with sync")
        return _synced(root)
    images = referenced(root)
    if not images:
        print(f"{TOOL}: no image of the mirror is named in the files", file=sys.stderr)
        return 2
    refused: set[str] = set()

    def watching(command: list[str]) -> tuple[int, str]:
        # What ghcr.io refuses to show is not what it does not hold: the message tells them apart.
        code, answer = read(command)
        if code and REFUSED.search(answer) and not UNKNOWN_TAG.search(answer):
            refused.add(command[-1])
        return code, answer

    try:
        missing = ensure(images, push=options.push, read=watching, wait=wait)
    except ImageError as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"{TOOL}: {error.filename or 'docker'} could not run: {error}", file=sys.stderr)
        return 2
    if missing and not options.push:
        for image in missing:
            if image.pinned in refused:
                # ghcr.io refuses alike a reader not logged in and a package never created.
                what = (
                    f"{REGISTRY} refused to answer for {image.pinned}: either log in to "
                    f"{REGISTRY}, or the package is not copied yet (make mirror PUSH=yes)"
                )
            else:
                what = f"{image.pinned} is missing (make mirror PUSH=yes)"
            print(f"{TOOL}: {what}", file=sys.stderr)
        return 1
    print(f"{TOOL}: {len(images)} images, {len(missing)} copied", file=sys.stderr)
    return 0


def _synced(root: Path) -> int:
    """Copy the manifest into the files; fail on what that does not settle."""
    for path in sync(root):
        print(f"{TOOL}: {path.relative_to(root)} follows {MANIFEST}", file=sys.stderr)
    wrong = drift(root)
    for line in wrong:
        print(f"{TOOL}: {line}", file=sys.stderr)
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
