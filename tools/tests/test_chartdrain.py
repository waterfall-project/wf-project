# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The pods that serve requests drain before they stop, and are replaced one by one (US-2850).

A pod being removed leaves the Services and the ingress a moment after it is told to stop: until
then they still send it requests. Each container that serves one waits that moment before it is
stopped, then ends what it serves within the grace of its pod; and an upgrade makes the new
instance ready before it removes an old one. The API, whose clients keep their connections, writes
the file of its drain first, from which each answer closes its connection (#5020). That no request
fails is tried on a cluster, by ``make chart-upgrade`` (wftools.chartupgrade). Selected by the
marker ``chart`` (``make test-chart``): they need Helm, which the tools leave out.
"""

from pathlib import PurePosixPath
from typing import Any

import pytest
import yaml

from wftools import chart

pytestmark = [
    pytest.mark.chart,
    pytest.mark.requirement("WF-EXP-0030-A"),
    pytest.mark.story("US-2850"),
]

SERVING = {"api": {"api"}, "front": {"front", "front-proxy"}, "keycloak": {"keycloak"}}
"""The Deployments whose pods serve requests, and their containers that do."""
DRAIN = 10
"""The seconds a container that serves waits once its pod is ending, as the chart sets them."""
GRACE = 40
"""The seconds a pod is given to stop, the wait of its containers included."""


@pytest.fixture(scope="module")
def deployments() -> dict[str, dict[str, Any]]:
    """Return the Deployments of the chart rendered with the values of the chain, by component."""
    return {
        item["metadata"]["labels"]["app.kubernetes.io/component"]: item
        for item in yaml.safe_load_all(chart.render())
        if item and item["kind"] == "Deployment"
    }


CLOSING = {
    "preStop": {
        "exec": {"command": ["sh", "-c", f'touch "$WATERFALL_DRAIN_FILE" && sleep {DRAIN}']}
    }
}
"""The drain of the API: the file of its drain written, then the same wait."""


def test_each_container_that_serves_waits_before_it_is_stopped(
    deployments: dict[str, dict[str, Any]],
) -> None:
    for component, serving in SERVING.items():
        spec = deployments[component]["spec"]["template"]["spec"]
        waiting = {
            container["name"]
            for container in spec["containers"]
            if container.get("lifecycle") in ({"preStop": {"sleep": {"seconds": DRAIN}}}, CLOSING)
        }
        assert waiting == serving, component


def test_the_api_writes_the_file_of_its_drain_before_it_waits(
    deployments: dict[str, dict[str, Any]],
) -> None:
    (api,) = deployments["api"]["spec"]["template"]["spec"]["containers"]
    assert api["lifecycle"] == CLOSING
    environment = {variable["name"]: variable.get("value") for variable in api["env"]}
    # A file of the container's own, where any user writes: under its /tmp.
    assert PurePosixPath(environment["WATERFALL_DRAIN_FILE"]).parent == PurePosixPath("/", "tmp")


def test_a_pod_that_serves_is_given_the_time_to_end_what_it_serves(
    deployments: dict[str, dict[str, Any]],
) -> None:
    for component in SERVING:
        spec = deployments[component]["spec"]["template"]["spec"]
        assert spec["terminationGracePeriodSeconds"] == GRACE, component
    assert GRACE > DRAIN


def test_an_upgrade_replaces_the_instances_that_serve_one_by_one(
    deployments: dict[str, dict[str, Any]],
) -> None:
    for component in SERVING:
        assert deployments[component]["spec"]["strategy"] == {
            "type": "RollingUpdate",
            "rollingUpdate": {"maxSurge": 1, "maxUnavailable": 0},
        }, component


def test_the_worker_stops_where_it_stands_its_task_taken_again(
    deployments: dict[str, dict[str, Any]],
) -> None:
    spec = deployments["worker"]["spec"]["template"]["spec"]
    assert all("lifecycle" not in container for container in spec["containers"])
