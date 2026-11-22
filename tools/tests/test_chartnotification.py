# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Alertmanager and Grafana in the chart (US-2880, WF-OBS-0030).

The chart runs the Alertmanager and the Grafana of compose.prod.yaml, the same images, the same
script and the same dashboard (files/ links to deploy/compose), on the values the operator gives:
the mail server of the alerts, and the account of the dashboard, whose password is a key of the
Secret of the platform, without which the chart does not render. Selected by the marker ``chart``
(``make test-chart``): they need Helm.
"""

import json
import os
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_alerts import by_compose, promtool
from test_chartprometheus import PRODUCTION, configuration, container, environment, named, rendered
from test_notification import DASHBOARD, accepted

from wftools.chart import SECRET_KEYS, ChartError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.chart]

DASHBOARD_KEY = "WATERFALL_GRAFANA_ADMIN_PASSWORD"
MIRROR = "${WATERFALL_MIRROR:-}"
SMTP = {
    "host": "smtp.example.test:587",
    "from": "waterfall@example.test",
    "recipient": "exploitation@example.test",
}


@pytest.fixture(scope="module")
def objects() -> list[dict[str, Any]]:
    return rendered()


def image_of(service: str) -> str:
    """Give the image the Compose runs for a service, without its mirror."""
    services = yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]
    return str(services[service]["image"]).removeprefix(MIRROR)


@pytest.mark.story("US-2880")
def test_the_chart_runs_the_alertmanager_of_the_compose_by_its_script(
    objects: list[dict[str, Any]],
) -> None:
    alertmanager = container(objects, "Deployment", "alertmanager")
    assert alertmanager["image"] == image_of("alertmanager")
    assert alertmanager["command"] == ["/bin/sh", "/etc/waterfall/alertmanager.sh"]
    assert "--storage.path=/alertmanager" in alertmanager["args"]
    mounts = {mount["name"]: mount["mountPath"] for mount in alertmanager["volumeMounts"]}
    # In TLS alone, with the certificate its container of initialisation issues (US-2840).
    assert mounts == {"script": "/etc/waterfall", "state": "/alertmanager", "certificates": "/tls"}
    assert "--web.config.file=/etc/waterfall/alertmanager-web.yml" in alertmanager["args"]
    script = named(objects, "ConfigMap", "alertmanager")["data"]["alertmanager.sh"]
    compose = (PRODUCTION.parent / "alertmanager.sh").read_text(encoding="utf-8")
    assert script == compose.rstrip("\n")
    (service,) = named(objects, "Service", "alertmanager")["spec"]["ports"]
    assert service["port"] == 9093


@pytest.mark.story("US-2880")
def test_prometheus_sends_its_alerts_to_the_alertmanager_of_the_chart(
    objects: list[dict[str, Any]], tmp_path: Path
) -> None:
    text = configuration(objects)["prometheus.yml"]
    (manager,) = yaml.safe_load(text)["alerting"]["alertmanagers"]
    name = named(objects, "Service", "alertmanager")["metadata"]["name"]
    assert manager["static_configs"] == [{"targets": [f"{name}:9093"]}]
    for file, content in configuration(objects).items():
        (tmp_path / file).write_text(content, encoding="utf-8")
    checked = promtool("check", "config", str(tmp_path / "prometheus.yml"))
    assert checked.returncode == 0, checked.stdout + checked.stderr
    # The Compose's, which the chart's is written from, names its own service.
    by_compose(tmp_path / "compose")
    assert yaml.safe_load((tmp_path / "compose" / "prometheus.yml").read_text())["alerting"]


def started_as_the_pod_does(objects: list[dict[str, Any]], folder: Path) -> None:
    """Run the script of the ConfigMap with the variables of the container, on nothing."""
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "alertmanager.sh"
    script.write_text(
        named(objects, "ConfigMap", "alertmanager")["data"]["alertmanager.sh"], encoding="utf-8"
    )
    variables = environment(container(objects, "Deployment", "alertmanager"))
    given = {name: value for name, value in variables.items() if isinstance(value, str)}
    done = subprocess.run(
        ["sh", str(script)],
        env={
            "PATH": os.environ["PATH"],
            "RENDERED": str(folder),
            "ALERTMANAGER": "true",
            **given,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr


@pytest.mark.story("US-2880")
def test_the_chart_notifies_nothing_without_a_server_and_by_e_mail_through_the_one_it_names(
    objects: list[dict[str, Any]], tmp_path: Path
) -> None:
    # The values are those of the Compose: nothing without a host; with one, each alert by e-mail.
    started_as_the_pod_does(objects, tmp_path / "without")
    assert accepted(tmp_path / "without")["receivers"] == [{"name": "operator"}]
    named_server = rendered({"alertmanager": {"smtp": SMTP}})
    started_as_the_pod_does(named_server, tmp_path / "with")
    configuration_written = accepted(tmp_path / "with")
    assert configuration_written["global"]["smtp_smarthost"] == "smtp.example.test:587"
    assert configuration_written["global"]["smtp_from"] == "waterfall@example.test"
    assert configuration_written["receivers"][0]["email_configs"][0]["to"] == (
        "exploitation@example.test"
    )


@pytest.mark.story("US-2880")
def test_the_password_of_the_mail_server_is_read_from_the_secret_where_nothing_requires_it(
    objects: list[dict[str, Any]],
) -> None:
    variables = environment(container(objects, "Deployment", "alertmanager"))
    password = variables["WATERFALL_ALERT_SMTP_PASSWORD"]["secretKeyRef"]
    assert password["key"] == "WATERFALL_ALERT_SMTP_PASSWORD"
    assert password["optional"] is True
    secret = named(objects, "Secret", "secrets")
    assert "WATERFALL_ALERT_SMTP_PASSWORD" not in secret["stringData"]
    key = "WATERFALL_ALERT_SMTP_PASSWORD"
    given = rendered({"secrets": {"values": {key: "from-the-values"}}})
    secret = named(given, "Secret", "secrets")
    assert secret["stringData"][key] == "from-the-values"
    assert password["name"] == secret["metadata"]["name"]


@pytest.mark.story("US-2880")
def test_the_chart_runs_the_grafana_of_the_compose_on_its_dashboard_and_its_one_source(
    objects: list[dict[str, Any]],
) -> None:
    grafana = container(objects, "Deployment", "grafana")
    assert grafana["image"] == image_of("grafana")
    data = named(objects, "ConfigMap", "grafana")["data"]
    assert json.loads(data["waterfall.json"]) == json.loads(DASHBOARD.read_text(encoding="utf-8"))
    (source,) = yaml.safe_load(data["datasource.yml"])["datasources"]
    prometheus = named(objects, "Service", "prometheus")["metadata"]["name"]
    # In HTTPS, its certificate checked against the roots of the pod (US-2840, TFX-14).
    assert (source["type"], source["uid"], source["url"]) == (
        "prometheus",
        "prometheus",
        f"https://{prometheus}:9090",
    )
    assert source["jsonData"] == {"tlsAuthWithCACert": True}
    assert source["secureJsonData"] == {"tlsCACert": "$__file{/trust/root.crt}"}
    mounted = {mount["mountPath"] for mount in grafana["volumeMounts"]}
    assert "/var/lib/waterfall-dashboards/waterfall.json" in mounted
    other = rendered({"grafana": {"prometheusUrl": "http://prometheus.operator:9090"}})
    (source,) = yaml.safe_load(named(other, "ConfigMap", "grafana")["data"]["datasource.yml"])[
        "datasources"
    ]
    assert source["url"] == "http://prometheus.operator:9090"


@pytest.mark.story("US-2880")
def test_grafana_has_its_own_account_whose_password_is_a_secret_the_chart_cannot_do_without(
    objects: list[dict[str, Any]],
) -> None:
    # Proper to US-2880: the password of the account of the dashboard, outside the identity
    # provider, is a secret of the deployment; without it, the chart does not render, as the Compose
    # does not start.
    assert DASHBOARD_KEY in SECRET_KEYS
    variables = environment(container(objects, "Deployment", "grafana"))
    assert variables["GF_SECURITY_ADMIN_PASSWORD"]["secretKeyRef"]["key"] == DASHBOARD_KEY
    assert variables["GF_SECURITY_ADMIN_USER"] == "operator"
    assert variables["GF_AUTH_ANONYMOUS_ENABLED"] == "false"
    assert variables["GF_USERS_ALLOW_SIGN_UP"] == "false"
    assert variables["GF_SECURITY_COOKIE_SECURE"] == "true"
    assert not [name for name in variables if name.startswith(("GF_AUTH_GENERIC", "GF_DATABASE"))]
    with pytest.raises(ChartError, match=rf"secrets\.values\.{DASHBOARD_KEY}"):
        rendered({"secrets": {"values": {DASHBOARD_KEY: ""}}})


@pytest.mark.story("US-2880")
def test_grafana_reads_neither_postgresql_nor_redis_and_keeps_nothing(
    objects: list[dict[str, Any]],
) -> None:
    # It stays served when they are down: no init container waits for them — the one it has
    # issues its certificate (US-2840) —, no address of theirs.
    pod = named(objects, "Deployment", "grafana")["spec"]["template"]["spec"]
    assert [step["name"] for step in pod["initContainers"]] == ["transport"]
    text = yaml.safe_dump(pod)
    assert "postgres" not in text.lower().replace("postgresql", "")
    assert "redis" not in text.lower()
    assert [volume for volume in pod["volumes"] if "emptyDir" in volume]
    assert "persistentVolumeClaim" not in text


@pytest.mark.story("US-2880")
def test_without_its_prometheus_grafana_reads_the_one_the_values_name_and_alertmanager_stays() -> (
    None
):
    # prometheus.enabled false leaves the collection to a Prometheus of the operator: Grafana reads
    # the one grafana.prometheusUrl names, and the chart refuses to render without it, as a source
    # on a Service that does not exist would leave the dashboard empty. Alertmanager stays, and the
    # ConfigMap the operator's Prometheus reads still sends its alerts to it.
    with pytest.raises(ChartError, match=r"grafana\.prometheusUrl"):
        rendered({"prometheus": {"enabled": False}})
    url = "http://prometheus.operator:9090"
    objects = rendered({"prometheus": {"enabled": False}, "grafana": {"prometheusUrl": url}})
    (source,) = yaml.safe_load(named(objects, "ConfigMap", "grafana")["data"]["datasource.yml"])[
        "datasources"
    ]
    assert source["url"] == url
    alertmanager = named(objects, "Service", "alertmanager")["metadata"]["name"]
    assert named(objects, "Deployment", "alertmanager")
    sent = yaml.safe_load(named(objects, "ConfigMap", "prometheus")["data"]["prometheus.yml"])
    (manager,) = sent["alerting"]["alertmanagers"]
    assert manager["static_configs"] == [{"targets": [f"{alertmanager}:9093"]}]
