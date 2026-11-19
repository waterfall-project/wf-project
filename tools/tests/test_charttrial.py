# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The trial of the chart on a cluster of kind, and the tools it pins (US-2800).

The cluster is made, the chart installed and the first administrator signed in by ``make
chart-trial`` in the full tier of the chain; these tests hold what the trial and the installation of
Helm, kind and kubectl decide by themselves, without a cluster nor a download.
"""

import base64
import hashlib
import io
import re
import tarfile
from typing import TYPE_CHECKING

import pytest

from wftools import chart, charttrial, kubetools
from wftools.charttrial import Tools, Trial, TrialError
from wftools.kubetools import Binary, ToolError
from wftools.production import Platform

if TYPE_CHECKING:
    from pathlib import Path

PLATFORM = Platform("waterfall.localhost", 41443, 0)


def archive(member: str, content: bytes) -> bytes:
    """Return a gzipped tarball holding one file."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as written:
        info = tarfile.TarInfo(member)
        info.size = len(content)
        written.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_a_tool_is_taken_from_its_archive_at_the_digest_pinned() -> None:
    payload = archive("linux-amd64/helm", b"the binary")
    binary = Binary(
        "helm",
        "1",
        "https://x/helm.tar.gz",
        hashlib.sha256(payload).hexdigest(),
        "linux-amd64/helm",
    )
    assert kubetools.extracted(binary, payload) == b"the binary"


def test_a_tool_that_is_the_release_itself_is_taken_as_it_is() -> None:
    binary = Binary("kind", "1", "https://x/kind", hashlib.sha256(b"kind").hexdigest())
    assert kubetools.extracted(binary, b"kind") == b"kind"


def test_a_download_of_another_digest_is_refused() -> None:
    binary = Binary("kind", "1", "https://x/kind", "0" * 64)
    with pytest.raises(ToolError, match="not the one pinned"):
        kubetools.extracted(binary, b"another")


def test_each_tool_lives_in_a_folder_of_its_version(tmp_path: Path) -> None:
    assert (
        kubetools.location(kubetools.BINARIES["helm"], tmp_path) == tmp_path / "helm-4.3.2" / "helm"
    )
    assert kubetools.cache({"XDG_CACHE_HOME": str(tmp_path)}) == tmp_path / "waterfall" / "bin"
    assert all(re.fullmatch(r"[0-9a-f]{64}", tool.sha256) for tool in kubetools.BINARIES.values())


def test_every_secret_is_drawn_in_the_form_it_is_asked() -> None:
    drawn = charttrial.drawn_secrets()
    assert set(drawn) == set(chart.SECRET_KEYS)
    # A password written in a URL holds letters and digits alone.
    assert drawn["WATERFALL_REDIS_PASSWORD"].isalnum()
    assert len(base64.b64decode(drawn["WATERFALL_SERVER_ACTIONS_KEY"])) == 32
    assert re.fullmatch(r"[0-9a-f]{64}", drawn["WATERFALL_STORAGE_RPC_SECRET"])
    assert charttrial.drawn_secrets() != drawn


def test_the_cluster_publishes_https_on_the_loopback_alone(tmp_path: Path) -> None:
    configuration = charttrial.cluster_configuration(41443, None)
    (node,) = configuration["nodes"]
    assert node["extraPortMappings"] == [
        {"containerPort": charttrial.NODE_PORT, "hostPort": 41443, "listenAddress": "127.0.0.1"}
    ]
    assert "extraMounts" not in node
    (node,) = charttrial.cluster_configuration(41443, tmp_path / "config.json")["nodes"]
    assert node["extraMounts"] == [
        {"hostPath": str(tmp_path / "config.json"), "containerPath": "/var/lib/kubelet/config.json"}
    ]


def test_the_node_pulls_with_the_credentials_of_docker_only_from_the_mirror(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    mirror = {
        "WATERFALL_MIRROR": "ghcr.io/waterfall-project/mirror/",
        "DOCKER_CONFIG": str(tmp_path),
    }
    assert charttrial.docker_config_of(mirror) == tmp_path / "config.json"
    assert charttrial.docker_config_of({"DOCKER_CONFIG": str(tmp_path)}) is None
    assert charttrial.docker_config_of({**mirror, "DOCKER_CONFIG": str(tmp_path / "none")}) is None


def test_the_front_reaches_the_published_name_at_the_ingress_inside_the_cluster() -> None:
    values = charttrial.chart_values("abc", PLATFORM, "10.96.0.7", {"WATERFALL_MIRROR": "m/"})
    assert values["platform"] == {"domain": "waterfall.localhost", "httpsPort": "41443"}
    assert values["images"] == {"tag": "abc", "mirror": "m/"}
    assert values["front"]["hostAliases"] == [
        {"ip": "10.96.0.7", "hostnames": ["waterfall.localhost"]}
    ]
    assert values["ingress"] == {"className": "traefik", "tlsSecret": charttrial.CERTIFICATE}
    assert values["transport"] == {"authority": charttrial.AUTHORITY}


def test_an_image_not_built_here_stops_the_trial_before_the_cluster_loads_any(
    tmp_path: Path,
) -> None:
    ran: list[list[str]] = []

    def run(command: list[str]) -> int:
        ran.append(command)
        return 1 if command[-1].endswith("/keycloak:abc") else 0

    trial = Trial(
        Tools(["kind"], ["kubectl"], ["helm"]), run, lambda _: (0, ""), tmp_path, PLATFORM
    )
    with pytest.raises(TrialError, match="keycloak:abc is not built here"):
        trial.load("cluster", "abc")
    assert not any(command[0] == "kind" for command in ran)
