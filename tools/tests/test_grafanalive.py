# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Grafana started as the production Compose starts it: its provisioning and its account (US-2880).

The image pinned by its digest runs with the variables GF_* and the mounts of the service grafana of
compose.prod.yaml, and a password of the test: it answers under /grafana, loads the dashboard the
platform delivers and the one source that is Prometheus, and the account ``operator`` opens a
session there, a wrong password not. Docker is needed: a test skips without it, and says so.
"""

import base64
import http.client
import json
import re
import shutil
import subprocess
import time
import uuid
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_notification import COMPOSE, DASHBOARD, PRODUCTION

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = [
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed"),
    pytest.mark.unexecuted("skipped where docker is not installed"),
]

PHRASE = "grafana-test-only"
START_WITHIN = 120.0
OK = 200
UNAUTHORIZED = 401


def substituted(value: str, given: dict[str, str]) -> str:
    """Read a value of the Compose as Compose does: the defaults, the required values given."""
    value = value.replace("${WATERFALL_HTTPS_PORT:+:${WATERFALL_HTTPS_PORT}}", "")

    def read(found: re.Match[str]) -> str:
        name, kind, default = found.group(1), found.group(2), found.group(3)
        if name in given:
            return given[name]
        assert kind == ":-", f"{name} is required and not given"
        return default

    return re.sub(r"\$\{(\w+)(:[-?])([^}]*)\}", read, value)


def production() -> dict[str, Any]:
    services = yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]
    return dict(services["grafana"])


def image() -> str:
    return str(production()["image"]).removeprefix("${WATERFALL_MIRROR:-}")


def get(port: int, path: str, password: str | None = None) -> tuple[int, Any]:
    """Read an address of Grafana, with the account operator when a password is given."""
    headers: dict[str, str] = {}
    if password is not None:
        token = base64.b64encode(f"operator:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path, headers=headers)
        answer = connection.getresponse()
        body = answer.read()
        return answer.status, json.loads(body) if answer.status == OK else None
    finally:
        connection.close()


def until(path: str, port: int, password: str | None = None) -> tuple[int, Any]:
    """Read an address until it answers 200, for a bounded time."""
    deadline = time.monotonic() + START_WITHIN
    status: int | str = "nothing"
    while time.monotonic() < deadline:
        try:
            status, body = get(port, path, password)
        except OSError:
            status = "no connection"
        else:
            if status == OK:
                return status, body
        time.sleep(1)
    message = f"{path} answered {status} for {START_WITHIN:.0f} seconds"
    raise AssertionError(message)


@pytest.fixture(scope="module")
def grafana() -> Iterator[int]:
    """Start Grafana on the variables and the mounts of the production Compose; give its port."""
    service = production()
    given = {"WATERFALL_GRAFANA_ADMIN_PASSWORD": PHRASE, "WATERFALL_DOMAIN": "waterfall.test"}
    variables = {
        name: substituted(str(value), given) for name, value in service["environment"].items()
    }
    mounts: list[str] = []
    for volume in service["volumes"]:
        source, target, mode = str(volume).split(":")
        mounts += ["--volume", f"{(COMPOSE / source).resolve()}:{target}:{mode}"]
    name = f"waterfall-grafana-us2880-{uuid.uuid4().hex[:8]}"
    started = subprocess.run(
        [
            *("docker", "run", "--detach", "--name", name, "--publish", "127.0.0.1::3000"),
            *(
                argument
                for key, value in variables.items()
                for argument in ("--env", f"{key}={value}")
            ),
            *mounts,
            image(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        assert started.returncode == 0, started.stderr
        mapped = subprocess.run(
            ["docker", "port", name, "3000/tcp"], capture_output=True, text=True, check=True
        ).stdout
        yield int(mapped.split()[0].rsplit(":", 1)[1])
    finally:
        subprocess.run(
            ["docker", "rm", "--force", "--volumes", name], capture_output=True, check=False
        )


@pytest.mark.story("US-2880")
def test_grafana_answers_under_its_path_and_the_operator_opens_a_session_there(
    grafana: int,
) -> None:
    # Proper to US-2880: Grafana started on the values of production serves /grafana, and the
    # account of its own, whose password is the one of .env, opens a session; another is refused.
    status, health = until("/grafana/api/health", grafana)
    assert (status, health["database"]) == (OK, "ok")
    status, user = until("/grafana/api/user", grafana, PHRASE)
    assert (status, user["login"], user["isGrafanaAdmin"]) == (OK, "operator", True)
    assert get(grafana, "/grafana/api/user", "not-the-password")[0] == UNAUTHORIZED
    assert get(grafana, "/grafana/api/datasources")[0] == UNAUTHORIZED


@pytest.mark.story("US-2880")
def test_grafana_loads_the_dashboard_and_the_one_source_the_platform_delivers(grafana: int) -> None:
    # Proper to US-2880: the provisioning is read at the start: the dashboard of the file is there,
    # under its uid, and the only source is Prometheus; the panel of the alerts in progress is the
    # one whose expression the test of the alert plays (test_notification.py).
    delivered = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    _, loaded = until(f"/grafana/api/dashboards/uid/{delivered['uid']}", grafana, PHRASE)
    assert loaded["dashboard"]["title"] == delivered["title"]
    expressions = {
        panel["title"]: [target["expr"] for target in panel["targets"]]
        for panel in loaded["dashboard"]["panels"]
    }
    assert expressions == {
        panel["title"]: [target["expr"] for target in panel["targets"]]
        for panel in delivered["panels"]
    }
    assert expressions["Alertes en cours"]
    _, sources = until("/grafana/api/datasources", grafana, PHRASE)
    assert [(source["type"], source["uid"], source["url"]) for source in sources] == [
        ("prometheus", "prometheus", "http://prometheus:9090")
    ]
