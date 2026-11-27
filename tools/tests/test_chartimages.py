# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The images of Waterfall in the cluster of the trial of the chart (US-2800).

What the trial decides by itself about loading the images and naming them by their digest, without
a cluster: the commands are recorded, and the answers of the node are given.
"""

from typing import TYPE_CHECKING

import pytest

from wftools import chartimages
from wftools.chartrun import TrialError

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = [pytest.mark.requirement("WF-ARC-0050-A"), pytest.mark.story("US-2800")]

KIND = ["kind"]


def listing(reference: str, digest: str) -> str:
    """Return what ``ctr images ls name==…`` says of an image the node holds under a tag."""
    row = f"{reference} application/vnd.oci.image.index.v1+json {digest} 75.8 MiB linux/amd64 -"
    return f"REF TYPE DIGEST SIZE PLATFORMS LABELS\n{row}\n"


def test_an_image_not_built_here_stops_the_trial_before_the_cluster_loads_any() -> None:
    ran: list[list[str]] = []

    def run(command: list[str]) -> int:
        ran.append(command)
        return 1 if command[-1].endswith("/keycloak:abc") else 0

    with pytest.raises(TrialError, match="keycloak:abc is not built here"):
        chartimages.load((run, lambda _: (0, "")), KIND, "cluster", "abc")
    assert not any(command[0] == "kind" for command in ran)


def test_the_chart_designates_the_images_by_the_digests_the_cluster_holds_them_by() -> None:
    # ``kind load`` leaves an image under its tag alone, and ``crictl`` names its digest after the
    # import, not after the image: the digest is read from containerd, the node told to name the
    # image by it, and the runtime asked to find it so — what the kubelet does for the pod.
    asked: list[list[str]] = []
    ran: list[list[str]] = []
    held = {name: f"sha256:{index:064x}" for index, name in enumerate(chartimages.IMAGES, start=1)}

    def read(command: list[str]) -> tuple[int, str]:
        asked.append(command)
        if "ls" in command:
            reference = command[-1].removeprefix("name==")
            return 0, listing(reference, held[reference.rsplit("/", 1)[1].split(":")[0]])
        return 0, "{}"

    def run(command: list[str]) -> int:
        ran.append(command)
        return 0

    assert chartimages.load((run, read), KIND, "cluster", "abc") == held
    node = ["docker", "exec", "cluster-control-plane"]
    ctr = [*node, "ctr", "--namespace=k8s.io", "images"]
    for name, digest in held.items():
        tagged = f"ghcr.io/waterfall-project/{name}"
        assert [*ctr, "ls", f"name=={tagged}:abc"] in asked
        assert [*ctr, "tag", "--force", f"{tagged}:abc", f"{tagged}@{digest}"] in ran
        assert [*node, "crictl", "inspecti", f"{tagged}@{digest}"] in asked


def test_an_image_the_cluster_holds_by_no_digest_stops_the_trial() -> None:
    def read(_: list[str]) -> tuple[int, str]:
        return 0, "REF TYPE DIGEST SIZE PLATFORMS LABELS\n"

    with pytest.raises(TrialError, match=r"front:abc by no digest"):
        chartimages.load((lambda _: 0, read), KIND, "cluster", "abc")


class Time:
    """A clock that only the pauses move: nothing sleeps for real."""

    def __init__(self) -> None:
        self.now = 0.0
        self.pauses = 0

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        self.pauses += 1

    def waiting(self) -> chartimages.Waiting:
        return chartimages.Waiting(lambda: self.now, self.sleep)


def node(unknown: int) -> Callable[[list[str]], tuple[int, str]]:
    """Return a node whose runtime knows the name only after ``unknown`` tries of ``inspecti``."""
    tries: list[list[str]] = []

    def read(command: list[str]) -> tuple[int, str]:
        if "ls" in command:
            return 0, listing(command[-1].removeprefix("name=="), f"sha256:{'b' * 64}")
        tries.append(command)
        return (0, "{}") if len(tries) > unknown else (1, "no such image")

    return read


def test_an_image_the_runtime_knows_after_a_few_tries_is_found() -> None:
    # #5065: ``ctr tag`` returns before the CRI plugin has the new name.
    clock = Time()
    found = chartimages.digest(
        (lambda _: 0, node(3)), "n", "ghcr.io/waterfall-project/front:abc", clock.waiting()
    )
    assert found == f"sha256:{'b' * 64}"
    assert clock.pauses == 3


def test_an_image_the_runtime_never_finds_stops_the_trial_after_the_bound() -> None:
    clock = Time()
    with pytest.raises(
        TrialError,
        match=rf"find .*front@sha256:{'b' * 64} in the cluster failed \(1\) in 10 s: no such image",
    ):
        chartimages.digest(
            (lambda _: 0, node(10**6)), "n", "ghcr.io/waterfall-project/front:abc", clock.waiting()
        )
    assert clock.now == chartimages.FIND_WAIT
