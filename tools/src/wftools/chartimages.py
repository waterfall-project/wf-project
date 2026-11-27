# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The images of Waterfall in the cluster of the trial of the chart (US-2800).

The images built on the workstation (``make images``) are loaded into the node of kind or of k3s,
and each is named there by its digest too: the chart designates the images so (#3726), and the
kubelet finds them by it. ``wftools.charttrial`` calls this module once the cluster is made.
"""

from wftools import chartk3s
from wftools.chartrun import Read, Run, TrialError, must, output
from wftools.images import DIGEST, REGISTRY

IMAGES = ("front", "waterfall", "keycloak")


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
    run, read = commands
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


def digest(commands: tuple[Run, Read], node: str, reference: str) -> str:
    """Make the node hold an image by its digest too, and return it.

    ``kind load`` leaves an image under its tag, and ``crictl`` names no digest of it but the
    import's: the kubelet would not find ``name@sha256:…``. ``ctr`` lists the digest of the
    image under the tag, the node is told to name it so, and the runtime to find it.
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
    output(read, find, f"find {named} in the cluster")
    return found.group(0)
