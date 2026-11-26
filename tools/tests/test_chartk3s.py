# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The trial of the chart on k3s, the second distribution (US-2810).

« Le chart s'installe sur deux distributions de Kubernetes différentes sans modification. »
(WF-CMP-0020-A): ``make chart-trial-k3s`` makes a cluster of k3s in a container and installs the
chart on it with the values of kind, in the full tier of the chain. These tests hold what the trial
decides by itself, without a cluster nor a container.
"""

import base64
import json
import re
from typing import TYPE_CHECKING

import pytest

from wftools import chartk3s, charttrial
from wftools.chartrun import TrialError
from wftools.charttrial import Tools, Trial
from wftools.production import Platform

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-CMP-0020-A"), pytest.mark.story("US-2810")]

PLATFORM = Platform("waterfall.localhost", 41443, 0)


def test_k3s_is_pulled_by_the_digest_of_its_manifest_and_is_not_the_kubernetes_of_kind() -> None:
    assert re.search(r"@sha256:[0-9a-f]{64}$", chartk3s.K3S)
    assert "v1.36." in chartk3s.K3S
    assert "v1.37." in charttrial.NODE


def test_the_node_is_a_privileged_container_that_publishes_https_and_the_api_on_the_loopback() -> (
    None
):
    command = chartk3s.node_command("c", 41443, 41444, None)
    assert command[:3] == ["docker", "run", "--detach"]
    assert command[command.index("--name") + 1] == "c-control-plane"
    assert "--privileged" in command
    published = [command[at + 1] for at, word in enumerate(command) if word == "--publish"]
    assert published == ["127.0.0.1:41443:30443", "127.0.0.1:41444:6443"]
    assert command[command.index(chartk3s.K3S) :] == [
        chartk3s.K3S,
        "server",
        "--disable=traefik",
        "--disable=servicelb",
        "--write-kubeconfig-mode=644",
    ]
    assert "--volume" not in command


def test_the_credentials_of_the_mirror_are_given_to_k3s_in_its_own_file(tmp_path: Path) -> None:
    command = chartk3s.node_command("c", 1, 2, tmp_path)
    assert command[command.index("--volume") + 1] == (
        f"{tmp_path / 'registries.yaml'}:/etc/rancher/k3s/registries.yaml:ro"
    )


def test_the_credentials_of_docker_become_those_of_k3s_and_none_means_none(tmp_path: Path) -> None:
    assert chartk3s.registries(None) is None
    config = tmp_path / "config.json"
    auth = base64.b64encode(b"robot:s3:cret").decode()
    config.write_text(
        json.dumps({"auths": {"ghcr.io": {"auth": auth}, "other.io": {}}}), encoding="utf-8"
    )
    assert chartk3s.registries(config) == {
        "configs": {"ghcr.io": {"auth": {"username": "robot", "password": "s3:cret"}}}
    }
    config.write_text(json.dumps({"auths": {}}), encoding="utf-8")
    assert chartk3s.registries(config) is None


def test_the_access_k3s_writes_is_pointed_at_the_port_the_container_publishes() -> None:
    written = "server: https://127.0.0.1:6443\n"
    assert chartk3s.access(written, 41444) == "server: https://127.0.0.1:41444\n"


def test_a_cluster_that_never_answers_stops_the_trial_naming_what_it_waited_for() -> None:
    slept: list[float] = []
    with pytest.raises(chartk3s.K3sError, match=r"read the access failed \(1\)"):
        chartk3s.wait_for(lambda _: (1, ""), ["cat"], "read the access", slept.append)
    assert sum(slept) == chartk3s.WAIT


def test_a_cluster_that_answers_late_is_waited_for() -> None:
    answers = iter([(1, ""), (1, ""), (0, "ready")])
    assert chartk3s.wait_for(lambda _: next(answers), ["cat"], "x", lambda _: None) == "ready"


def trial_of(tmp_path: Path, ran: list[list[str]], *, fails: str = "") -> Trial:
    def run(command: list[str]) -> int:
        ran.append(command)
        return 1 if fails and fails in command else 0

    def read(command: list[str]) -> tuple[int, str]:
        ran.append(command)
        return 0, "server: https://127.0.0.1:6443\n"

    return Trial(
        Tools(["kind"], ["kubectl", "--kubeconfig", "k"], ["helm"]),
        run,
        read,
        tmp_path,
        PLATFORM,
        distribution=charttrial.K3S,
        api_port=41444,
    )


def test_a_cluster_of_k3s_is_a_container_not_a_cluster_of_kind(tmp_path: Path) -> None:
    ran: list[list[str]] = []
    trial = trial_of(tmp_path, ran)
    trial.create("c", None)
    assert ran[0][:3] == ["docker", "run", "--detach"]
    assert not any(command[0] == "kind" for command in ran)
    assert (tmp_path / "kubeconfig").read_text(encoding="utf-8") == (
        "server: https://127.0.0.1:41444\n"
    )
    assert ["kubectl", "--kubeconfig", "k", "get", "--raw", "/readyz"] in ran
    trial.delete("c")
    assert ran[-1] == ["docker", "rm", "--force", "--volumes", "c-control-plane"]


def test_the_images_are_loaded_into_the_node_of_k3s_by_its_containerd() -> None:
    ran: list[list[str]] = []

    def run(command: list[str]) -> int:
        ran.append(command)
        return 0

    chartk3s.import_images(run, "c-control-plane", ["a:1", "b:1"])
    assert ran[0][:3] == ["docker", "save", "--output"]
    assert ran[0][-2:] == ["a:1", "b:1"]
    assert ran[1][:2] == ["docker", "cp"]
    assert ran[1][-1] == "c-control-plane:/images.tar"
    assert ran[2] == [
        "docker",
        "exec",
        "c-control-plane",
        "ctr",
        "--namespace=k8s.io",
        "images",
        "import",
        "/images.tar",
    ]


def test_a_node_that_does_not_start_is_named_by_what_it_was_for(tmp_path: Path) -> None:
    trial = trial_of(tmp_path, [], fails="--detach")
    with pytest.raises(TrialError, match=r"^start the node of k3s failed \(1\)$"):
        trial.create("c", None)


def test_a_distribution_that_is_neither_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert charttrial.main({"WATERFALL_CHART_DISTRIBUTION": "minikube"}) == 2
    assert "minikube is none of kind, k3s" in capsys.readouterr().err
