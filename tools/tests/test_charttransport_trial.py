# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The trial of the chart holds that nothing of it accepts the clear, inside its cluster (US-2840).

« Aucune connexion en clair n'est acceptée par un composant de la plateforme, hors le point de
métriques, qui n'est pas joignable hors du cluster. » (WF-SEC-0010-A). ``make chart-trial`` runs the
probe of ``wftools.transport`` in the container of the API, on the cluster of kind, as ``make
production-trial`` runs it on the Compose: these tests hold the plan it is given — the Services
of the chart, their ports, the addresses of the pods of what must not be reached — and what the
trial concludes from what the probe answers. Those that render the chart are selected by the
marker ``chart`` (``make test-chart``): they need Helm.
"""

import json
import re
import tomllib
from typing import TYPE_CHECKING

import pytest
from test_chart import Objects, of_kind, rendered

from wftools import chart, charttrial, transport
from wftools.charttrial import Tools, Trial, TrialError
from wftools.production import Platform

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-SEC-0010-A")]

PODS = {
    "api": "10.244.0.11",
    "keycloak": "10.244.0.12",
    "storage": "10.244.0.13",
    "front": "10.1.0.4",
}
PLAN = charttrial.chart_plan(PODS)
REFUSED = PLAN.expected()


class Cluster:
    """A cluster that answers as a test tells it, and records what it is asked."""

    def __init__(self, said: dict[str, str]) -> None:
        self.said = said
        self.read: list[list[str]] = []

    def answer(self, command: list[str]) -> tuple[int, str]:
        self.read.append(command)
        if "exec" in command:
            return 0, json.dumps(self.said)
        component = re.search(r"component=(\w+)", " ".join(command))
        assert component is not None
        return 0, PODS[component.group(1)]


def trial_of(cluster: Cluster, folder: Path) -> Trial:
    return Trial(
        Tools(["kind"], ["kubectl"], ["helm"]),
        lambda _: 0,
        cluster.answer,
        folder,
        Platform("waterfall.localhost", 41443, 0),
    )


def test_the_trial_runs_the_probe_in_the_container_of_the_api_on_the_plan_of_the_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cluster = Cluster(REFUSED)
    trial_of(cluster, tmp_path).hold_transport()
    probe = cluster.read[-1]
    exec_at = probe.index("exec")
    assert probe[exec_at : exec_at + 3] == ["exec", f"deployment/{chart.RELEASE}-api", "--"]
    assert probe[exec_at + 3 :] == PLAN.command()
    assert probe[:exec_at] == ["kubectl", "--namespace", charttrial.NAMESPACE]
    # The pods that hold what must not be reached are read before, among those that run.
    for command in cluster.read[:-1]:
        assert "status.phase=Running" in command
    said = capsys.readouterr().out
    assert "postgres, redis, api, keycloak, keycloak-management, storage" in said
    assert "refuse a connection in the clear, and serve in TLS" in said


@pytest.mark.parametrize(
    ("name", "said"),
    [
        ("postgres", "accepted"),
        ("redis", "no tls"),
        ("grafana", "accepted"),
        ("front", "unreached"),
        ("keycloak-management", "accepted"),
        ("keycloak-http", "accepted"),
        ("garage", "accepted"),
        ("front-http", "accepted"),
        ("api-metrics", "accepted"),
    ],
)
def test_the_trial_fails_naming_a_listener_of_the_chart_that_does_not_refuse_the_clear(
    tmp_path: Path, name: str, said: str
) -> None:
    with pytest.raises(TrialError, match=f"not refused as it must be: {name} {said}$"):
        trial_of(Cluster({**REFUSED, name: said}), tmp_path).hold_transport()


def test_the_trial_fails_when_a_server_of_the_chart_is_not_tried(tmp_path: Path) -> None:
    left = {name: verdict for name, verdict in REFUSED.items() if name != "alertmanager"}
    with pytest.raises(TrialError, match="alertmanager not tried"):
        trial_of(Cluster(left), tmp_path).hold_transport()


def test_the_probe_reads_the_plan_it_is_given() -> None:
    compile(transport.PROBE, "probe", "exec")
    read = json.loads(PLAN.argument())
    assert read["served"] == {name: list(address) for name, address in PLAN.served.items()}
    assert read["closed"]["garage"] == [PODS["storage"], 3902]
    assert read["metrics"] == [PODS["api"], 8000]
    # The Compose is tried by the same probe, on its own plan.
    assert transport.COMPOSE.command()[:3] == ["python", "-c", transport.PROBE]


@pytest.mark.chart
def test_the_plan_names_each_server_of_the_chart_by_its_service_and_its_port() -> None:
    objects: Objects = rendered()
    services = of_kind(objects, "Service")
    for name, (host, port) in [
        ("postgres", PLAN.postgres),
        ("redis", PLAN.redis),
        *PLAN.served.items(),
    ]:
        component = host.removeprefix(f"{chart.RELEASE}-")
        assert component in services, name
        ports = [each["port"] for each in services[component]["spec"]["ports"]]
        assert port in ports, name
    # Every server of the chart in TLS is tried: none of the Services that route is left out.
    routing = {
        component for component, item in services.items() if item["spec"].get("clusterIP") != "None"
    }
    tried = {host.removeprefix(f"{chart.RELEASE}-") for host, _ in PLAN.served.values()}
    assert routing == tried | {"postgres", "redis"}


@pytest.mark.chart
def test_what_must_not_be_reached_is_where_the_chart_puts_it() -> None:
    objects: Objects = rendered()
    garage = tomllib.loads(of_kind(objects, "ConfigMap")["storage"]["data"]["garage.toml"])
    assert garage["s3_api"]["api_bind_addr"] == f"127.0.0.1:{PLAN.closed['garage'][1]}"
    assert garage["rpc_bind_addr"] == f"127.0.0.1:{PLAN.closed['garage-rpc'][1]}"
    api = of_kind(objects, "Deployment")["api"]["spec"]["template"]["spec"]["containers"][0]
    metrics = {each["name"]: each["containerPort"] for each in api["ports"]}["metrics"]
    assert metrics == PLAN.metrics[1]
