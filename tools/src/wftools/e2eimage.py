# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work image of the end-to-end paths, found or published, and a command played in it (US-1900).

Usage: ``python -m wftools.e2eimage publish [--push]`` and
``python -m wftools.e2eimage run --image <reference> -- <command>…``.

The image is Playwright's with make, the Python of the tools, pnpm and Docker's client
(``deploy/e2e/Dockerfile``): the jobs of the paths download no package of Ubuntu (#2913). It is
tagged by the hash of its directory, so that a tag names one content, never two. ``publish``, run by
the chain before the paths, asks the registry for that tag: held, it prints its reference by digest;
missing, it builds the image, and with ``--push`` publishes it, then prints that reference. A change
of the image is thus built once, by the first run of the chain that needs it — that of a pull
request in the merge queue, or of a branch run by hand —, and pulled by every other: the publication
after a merge (images.yml) would come after the first run that needs it; the fast tier builds it
without ``--push``. A registry that does not answer, a build or a publication that fails, is tried
again, then fails the run here, naming it, before any job of the paths starts. The line it prints,
``image=<reference>``, is the output of a step of GitHub Actions.

``run`` plays a command in the image, on the network of the host, until it ends or the tool is
stopped. service.yml serves the browser of the paths against the service so — Playwright's
server, which ``playwright test`` connects to from the runner (Makefile, e2e-service): the browser
reaches the front and Keycloak on the ports of the runner, which a job container does not see. The
checkout is mounted at its own path, so that every path the command is given reads the same inside,
and so is Docker's socket. The command is given the variables of the environment the paths read, by
name: their values never appear on a command line.

``run`` is made for a runner of the chain, not for a workstation: the command runs as root in the
image, and the files it writes in the checkout are root's; Docker's socket is the one at its usual
path, whatever DOCKER_HOST says. On a workstation the paths play without the image.
"""

import argparse
import hashlib
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from types import FrameType

REGISTRY = "ghcr.io"
"""The registry the image is published to and pulled from, which a failure names."""

NAME = f"{REGISTRY}/waterfall-project/e2e"
"""Where the image is published, beside the images of Waterfall (wftools.images)."""

CONTEXT = REPOSITORY / "deploy" / "e2e"
"""The directory the image is built from, and whose hash tags it."""

TAG_LENGTH = 16
"""The hexadecimal digits of the hash the tag keeps: 64 bits, enough to never meet twice."""

SOCKET = "/var/run/docker.sock"
"""Docker's socket on a runner, mounted at the same path in the image; DOCKER_HOST is not read."""

ATTEMPTS = 4
"""The attempts at a request to the registry, or at a build, before its failure is said (#2530)."""

PAUSE = 20.0
"""The seconds between two attempts, as curl waited between its own for the package of make."""

# The variables of the environment the paths and the front they start read: the settings of the
# platform and of the harness, those of Node and of Next, and two of the run itself. Never PATH,
# HOME or the variables of Playwright, which are the image's, nor NODE_OPTIONS or NODE_PATH, which
# would load in the image what the runner's Node was told to.
PASSED = re.compile(r"(?!NODE_(?:OPTIONS|PATH)$)(?:WATERFALL|E2E|NODE|NEXT)_[A-Z0-9_]+|CI|TZ")
# What the registry answers for a tag it does not hold.
UNKNOWN_TAG = re.compile(r"not found|manifest unknown|name unknown", re.IGNORECASE)
# What it answers for a package it does not hold yet, the first time, as for one it refuses to show:
# a refusal — `403 Forbidden`, or `requested access to the resource is denied`. The image is then
# built, and its publication says which it was.
REFUSED = re.compile(r"403 Forbidden|denied", re.IGNORECASE)
# The digest of the index or of the manifest, as `docker buildx imagetools inspect` says it.
DIGEST = re.compile(r"^Digest:\s+(sha256:[0-9a-f]{64})\s*$", re.MULTILINE)


class ImageError(Exception):
    """The image could not be found, built or published: the message says where it stopped."""


def tag(context: Path = CONTEXT) -> str:
    """Return the tag of the image: the hash of every file of its directory, path and content."""
    hashed = hashlib.sha256()
    for path in sorted(p for p in context.rglob("*") if p.is_file()):
        hashed.update(path.relative_to(context).as_posix().encode())
        hashed.update(b"\0")
        hashed.update(path.read_bytes())
        hashed.update(b"\0")
    return hashed.hexdigest()[:TAG_LENGTH]


def reference(context: Path = CONTEXT) -> str:
    """Return the name and tag of the image, as the chain asks the registry for it."""
    return f"{NAME}:{tag(context)}"


def held_digest(
    tagged: str,
    read: Callable[[list[str]], tuple[int, str]],
    wait: Callable[[float], None] = time.sleep,
) -> str | None:
    """Return the digest the registry holds for the tag, None if it does not hold it.

    A refusal is taken for a package not yet published: ghcr.io answers so for a name it does not
    hold, before the image is first published, and the publication that follows fails on a true
    refusal. Any other answer — the registry unreachable, a 5xx, a delay — is asked again,
    ATTEMPTS times in all, then is an error that names the registry and what it said last: the paths
    would not find their image either.
    """
    said = "nothing"
    for attempt in range(1, ATTEMPTS + 1):
        code, answer = read(["docker", "buildx", "imagetools", "inspect", tagged])
        said = (answer.strip().splitlines() or ["nothing"])[-1]
        if code == 0:
            if found := DIGEST.search(answer):
                return found.group(1)
            message = f"the registry held {tagged} but said no digest"
            raise ImageError(message)
        if UNKNOWN_TAG.search(answer):
            return None
        if REFUSED.search(answer):
            print(f"wftools.e2eimage: {REGISTRY} refused to show {tagged}: {said}", file=sys.stderr)
            return None
        _again(attempt, f"{REGISTRY} did not answer for {tagged}: {said}", wait)
    message = f"{REGISTRY} did not say whether it holds {tagged}, in {ATTEMPTS} attempts: {said}"
    raise ImageError(message)


def _again(attempt: int, what: str, wait: Callable[[float], None]) -> None:
    """Say a failed attempt, and wait before the next one; the last waits for nothing."""
    if attempt < ATTEMPTS:
        print(f"wftools.e2eimage: {what}; attempt {attempt + 1} in {PAUSE:g} s", file=sys.stderr)
        wait(PAUSE)


def _attempted(
    command: list[str], run: Callable[[list[str]], int], wait: Callable[[float], None]
) -> bool:
    """Run a command of Docker until it succeeds, ATTEMPTS times at most; say whether it did.

    A build tried again starts from the layers its cache kept: only the download that failed is done
    again — an archive, the package of make, the Python of uv, pnpm from npm.
    """
    for attempt in range(1, ATTEMPTS + 1):
        if run(command) == 0:
            return True
        _again(attempt, f"{' '.join(command[:2])} failed", wait)
    return False


def publish(
    *,
    push: bool,
    run: Callable[[list[str]], int],
    read: Callable[[list[str]], tuple[int, str]],
    context: Path = CONTEXT,
    wait: Callable[[float], None] = time.sleep,
) -> str:
    """Find the image in the registry, or build it — and publish it with ``push``; return its name.

    Held or published, the name is pinned by its digest; built without ``push``, it is its tag. Two
    runs of the merge queue that both miss the tag may both build and publish it, and the second
    replaces the first under the tag: the build is not reproducible to the byte, but each run reads
    the image it published by its digest, and the content the tag names — the files of the
    directory — is the same.
    """
    tagged = reference(context)
    if (digest := held_digest(tagged, read, wait)) is not None:
        print(f"wftools.e2eimage: {tagged} is in the registry", file=sys.stderr)
        return f"{tagged}@{digest}"
    print(f"wftools.e2eimage: {tagged} is not in the registry: built here", file=sys.stderr)
    if not _attempted(["docker", "build", "--tag", tagged, str(context)], run, wait):
        message = f"the build of {tagged} failed, in {ATTEMPTS} attempts"
        raise ImageError(message)
    if not push:
        return tagged
    if not _attempted(["docker", "push", tagged], run, wait):
        message = f"the publication of {tagged} to {REGISTRY} failed, in {ATTEMPTS} attempts"
        raise ImageError(message)
    if (digest := held_digest(tagged, read, wait)) is None:
        message = f"{REGISTRY} does not hold {tagged}, just published"
        raise ImageError(message)
    return f"{tagged}@{digest}"


def passed_names(environment: Mapping[str, str]) -> list[str]:
    """Return the names of the variables of the environment the command in the image is given."""
    return sorted(name for name in environment if PASSED.fullmatch(name))


def run_command(
    image: str, command: Sequence[str], directory: Path, environment: Mapping[str, str]
) -> list[str]:
    """Return the command of Docker that plays a command in the image, on the network of the host.

    The checkout is mounted at its own path and the command runs in the same directory as here; the
    variables are given by name, Docker reading their values from its own environment.
    """
    if not command:
        message = "no command to play in the image"
        raise ImageError(message)
    if not directory.is_relative_to(REPOSITORY):
        message = f"{directory} is outside the checkout, which alone is mounted"
        raise ImageError(message)
    passed = [option for name in passed_names(environment) for option in ("--env", name)]
    return [
        "docker",
        "run",
        "--rm",
        "--init",
        "--network",
        "host",
        # Chromium shares memory through /dev/shm, which Docker bounds to 64 MB (e2e.yml).
        "--ipc",
        "host",
        "--volume",
        f"{REPOSITORY}:{REPOSITORY}",
        "--volume",
        f"{SOCKET}:{SOCKET}",
        "--workdir",
        str(directory),
        *passed,
        image,
        *command,
    ]


def _run(command: list[str]) -> int:
    # What Docker prints goes to the error stream: the output is the line of the step.
    return subprocess.run(command, cwd=REPOSITORY, stdout=sys.stderr, check=False).returncode


def _read(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, check=False)
    return result.returncode, f"{result.stdout}{result.stderr}"


def _play(command: list[str]) -> int:
    # Stopped, the tool stops the command: Docker's client hands the signal on to the container,
    # which --rm then removes — the server of the browser the Makefile stops after the paths.
    with subprocess.Popen(command) as process:

        def stop(_signal: int, _frame: FrameType | None) -> None:
            process.terminate()

        stopped = signal.signal(signal.SIGTERM, stop)
        try:
            return process.wait()
        finally:
            signal.signal(signal.SIGTERM, stopped)


@dataclass(frozen=True)
class Docker:
    """The commands of Docker the tool runs, and its wait between two attempts: a test's own."""

    run: Callable[[list[str]], int] = _run
    """Run a command, what it prints on the error stream; return its code."""
    read: Callable[[list[str]], tuple[int, str]] = _read
    """Run a command; return its code and what it printed."""
    play: Callable[[list[str]], int] = _play
    """Play a command, on the streams of the tool; return its code."""
    wait: Callable[[float], None] = time.sleep
    """Wait so many seconds."""


def main(
    arguments: Sequence[str],
    docker: Docker | None = None,
    environment: Mapping[str, str] = os.environ,
) -> int:
    """Publish the image, or play a command in it; say where it stopped on failure."""
    docker = docker or Docker()
    parser = argparse.ArgumentParser(
        prog="wftools.e2eimage", description="The work image of the end-to-end paths."
    )
    commands = parser.add_subparsers(dest="action", required=True)
    publishing = commands.add_parser("publish", help="find the image, or build it")
    publishing.add_argument("--push", action="store_true", help="publish the image built")
    playing = commands.add_parser("run", help="play a command in the image")
    playing.add_argument("--image", required=True, help="the reference of the image")
    playing.add_argument("command", nargs=argparse.REMAINDER, help="the command, after --")
    options = parser.parse_args(arguments)
    try:
        if options.action == "publish":
            found = publish(push=options.push, run=docker.run, read=docker.read, wait=docker.wait)
            print(f"image={found}")
            return 0
        command = options.command[1:] if options.command[:1] == ["--"] else options.command
        return docker.play(run_command(options.image, command, Path.cwd(), environment))
    except ImageError as error:
        print(f"wftools.e2eimage: {error}", file=sys.stderr)
    except OSError as error:
        print(
            f"wftools.e2eimage: {error.filename or 'docker'} could not run: {error}",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
