# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chart requires Kubernetes 1.27 and checks the components before its migrations (US-2810).

« Kubernetes dans une version au moins égale à 1.27 » and « Le déploiement échoue en le disant si
un composant est d'une version antérieure à celle exigée. » (WF-CMP-0020-A). The chart declares the
version of Kubernetes it requires, and keeps the drain of its pods on each one it accepts; the
command ``waterfall-check-components`` of the image of Waterfall runs, as a step of the hook of the
migrations, before them. That a refusal fails the deployment is held by the tests of the command
(``backend/tests/test_components.py``); that the chart installs on two distributions is held on
clusters, by ``make chart-trial`` and ``make chart-trial-k3s`` in the full tier. Selected by the
marker ``chart`` (``make test-chart``): they need Helm, which the tools leave out.
"""

from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_chart import containers, environment, of_kind, rendered
from test_chartprovided import PROVIDED

from wftools import chart

if TYPE_CHECKING:
    from collections.abc import Mapping

pytestmark = [pytest.mark.chart, pytest.mark.requirement("WF-CMP-0020-A")]


def check_of(values: Mapping[str, Any] | None = None, *, upgrade: bool = False) -> dict[str, Any]:
    """Return the step that checks the components in the hook of the migrations."""
    options = ["--is-upgrade"] if upgrade else []
    documents = yaml.safe_load_all(chart.render(values, options=options))
    objects = [document for document in documents if document]
    (step,) = [
        container
        for container in containers(of_kind(objects, "Job")["migrate"])
        if container["name"] == "components"
    ]
    return step


@pytest.mark.parametrize("version", ["1.27.0", "1.28.4", "1.29.9", "1.30.0", "1.37.2"])
def test_the_chart_installs_on_every_version_of_kubernetes_from_1_27(version: str) -> None:
    assert chart.render(options=[f"--kube-version={version}"])


@pytest.mark.parametrize("version", ["1.26.9", "1.20.0"])
def test_the_chart_is_refused_on_a_cluster_older_than_1_27_and_says_why(version: str) -> None:
    with pytest.raises(chart.ChartError, match="kubeVersion"):
        chart.render(options=[f"--kube-version={version}"])


def test_the_chart_declares_the_version_of_kubernetes_the_specification_requires() -> None:
    declared = yaml.safe_load((chart.CHART / "Chart.yaml").read_text(encoding="utf-8"))
    assert declared["kubeVersion"] == ">=1.27.0-0"


@pytest.mark.story("US-2850")
def test_the_drain_of_the_pods_waits_by_a_command_every_version_of_kubernetes_knows() -> None:
    # The action `sleep` of a hook is Kubernetes 1.30: under 1.29 it is dropped, or refused with the
    # gate off, and the drain is lost. The sleep of the image is run by every version.
    objects = rendered()
    serving = [
        container
        for item in of_kind(objects, "Deployment").values()
        for container in containers(item)
        if "lifecycle" in container
    ]
    assert len(serving) == 4
    for container in serving:
        assert container["lifecycle"] == {"preStop": {"exec": {"command": ["sleep", "10"]}}}


def test_the_components_are_checked_before_the_migrations_by_the_image_of_waterfall() -> None:
    objects = rendered()
    steps = [step["name"] for step in containers(of_kind(objects, "Job")["migrate"])]
    assert steps.index("components") < steps.index("migrate")
    assert steps.index("components") > steps.index("waterfall-database")
    step = check_of()
    migrate = next(
        each for each in containers(of_kind(objects, "Job")["migrate"]) if each["name"] == "migrate"
    )
    assert step["image"] == migrate["image"]
    assert step["command"][0] == "waterfall-check-components"


def test_the_check_reads_the_components_as_the_command_of_the_compose_does() -> None:
    variables = environment(check_of())
    assert {
        "WATERFALL_DATABASE_URL",
        "WATERFALL_REDIS_URL",
        "WATERFALL_KEYCLOAK_ADDRESS",
        "WATERFALL_KEYCLOAK_BACKCHANNEL",
        "WATERFALL_SERVICE_CLIENT_SECRET",
        "WATERFALL_TLS_AUTHORITY",
    } <= variables.keys()
    # As the owner of the tables, whose role the steps above made.
    assert variables["WATERFALL_DATABASE_URL"].startswith(
        "postgresql://waterfall:$(WATERFALL_POSTGRES_PASSWORD)@"
    )


def test_an_upgrade_checks_the_three_components_which_are_all_there() -> None:
    assert check_of(upgrade=True)["command"] == ["waterfall-check-components"]


def test_an_installation_checks_postgresql_alone_when_the_chart_makes_the_rest() -> None:
    assert check_of()["command"] == [
        "waterfall-check-components",
        "--component",
        "postgresql",
    ]


def test_an_installation_on_the_redis_of_the_operator_checks_it_too() -> None:
    assert check_of(PROVIDED)["command"] == [
        "waterfall-check-components",
        "--component",
        "postgresql",
        "--component",
        "redis",
    ]
