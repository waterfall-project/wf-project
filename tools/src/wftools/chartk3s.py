# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The second distribution of the trial of the chart: k3s, in a container, thrown away (US-2810).

« Le chart s'installe sur deux distributions de Kubernetes différentes sans modification. »
(WF-CMP-0020-A): ``wftools.charttrial`` makes a cluster of kind, or, given
``WATERFALL_CHART_DISTRIBUTION=k3s``, one of k3s — a Kubernetes of another make, with another
runtime setup, another network plugin and another provisioner of volumes — and installs the chart on
it with the very same values. This module holds what differs: the container that is the node, its
access, its credentials for the mirror of the images, and the loading of the images built here.
The image of k3s is pinned by the digest of its manifest, as each binary of ``kubetools`` is;
Traefik is installed by the trial as on kind (k3s ships its own, which the trial leaves off).
"""

import json
import tempfile
import time
from base64 import b64decode
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from wftools.chartrun import Read, Run, TrialError, must

if TYPE_CHECKING:
    from collections.abc import Callable

K3S = (
    "rancher/k3s:v1.36.6-k3s1"
    "@sha256:88d3fac10eb4a429d3c5275f4868fe4b13620f6bbca5bdb5dca0627ac76ae2a0"
)
"""k3s for Kubernetes 1.36, by the digest of its manifest: not the Kubernetes of kind."""
NODE_PORT = 30443
"""The port of the node HTTPS is served on, which the container publishes on the loopback."""
API_PORT = 6443
CONFIGURATION = "/etc/rancher/k3s/k3s.yaml"
REGISTRIES = "/etc/rancher/k3s/registries.yaml"
WAIT = 180.0
"""How long the API of the new cluster is waited for, in seconds."""
STEP = 2.0
NODE_WAIT = 60.0
"""How long the node is waited to register with the API once it answers, in seconds.

Measured (US-2810/L4, #5103): the API answers ``/readyz`` before the kubelet has registered the
node, and ``kubectl wait --all`` then ends at once on « no matching resources found ». Locally the
node is listed 0.5 s after ``/readyz`` (five runs of the pinned image, 0.50 to 0.51 s); on the
runners of the chain the node was still missing 2.1 s after the last failed ``/readyz`` in three
passages (45913572822, 45935509708, 45937624908), and registered and Ready within 2.2 s of it in
the passage that held (45934597996). Nothing seen exceeds 2.5 s, so 60 s leaves a margin of more
than twenty times without hiding a node that never comes.
"""


class K3sError(Exception):
    """What keeps the cluster from being made."""


def registries(docker_config: Path | None) -> dict[str, Any] | None:
    """Return the credentials of k3s for the registries the user of Docker is signed in to.

    k3s reads them from its own file, not from the configuration of Docker kind is given: the
    mirror of the images (``ghcr.io``) wants the credentials the chain logs in with. ``None`` when
    there is none to give.
    """
    if docker_config is None:
        return None
    document = cast("dict[str, Any]", json.loads(docker_config.read_text(encoding="utf-8")))
    authorized = cast("dict[str, Any]", document.get("auths", {}))
    configs: dict[str, Any] = {}
    for registry, found in authorized.items():
        entry = cast("dict[str, Any]", found) if isinstance(found, dict) else {}
        if not entry.get("auth"):
            continue
        user, _, password = b64decode(str(entry["auth"])).decode().partition(":")
        configs[registry] = {"auth": {"username": user, "password": password}}
    return {"configs": configs} if configs else None


def node_command(name: str, https_port: int, api_port: int, folder: Path | None) -> list[str]:
    """Return the command that starts the node: privileged, as k3s asks of a container, alone.

    Traefik and the load balancer of k3s are left off: the trial installs Traefik itself, the
    same on both distributions, behind a NodePort the container publishes. ``folder`` holds
    ``registries.yaml`` when there are credentials to give.
    """
    command = [
        "docker",
        "run",
        "--detach",
        "--name",
        f"{name}-control-plane",
        "--privileged",
        "--tmpfs",
        "/run",
        "--tmpfs",
        "/var/run",
        "--publish",
        f"127.0.0.1:{https_port}:{NODE_PORT}",
        "--publish",
        f"127.0.0.1:{api_port}:{API_PORT}",
    ]
    if folder is not None:
        command += ["--volume", f"{folder / 'registries.yaml'}:{REGISTRIES}:ro"]
    return [
        *command,
        K3S,
        "server",
        "--disable=traefik",
        "--disable=servicelb",
        "--write-kubeconfig-mode=644",
    ]


def access(configuration: str, api_port: int) -> str:
    """Return the access k3s writes, its address the one the container publishes on the loopback."""
    return configuration.replace(f"https://127.0.0.1:{API_PORT}", f"https://127.0.0.1:{api_port}")


def wait_for(
    read: Read,
    command: list[str],
    what: str,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Run a command until it succeeds, for a while, and return what it wrote."""
    waited = 0.0
    while True:
        code, output = read(command)
        if code == 0:
            return output
        if waited >= WAIT:
            message = f"{what} failed ({code}) in {WAIT:.0f} s"
            raise K3sError(message)
        sleep(STEP)
        waited += STEP


def wait_for_node(
    read: Read,
    command: list[str],
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Wait until the API lists a node, which ``kubectl wait --all`` does not do itself.

    ``kubectl wait`` over ``--all`` ends at once, in error, when no resource matches: it does not
    wait for one to appear. The node registers a moment after the API answers, so it is listed
    again, for ``NODE_WAIT`` seconds, until the output is not empty.
    """
    waited = 0.0
    while True:
        code, output = read([*command, "get", "nodes", "--output", "name"])
        if code == 0 and output.strip():
            return
        if waited >= NODE_WAIT:
            message = f"wait for the node to register failed ({code}) in {NODE_WAIT:.0f} s"
            raise K3sError(message)
        sleep(STEP)
        waited += STEP


def create(
    commands: tuple[Run, Read],
    kubectl: tuple[list[str], Path],
    name: str,
    ports: tuple[int, int],
    docker_config: Path | None,
) -> None:
    """Make the cluster as a container of k3s, and write the access to it once it answers.

    ``kubectl`` is the command and the file the access is written to, which the trial reads from;
    ``ports`` are those the platform and the API are published on. The container is
    ``<name>-control-plane``, as kind names the node of its cluster.
    """
    run, read = commands
    command, access_file = kubectl
    https_port, api_port = ports
    folder = access_file.parent
    credentials = registries(docker_config)
    if credentials is not None:
        (folder / "registries.yaml").write_text(json.dumps(credentials), encoding="utf-8")
    must(
        run,
        node_command(name, https_port, api_port, folder if credentials is not None else None),
        "start the node of k3s",
    )
    try:
        written = wait_for(
            read,
            ["docker", "exec", f"{name}-control-plane", "cat", CONFIGURATION],
            "read the access to the cluster",
        )
        access_file.write_text(access(written, api_port), encoding="utf-8")
        wait_for(read, [*command, "get", "--raw", "/readyz"], "wait for the API")
        wait_for_node(read, command)
    except K3sError as error:
        raise TrialError(str(error)) from error
    must(
        run,
        [*command, "wait", "--for=condition=Ready", "node", "--all", "--timeout", "5m"],
        "wait for the node",
    )


def import_images(run: Run, node: str, references: list[str]) -> None:
    """Load the images built here into the node of k3s, as ``kind load`` does into kind's."""
    with tempfile.TemporaryDirectory(prefix="waterfall-k3s-images-") as folder:
        archive = Path(folder) / "images.tar"
        must(run, ["docker", "save", "--output", str(archive), *references], "save the images")
        must(run, ["docker", "cp", str(archive), f"{node}:/images.tar"], "copy the images")
    must(
        run,
        ["docker", "exec", node, "ctr", "--namespace=k8s.io", "images", "import", "/images.tar"],
        "load the images into the cluster",
    )
