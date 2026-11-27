# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The images of Waterfall in the cluster of the trial of the chart (US-2800).

The images built on the workstation (``make images``) are loaded into the node of kind or of k3s,
and each is named there by its digest too: the chart designates the images so (#3726), and the
kubelet finds them by it. ``wftools.charttrial`` calls this module once the cluster is made.
"""

import time
from typing import TYPE_CHECKING, NamedTuple

from wftools import chartk3s
from wftools.chartrun import Read, Run, TrialError, must, output
from wftools.images import DIGEST, REGISTRY

if TYPE_CHECKING:
    from collections.abc import Callable

IMAGES = ("front", "waterfall", "keycloak")
FIND_WAIT = 10.0
"""How long the runtime of the node is given to know an image by its digest, once ``ctr`` named it.

Measured on a node of kind (2026-11-27, #5065, containerd 2.3.4): ``crictl inspecti`` found the
name at its first try, 0.12 s after ``ctr tag`` — a ``docker exec`` included — in 60 of 60 tags,
and under a load of two busy loops per processor it did so in 90 of 90, in 0.7 s at most. The race
the queue met twice (``no such image`` 120 ms after the tag) did not reproduce on the
workstation, so the bound is not measured against it: it is a margin, some fifteen times the worst
delay measured, for a node a loaded runner slows down; a name still unknown after it is another
fault.
"""
FIND_STEP = 0.5
"""The pause between two tries of ``crictl inspecti``."""


class Waiting(NamedTuple):
    """The clock and the pause of the wait for the runtime: a test gives its own."""

    clock: Callable[[], float]
    sleep: Callable[[float], None]


REAL = Waiting(time.monotonic, time.sleep)


def load(
    commands: tuple[Run, Read],
    kind: list[str] | None,
    name: str,
    tag: str,
) -> dict[str, str]:
    """Load the images of the tag, built on the workstation, into the cluster.

    ``kind`` is the command of kind, or ``None`` for a cluster of k3s. Return the digest of each,
    as the runtime of the node holds it: the chart designates them so (#3726), and the kubelet
    finds them by it.
    """
    run = commands[0]
    references = {image: f"{REGISTRY}/{image}:{tag}" for image in IMAGES}
    for reference in references.values():
        if run(["docker", "image", "inspect", "--format", "{{.Id}}", reference]):
            message = f"{reference} is not built here: make images first"
            raise TrialError(message)
    if kind is None:
        chartk3s.import_images(run, f"{name}-control-plane", list(references.values()))
    else:
        must(
            run,
            [*kind, "load", "docker-image", "--name", name, *references.values()],
            "load the images into the cluster",
        )
    return {
        image: digest(commands, f"{name}-control-plane", reference)
        for image, reference in references.items()
    }


def digest(
    commands: tuple[Run, Read],
    node: str,
    reference: str,
    waiting: Waiting = REAL,
) -> str:
    """Make the node hold an image by its digest too, and return it.

    ``kind load`` leaves an image under its tag, and ``crictl`` names no digest of it but the
    import's: the kubelet would not find ``name@sha256:…``. ``ctr`` lists the digest of the
    image under the tag, the node is told to name it so, and the runtime to find it.

    The runtime is not told at once. The CRI plugin of containerd, which ``crictl`` and the kubelet
    ask, keeps an image store of its own, refreshed from the events of images of containerd (the
    log of the node shows an ``ImageCreate`` and an ``ImageUpdate`` event for the new name): ``ctr
    tag`` returns when containerd has written the name, before the plugin has handled the event,
    and a ``crictl inspecti`` run right after sometimes finds ``no such image`` (#5065: 120 ms
    after the tag, on kind and on k3s). It is asked again every ``FIND_STEP`` seconds, for
    ``FIND_WAIT``, with the clock and the pause of ``waiting``.
    """
    run, read = commands
    containerd = ["docker", "exec", node, "ctr", "--namespace=k8s.io", "images"]
    listing = [*containerd, "ls", f"name=={reference}"]
    listed = output(read, listing, f"read the digest of {reference}")
    if not (found := DIGEST.search(listed)):
        message = f"the cluster holds {reference} by no digest"
        raise TrialError(message)
    named = f"{reference.rsplit(':', 1)[0]}@{found.group(0)}"
    tag = [*containerd, "tag", "--force", reference, named]
    must(run, tag, f"name {named} by its digest")
    find = ["docker", "exec", node, "crictl", "inspecti", named]
    began = waiting.clock()
    while (code := (answer := read(find))[0]) != 0:
        if (waited := waiting.clock() - began) >= FIND_WAIT:
            message = (
                f"find {named} in the cluster failed ({code}) in {waited:.0f} s: "
                f"{answer[1].strip()}"
            )
            raise TrialError(message)
        waiting.sleep(FIND_STEP)
    return found.group(0)
