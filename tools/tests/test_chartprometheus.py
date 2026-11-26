# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Prometheus in the chart, and what the supervision needs of the other pods (US-2880, #4229).

The chart runs the Prometheus of compose.prod.yaml, on the rules of the Compose and the thresholds
of its values, and finds the front, the API and the worker by headless Services. What these tests
render is checked by promtool, that of the release the platform runs; the rules are played in
test_alerts.py. Selected by the marker ``chart`` (``make test-chart``): they need Helm.
"""

import ipaddress
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_alerts import by_compose, promtool

from wftools import REPOSITORY, chart
from wftools.chart import ChartError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.chart]

PRODUCTION = REPOSITORY / "deploy" / "compose" / "compose.prod.yaml"
MIRROR = "${WATERFALL_MIRROR:-}"
# The thresholds and the window the chart ships, as the API reads them (WF-OBS-0030).
SHIPPED = {
    "WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS": "900",
    "WATERFALL_STORAGE_USAGE_THRESHOLD": "0.85",
    "WATERFALL_ERROR_RATE_THRESHOLD": "0.05",
    "WATERFALL_ERROR_RATE_WINDOW_SECONDS": "300",
}

Objects = list[dict[str, Any]]


def rendered(values: dict[str, Any] | None = None) -> Objects:
    """Render the chart with the values of the chain and those given."""
    return [document for document in yaml.safe_load_all(chart.render(values)) if document]


def named(objects: Objects, kind: str, component: str) -> dict[str, Any]:
    """Give the object of a kind of a component."""
    (found,) = [
        item
        for item in objects
        if item["kind"] == kind
        and item["metadata"]["labels"]["app.kubernetes.io/component"] == component
    ]
    return found


def container(objects: Objects, kind: str, component: str) -> dict[str, Any]:
    """Give the first container of the pods of a workload."""
    return named(objects, kind, component)["spec"]["template"]["spec"]["containers"][0]


def environment(item: dict[str, Any]) -> dict[str, Any]:
    """Give the variables of a container: a value, or where it is read from."""
    return {
        variable["name"]: variable.get("value", variable.get("valueFrom"))
        for variable in item["env"]
    }


@pytest.fixture(scope="module")
def objects() -> Objects:
    return rendered()


def configuration(objects: Objects) -> dict[str, str]:
    """Give the configuration and the rules of Prometheus the chart renders."""
    return named(objects, "ConfigMap", "prometheus")["data"]


@pytest.mark.story("US-2880")
def test_the_chart_runs_prometheus_on_a_configuration_promtool_accepts(
    objects: Objects, tmp_path: Path
) -> None:
    # Proper to US-2880: the platform delivers Prometheus, which collects and evaluates the rules,
    # by the chart as by the Compose: the same image, its series in a volume of its own.
    prometheus = container(objects, "StatefulSet", "prometheus")
    image = yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]["prometheus"][
        "image"
    ]
    assert prometheus["image"] == image.removeprefix(MIRROR)
    assert "--config.file=/etc/prometheus/prometheus.yml" in prometheus["args"]
    assert "--storage.tsdb.path=/prometheus" in prometheus["args"]
    mounts = {mount["name"]: mount["mountPath"] for mount in prometheus["volumeMounts"]}
    # In TLS alone, with the certificate its container of initialisation issues (US-2840).
    assert mounts == {
        "data": "/prometheus",
        "configuration": "/etc/prometheus",
        "certificates": "/tls",
    }
    assert "--web.config.file=/etc/prometheus/web.yml" in prometheus["args"]
    for name, content in configuration(objects).items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    checked = promtool("check", "config", str(tmp_path / "prometheus.yml"))
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "12 rules found" in checked.stdout


@pytest.mark.story("US-2880")
def test_the_chart_collects_the_front_the_api_and_the_worker_as_the_compose_does(
    objects: Objects, tmp_path: Path
) -> None:
    # Every pod of each, through a headless Service that selects them, ready or not: a pod that
    # does not answer is one Prometheus sees down. The jobs, their paths and their ports are the
    # Compose's.
    def jobs(text: str) -> dict[str, tuple[str, int, str]]:
        return {
            job["job_name"]: (
                job.get("metrics_path", "/metrics"),
                job["dns_sd_configs"][0]["port"],
                job["dns_sd_configs"][0]["names"][0],
            )
            for job in yaml.safe_load(text)["scrape_configs"]
        }

    by_chart = jobs(configuration(objects)["prometheus.yml"])
    by_compose(tmp_path)
    compose = jobs((tmp_path / "prometheus.yml").read_text(encoding="utf-8"))
    assert {job: found[:2] for job, found in by_chart.items()} == {
        job: found[:2] for job, found in compose.items()
    }
    assert set(by_chart) == {"front", "api", "worker"}
    for component, (_, port, name) in by_chart.items():
        service = named(objects, "Service", f"{component}-metrics")
        assert name == f"{service['metadata']['name']}.default.svc"
        assert service["spec"]["clusterIP"] == "None"
        assert service["spec"]["publishNotReadyAddresses"] is True
        workload = named(objects, "Deployment", component)
        assert service["spec"]["selector"] == workload["spec"]["selector"]["matchLabels"]
        (exposed,) = service["spec"]["ports"]
        assert exposed["port"] == port
        ports = {
            item["name"]: item["containerPort"]
            for item in container(objects, "Deployment", component)["ports"]
        }
        assert ports[exposed["targetPort"]] == port


@pytest.mark.requirement("WF-OBS-0030-A")
def test_a_threshold_changed_starts_prometheus_again_on_its_rules(objects: Objects) -> None:
    # « Chaque seuil modifié change la valeur à laquelle l'alerte apparaît. » : the rules change in
    # the ConfigMap, and the pod starts again on them.
    changed = rendered({"prometheus": {"thresholds": {"taskQueueAgeSeconds": 600}}})
    assert "> 600\n" in configuration(changed)["alerts.yml"]
    assert "> 900\n" in configuration(objects)["alerts.yml"]

    def checksum(items: Objects) -> str:
        template = named(items, "StatefulSet", "prometheus")["spec"]["template"]
        return template["metadata"]["annotations"]["checksum/configuration"]

    assert checksum(changed) != checksum(objects)


@pytest.mark.requirement("WF-OBS-0030-A")
@pytest.mark.parametrize(
    ("value", "given"),
    [
        ("taskQueueAgeSeconds", "15m"),
        ("taskQueueAgeSeconds", 0),
        ("errorRateWindowSeconds", -300),
        ("storageUsage", 85),
        ("storageUsage", 0),
        ("errorRate", "1.5"),
        ("errorRate", ""),
    ],
)
def test_a_threshold_that_is_not_one_stops_the_rendering_naming_it(value: str, given: Any) -> None:
    with pytest.raises(ChartError, match=rf"prometheus\.thresholds\.{value}"):
        rendered({"prometheus": {"thresholds": {value: given}}})


def test_without_its_prometheus_the_chart_leaves_the_rules_and_the_services_to_the_operator() -> (
    None
):
    objects = rendered(
        {"prometheus": {"enabled": False}, "grafana": {"prometheusUrl": "http://operator:9090"}}
    )
    components = {
        (item["kind"], item["metadata"]["labels"]["app.kubernetes.io/component"])
        for item in objects
    }
    assert ("StatefulSet", "prometheus") not in components
    assert ("Service", "prometheus") not in components
    assert ("ConfigMap", "prometheus") in components
    assert {("Service", f"{name}-metrics") for name in ("front", "api", "worker")} <= components


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_api_declares_the_capacities_of_the_volumes_of_the_chart(objects: Objects) -> None:
    # #4229: without a capacity, the alert of a storage at 85 % could never appear. The chart
    # declares the size of the volume of each space, in bytes.
    api = environment(container(objects, "Deployment", "api"))
    assert api["WATERFALL_DATABASE_CAPACITY_BYTES"] == str(10 * 1024**3)
    assert api["WATERFALL_STORAGE_CAPACITY_BYTES"] == str(10 * 1024**3)
    sized = rendered(
        {
            "postgresql": {"persistence": {"size": "500M"}},
            "storage": {"persistence": {"size": "2Ti"}},
        }
    )
    api = environment(container(sized, "Deployment", "api"))
    assert api["WATERFALL_DATABASE_CAPACITY_BYTES"] == "500000000"
    assert api["WATERFALL_STORAGE_CAPACITY_BYTES"] == str(2 * 1024**4)
    with pytest.raises(ChartError, match=r"storage\.persistence\.size"):
        rendered({"storage": {"persistence": {"size": "2 TB"}}})


@pytest.mark.requirement("WF-ADM-0130-A")
def test_the_api_presents_the_values_the_rules_and_the_worker_are_given(objects: Objects) -> None:
    # #4636: the status screen presents the operating parameters in force — the thresholds the
    # rules are written with, the retention the purge of the worker applies —, and reads the
    # Prometheus of the chart in HTTPS (TFX-14); the bootstrap writes the largest avatar.
    def api(values: dict[str, Any] | None = None) -> dict[str, Any]:
        return environment(container(rendered(values) if values else objects, "Deployment", "api"))

    shipped = api()
    assert {name: shipped[name] for name in SHIPPED} == SHIPPED
    worker = environment(container(objects, "Deployment", "worker"))
    retention = "WATERFALL_BACKGROUND_TASK_RETENTION_DAYS"
    assert shipped[retention] == worker[retention] == "30"
    assert shipped["WATERFALL_PROMETHEUS_ADDRESS"] == "https://waterfall-prometheus:9090"
    changed = {
        "prometheus": {"thresholds": {"taskQueueAgeSeconds": 600, "storageUsage": "0.9"}},
        "worker": {"backgroundTaskRetentionDays": 7},
    }
    given = api(changed)
    rules = configuration(rendered(changed))["alerts.yml"]
    assert given["WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS"] == "600"
    assert "> 600" in rules
    assert given["WATERFALL_STORAGE_USAGE_THRESHOLD"] == "0.9"
    assert given[retention] == "7"
    # The Prometheus of the operator is not given to the API: the screen says the metrics
    # unavailable.
    operator = api({"prometheus": {"enabled": False}, "grafana": {"prometheusUrl": "https://p"}})
    assert "WATERFALL_PROMETHEUS_ADDRESS" not in operator
    (install,) = named(objects, "Job", "install")["spec"]["template"]["spec"]["containers"]
    assert environment(install)["WATERFALL_AVATAR_MAX_BYTES"] == str(512 * 1024)


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_worker_serves_its_metrics_where_prometheus_reaches_it(objects: Objects) -> None:
    # #4229: on every interface of its pod, on the port of the values, the front's.
    worker = container(objects, "Deployment", "worker")
    variables = environment(worker)
    assert ipaddress.ip_address(variables["WATERFALL_HOST"]).is_unspecified
    assert variables["WATERFALL_METRICS_PORT"] == "9100"
    assert worker["ports"] == [{"name": "metrics", "containerPort": 9100}]
    moved = environment(container(rendered({"metrics": {"port": 9200}}), "Deployment", "worker"))
    assert moved["WATERFALL_METRICS_PORT"] == "9200"


def test_promtool_is_the_one_of_the_release_the_platform_runs() -> None:
    # The image of the Compose and of the chart, and the promtool the rules are played with.
    services = yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]
    tag = services["prometheus"]["image"].split("@")[0].rsplit(":", 1)[1]
    version = promtool("--version")
    assert version.returncode == 0
    assert f"promtool, version {tag.removeprefix('v')} " in version.stdout
