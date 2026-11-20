# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The notification of the alerts and the dashboard of the operator, under Compose (US-2880).

Alertmanager notifies each alert of Prometheus by e-mail, through the mail server the environment
names, and notifies nothing without one (alertmanager.sh). Grafana serves the dashboard the platform
delivers, on the one source that is Prometheus, with an account of its own, outside the identity
provider, whose password .env must hold. The configuration Alertmanager starts with is checked by
amtool, that of the release the platform runs; the alert the dashboard shows is played by promtool.
The chart's side is in test_chartnotification.py.
"""

import json
import os
import re
import stat
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_alerts import by_compose, promtool
from test_supervision import COMPOSE, PRODUCTION, SERVICE, TEMPLATE, environment, services

from wftools import kubetools

if TYPE_CHECKING:
    from pathlib import Path

START = COMPOSE / "alertmanager.sh"
CADDYFILE = COMPOSE / "Caddyfile.prod"
DASHBOARD = COMPOSE / "grafana-dashboard.json"
DATASOURCE = COMPOSE / "grafana-datasource.yml"
PROVIDERS = COMPOSE / "grafana-dashboards.yml"
SERVER = {
    "WATERFALL_ALERT_SMTP_HOST": "smtp.example.test:587",
    "WATERFALL_ALERT_SMTP_FROM": "waterfall@example.test",
    "WATERFALL_ALERT_RECIPIENT": "exploitation@example.test",
}


def started(folder: Path, **given: str) -> subprocess.CompletedProcess[str]:
    """Start Alertmanager as the Compose does, with the environment given, on nothing."""
    variables = {
        "PATH": os.environ["PATH"],
        "RENDERED": str(folder),
        "ALERTMANAGER": "echo",
        **given,
    }
    return subprocess.run(
        ["sh", str(START), "--storage.path=/alertmanager"],
        env=variables,
        capture_output=True,
        text=True,
        check=False,
    )


def accepted(folder: Path) -> dict[str, Any]:
    """Have amtool, that of the release the platform runs, check the configuration; read it."""
    path = folder / "alertmanager.yml"
    checked = subprocess.run(
        [str(kubetools.installed("amtool")), "check-config", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.story("US-2880")
def test_without_a_mail_server_alertmanager_notifies_nothing(tmp_path: Path) -> None:
    # Proper to US-2880: « sans serveur, il ne notifie rien et les alertes restent sur l'écran et le
    # tableau de bord » : a receiver that holds no e-mail, whatever else the environment says.
    for given in ({}, {"WATERFALL_ALERT_RECIPIENT": "exploitation@example.test"}):
        done = started(tmp_path, **given)
        assert done.returncode == 0, done.stderr
        assert "no alert is notified" in done.stderr
        configuration = accepted(tmp_path)
        assert configuration["route"]["receiver"] == "operator"
        assert configuration["receivers"] == [{"name": "operator"}]
        assert "global" not in configuration


@pytest.mark.story("US-2880")
def test_each_alert_is_notified_by_e_mail_through_the_server_the_environment_names(
    tmp_path: Path,
) -> None:
    # Proper to US-2880: Alertmanager notifies each alert by e-mail, by the mail server the values
    # name; the end of an alert is notified too. It hands over with the arguments it is given.
    done = started(tmp_path, **SERVER)
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == [
        f"--config.file={tmp_path / 'alertmanager.yml'}",
        "--storage.path=/alertmanager",
    ]
    configuration = accepted(tmp_path)
    assert configuration["global"] == {
        "smtp_smarthost": "smtp.example.test:587",
        "smtp_from": "waterfall@example.test",
        "smtp_require_tls": True,
    }
    assert configuration["route"]["receiver"] == "operator"
    assert configuration["route"]["group_by"] == ["alertname", "component"]
    assert configuration["receivers"] == [
        {
            "name": "operator",
            "email_configs": [{"to": "exploitation@example.test", "send_resolved": True}],
        }
    ]
    plain = accepted_after(tmp_path, WATERFALL_ALERT_SMTP_REQUIRE_TLS="false")
    assert plain["global"]["smtp_require_tls"] is False


def accepted_after(folder: Path, **given: str) -> dict[str, Any]:
    """Start Alertmanager on a server and the values given over it, and check what it writes."""
    done = started(folder, **{**SERVER, **given})
    assert done.returncode == 0, done.stderr
    return accepted(folder)


@pytest.mark.story("US-2880")
def test_the_password_of_the_mail_server_is_read_from_a_file_of_its_own(tmp_path: Path) -> None:
    hard = "p@ss 'w\"ord\\ $(x) #1"
    configuration = accepted_after(
        tmp_path,
        WATERFALL_ALERT_SMTP_USER="alerts@example.test",
        WATERFALL_ALERT_SMTP_PASSWORD=hard,
    )
    written = tmp_path / "smtp-password"
    assert configuration["global"]["smtp_auth_username"] == "alerts@example.test"
    assert configuration["global"]["smtp_auth_password_file"] == str(written)
    assert written.read_text(encoding="utf-8") == hard
    assert stat.S_IMODE(written.stat().st_mode) == 0o600
    assert hard not in (tmp_path / "alertmanager.yml").read_text(encoding="utf-8")
    # A start that does not ask to sign in leaves no password of an earlier one behind.
    accepted_after(tmp_path)
    assert not written.exists()


@pytest.mark.story("US-2880")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("WATERFALL_ALERT_SMTP_HOST", "smtp.example.test"),
        ("WATERFALL_ALERT_SMTP_HOST", "smtp.example.test:587\nx: y"),
        ("WATERFALL_ALERT_SMTP_HOST", "smtp'.example.test:25"),
        ("WATERFALL_ALERT_SMTP_FROM", ""),
        ("WATERFALL_ALERT_SMTP_FROM", "waterfall"),
        ("WATERFALL_ALERT_RECIPIENT", ""),
        ("WATERFALL_ALERT_RECIPIENT", "a'b@example.test"),
        ("WATERFALL_ALERT_RECIPIENT", "a@example.test\nb@example.test"),
        ("WATERFALL_ALERT_RECIPIENT", "a@example.test,b@example.test"),
        ("WATERFALL_ALERT_SMTP_REQUIRE_TLS", "yes"),
        ("WATERFALL_ALERT_SMTP_USER", "al ice"),
    ],
)
def test_a_value_that_is_not_what_it_must_be_stops_the_start_naming_it(
    tmp_path: Path, name: str, value: str
) -> None:
    done = started(tmp_path, **{"WATERFALL_ALERT_SMTP_PASSWORD": "x", **SERVER, name: value})
    assert done.returncode == 2
    assert name in done.stderr
    assert done.stdout == ""


@pytest.mark.story("US-2880")
def test_a_user_without_its_password_or_a_password_of_several_lines_stops_the_start(
    tmp_path: Path,
) -> None:
    user = {**SERVER, "WATERFALL_ALERT_SMTP_USER": "alerts"}
    for password in ("", "one\ntwo"):
        done = started(tmp_path, **user, WATERFALL_ALERT_SMTP_PASSWORD=password)
        assert done.returncode == 2
        assert "WATERFALL_ALERT_SMTP_PASSWORD" in done.stderr
        assert done.stdout == ""


@pytest.mark.story("US-2880")
def test_alertmanager_is_a_service_of_the_platform_that_prometheus_sends_its_alerts_to() -> None:
    alertmanager = services()["alertmanager"]
    assert alertmanager["entrypoint"] == ["/bin/sh", "/etc/waterfall/alertmanager.sh"]
    assert "ports" not in alertmanager
    assert alertmanager["restart"] == "unless-stopped"
    assert [str(volume) for volume in alertmanager["volumes"]] == [
        "./alertmanager.sh:/etc/waterfall/alertmanager.sh:ro",
        "alertmanager-data:/alertmanager",
    ]
    variables = environment("alertmanager")
    assert variables == {
        "WATERFALL_ALERT_SMTP_HOST": "${WATERFALL_ALERT_SMTP_HOST:-}",
        "WATERFALL_ALERT_SMTP_FROM": "${WATERFALL_ALERT_SMTP_FROM:-}",
        "WATERFALL_ALERT_RECIPIENT": "${WATERFALL_ALERT_RECIPIENT:-}",
        "WATERFALL_ALERT_SMTP_REQUIRE_TLS": "${WATERFALL_ALERT_SMTP_REQUIRE_TLS:-true}",
        "WATERFALL_ALERT_SMTP_USER": "${WATERFALL_ALERT_SMTP_USER:-}",
        "WATERFALL_ALERT_SMTP_PASSWORD": "${WATERFALL_ALERT_SMTP_PASSWORD:-}",
    }
    configuration = yaml.safe_load((COMPOSE / "prometheus.yml").read_text(encoding="utf-8"))
    (manager,) = configuration["alerting"]["alertmanagers"]
    assert manager["static_configs"] == [{"targets": ["alertmanager:9093"]}]
    assert "alertmanager-data" in yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["volumes"]
    template = TEMPLATE.read_text(encoding="utf-8")
    for name in (
        "WATERFALL_ALERT_SMTP_HOST",
        "WATERFALL_ALERT_SMTP_FROM",
        "WATERFALL_ALERT_RECIPIENT",
    ):
        assert re.search(rf"^{name}=$", template, re.MULTILINE), name


@pytest.mark.story("US-2880")
def test_the_service_platform_runs_the_same_alertmanager_and_grafana_on_the_same_files() -> None:
    # As for Prometheus (test_supervision.py): the same image, the same script, the same mounts,
    # for the tests that read them (the profile supervision), the volumes of state left out.
    for name in ("alertmanager", "grafana"):
        production = services()[name]
        beside = services(SERVICE)[name]
        assert beside["image"] == production["image"], name
        assert beside["profiles"] == ["supervision"], name
        assert beside.get("entrypoint") == production.get("entrypoint"), name
        kept = [
            str(volume)
            for volume in production["volumes"]
            if str(volume).startswith("./") and not str(volume).startswith("./Caddyfile")
        ]
        assert [str(volume) for volume in beside["volumes"]] == kept, name


@pytest.mark.story("US-2880")
def test_prometheus_configuration_with_its_alertmanager_is_accepted_by_promtool(
    tmp_path: Path,
) -> None:
    by_compose(tmp_path)
    checked = promtool("check", "config", str(tmp_path / "prometheus.yml"))
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.story("US-2880")
def test_grafana_does_not_start_without_the_password_of_its_own_account() -> None:
    # Proper to US-2880: « son compte propre, hors du fournisseur d'identité, dont le mot de passe
    # est un secret du déploiement » without which it does not start: Compose refuses, naming it.
    name = "WATERFALL_GRAFANA_ADMIN_PASSWORD"
    grafana = environment("grafana")
    assert grafana["GF_SECURITY_ADMIN_PASSWORD"] == f"${{{name}:?set {name} in .env}}"
    assert re.search(rf"^{name}=$", TEMPLATE.read_text(encoding="utf-8"), re.MULTILINE)
    # The account is Grafana's own: no sign-in through the identity provider, none anonymous, no
    # sign-up, and no variable of the realm nor of a database among what it reads.
    assert grafana["GF_AUTH_ANONYMOUS_ENABLED"] == "false"
    assert grafana["GF_USERS_ALLOW_SIGN_UP"] == "false"
    # The door serves HTTPS alone: the cookie of the session is Secure.
    assert grafana["GF_SECURITY_COOKIE_SECURE"] == "true"
    assert not [key for key in grafana if key.startswith(("GF_AUTH_GENERIC", "GF_AUTH_KEYCLOAK"))]
    assert not [key for key in grafana if "DATABASE" in key or "REDIS" in key or "KEYCLOAK" in key]


@pytest.mark.story("US-2880")
def test_grafana_reads_neither_postgresql_nor_redis_and_keeps_its_account_from_its_password() -> (
    None
):
    # It stays served when they are down (WF-OBS-0030): it waits for no service of data, and keeps
    # nothing in a volume — an account kept would outlive a password changed in .env.
    grafana = services()["grafana"]
    assert "depends_on" not in grafana
    assert "ports" not in grafana
    assert not [volume for volume in grafana["volumes"] if not str(volume).endswith(":ro")]
    assert grafana["restart"] == "unless-stopped"
    assert all("grafana" not in service.get("depends_on", {}) for service in services().values()), (
        "no service waits for the dashboard"
    )


@pytest.mark.story("US-2880")
def test_the_door_serves_grafana_under_its_own_path_and_the_address_is_the_platforms() -> None:
    caddyfile = CADDYFILE.read_text(encoding="utf-8")
    assert re.search(
        r"@grafana path /grafana /grafana/\*\s+handle @grafana \{\s*"
        r"reverse_proxy grafana:3000\s*\}",
        caddyfile,
    )
    grafana = environment("grafana")
    assert grafana["GF_SERVER_SERVE_FROM_SUB_PATH"] == "true"
    root = grafana["GF_SERVER_ROOT_URL"]
    assert root.startswith("https://${WATERFALL_DOMAIN:?")
    assert root.endswith("/grafana/")


def provisioned(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.story("US-2880")
def test_the_dashboard_is_delivered_on_the_one_source_that_is_prometheus() -> None:
    sources = provisioned(DATASOURCE)["datasources"]
    assert [(source["type"], source["uid"], source["url"]) for source in sources] == [
        ("prometheus", "prometheus", "http://prometheus:9090")
    ]
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    sourced = {
        (item["datasource"]["type"], item["datasource"]["uid"])
        for panel in dashboard["panels"]
        for item in [panel, *panel["targets"]]
    }
    assert sourced == {("prometheus", "prometheus")}
    (provider,) = provisioned(PROVIDERS)["providers"]
    assert provider["options"]["path"] == "/var/lib/waterfall-dashboards"
    mounts = [str(volume) for volume in services()["grafana"]["volumes"]]
    assert "./grafana-dashboard.json:/var/lib/waterfall-dashboards/waterfall.json:ro" in mounts
    assert (
        "./grafana-datasource.yml:/etc/grafana/provisioning/datasources/waterfall.yml:ro" in mounts
    )


@pytest.mark.story("US-2880")
def test_the_dashboard_shows_the_components_the_queue_the_storage_the_errors_and_the_alerts() -> (
    None
):
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    expressions = " ".join(
        target["expr"] for panel in dashboard["panels"] for target in panel["targets"]
    )
    for metric in (
        "up",
        "waterfall_component_up",
        "waterfall_queued_tasks",
        "waterfall_oldest_queued_task_age_seconds",
        "waterfall_storage_used_bytes",
        "waterfall_storage_available_bytes",
        "waterfall_api_requests_total",
        "waterfall_front_requests_total",
        "ALERTS",
    ):
        assert re.search(rf"\b{metric}\b", expressions), metric
    titles = [panel["title"] for panel in dashboard["panels"]]
    assert len(titles) == len(set(titles))
    assert len({panel["id"] for panel in dashboard["panels"]}) == len(titles)


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_alert_of_a_component_unavailable_is_on_the_dashboard_while_postgresql_is_down(
    tmp_path: Path,
) -> None:
    # « Pendant l'arrêt de PostgreSQL, l'alerte d'indisponibilité est visible sur le tableau de bord
    # de l'exploitant. » : the panel of the alerts in progress reads the series ALERTS of Prometheus
    # alone, which its own rules write; evaluated, as Grafana asks, while the database is down.
    # The series waterfall_component_up{component="database"} is injected by hand here: the API
    # writes it (US-2870/L1), which its own tests hold. That Grafana loads this very panel, with
    # this expression, is held by test_grafanalive.py, on the real image.
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    (panel,) = [item for item in dashboard["panels"] if item["title"] == "Alertes en cours"]
    (target,) = panel["targets"]
    test: dict[str, Any] = {
        "rule_files": [str(by_compose(tmp_path))],
        "evaluation_interval": "1m",
        "tests": [
            {
                "interval": "1m",
                "input_series": [
                    {"series": series, "values": values}
                    for series, values in {
                        'up{job="api"}': "1x10",
                        'up{job="worker"}': "1x10",
                        'waterfall_component_up{component="database",instance="a"}': "1x2 0x8",
                        'waterfall_component_up{component="cache",instance="a"}': "1x10",
                    }.items()
                ],
                "promql_expr_test": [
                    {
                        "expr": target["expr"],
                        "eval_time": "2m",
                        "exp_samples": [],
                    },
                    {
                        "expr": target["expr"],
                        "eval_time": "6m",
                        "exp_samples": [
                            {
                                "labels": (
                                    '{alertname="component_unavailable", component="database", '
                                    'severity="alert"}'
                                ),
                                "value": 1,
                            }
                        ],
                    },
                ],
            }
        ],
    }
    path = tmp_path / "dashboard.yml"
    path.write_text(yaml.safe_dump(test), encoding="utf-8")
    done = promtool("test", "rules", str(path))
    assert done.returncode == 0, done.stdout + done.stderr
