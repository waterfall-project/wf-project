# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The throwaway registry the trial of the production platform reads the digests of its images from.

The Compose of production designates each image by its digest (``name@sha256:…``, #3726), which an
image built here and never pushed does not have: a Docker with the classic store gives it no
``RepoDigests``, and Compose would try to pull it from ghcr.io, where the commit of a pull request
is not published. The trial (``make check-production``, US-2800) therefore starts a registry that
lives for the run (``deploy/compose/compose.registry.local.yaml``, on 127.0.0.1 and a port Docker
picks), pushes the three images to it, reads the digest each push says, and starts the platform
from that registry (``WATERFALL_REGISTRY``) by those digests, as an operator does from ghcr.io.
"""

import re
from typing import TYPE_CHECKING

from wftools import REPOSITORY
from wftools.images import IMAGES, Image, reference

if TYPE_CHECKING:
    from collections.abc import Callable

    Run = Callable[..., int]
    Read = Callable[[list[str]], tuple[int, str]]

COMPOSE = REPOSITORY / "deploy" / "compose" / "compose.registry.local.yaml"
PROJECT = "waterfall-production-registry"
PORT = 5000
NAMESPACE = "waterfall-project"
"""The path of the images in the registry of the trial, as it is ghcr.io's."""
ADDRESS = re.compile(r"(?:127\.0\.0\.1|\[::1\]|0\.0\.0\.0):(?P<port>\d+)\s*$")
# What ``docker push`` says of the manifest it wrote: ``<tag>: digest: sha256:… size: …``.
PUSHED = re.compile(r"\bdigest: (?P<digest>sha256:[0-9a-f]{64})\b")


class RegistryError(Exception):
    """The registry of the trial that does not start, or an image it does not take."""


def compose(project: str) -> list[str]:
    """Return the command of Compose for the registry of the trial."""
    return ["docker", "compose", "--project-name", project, "--file", str(COMPOSE)]


def start(run: Run, read: Read, project: str = PROJECT) -> str:
    """Start the registry; return the address Docker reaches it at, ``localhost:<port>``."""
    if code := run([*compose(project), "up", "--detach", "--wait", "--quiet-pull"]):
        message = f"the registry of the trial does not start (exit {code})"
        raise RegistryError(message)
    code, said = read([*compose(project), "port", "registry", str(PORT)])
    if code != 0 or not (found := ADDRESS.search(said.strip())):
        message = f"the registry of the trial gives no port: {said.strip()!r}"
        raise RegistryError(message)
    return f"localhost:{found['port']}"


def stop(run: Run, project: str = PROJECT) -> None:
    """Remove the registry, and what it holds."""
    run([*compose(project), "down", "--volumes"])


def pushed(image: Image, tag: str, address: str, read: Read) -> str:
    """Push an image built here to the registry of the trial; return the digest it says."""
    source, target = reference(image, tag), f"{address}/{NAMESPACE}/{image.package}:{tag}"
    if read(["docker", "tag", source, target])[0] != 0:
        message = f"{source} is not built here: make images first, or give the digests"
        raise RegistryError(message)
    code, said = read(["docker", "push", target])
    if code != 0 or not (found := PUSHED.search(said)):
        last = (said.strip().splitlines() or ["nothing"])[-1]
        message = f"the registry of the trial does not take {target}: {last}"
        raise RegistryError(message)
    return found["digest"]


def publish(tag: str, address: str, read: Read) -> dict[str, str]:
    """Push the three images of the tag to the registry; return the digest of each, by name."""
    return {image.name: pushed(image, tag, address, read) for image in IMAGES}


def location(address: str) -> str:
    """Return what ``WATERFALL_REGISTRY`` says to the Compose: where the images of the trial are."""
    return f"{address}/{NAMESPACE}"
