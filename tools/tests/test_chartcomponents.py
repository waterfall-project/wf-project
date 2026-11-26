# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chart requires Kubernetes 1.35 and checks the components before its migrations (US-2810).

« Kubernetes dans une version au moins égale à 1.27 » (the oldest maintained version, 1.35, since
the author's decision of 2026-11-26, #4085; #5069 for the specification) and « Le déploiement échoue
en le disant si un composant est d'une version antérieure à celle exigée. » (WF-CMP-0020-A). The
chart declares the version of Kubernetes it requires, the oldest maintained, whose native ``sleep``
it uses for the drain of its pods; the
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


def job_check_of(
    job: str, values: Mapping[str, Any] | None = None, *, upgrade: bool = False
) -> dict[str, Any]:
    """Return the step of the Job ``job`` that checks the components."""
    options = ["--is-upgrade"] if upgrade else []
    documents = yaml.safe_load_all(chart.render(values, options=options))
    objects = [document for document in documents if document]
    (step,) = [
        container
        for container in containers(of_kind(objects, "Job")[job])
        if container["name"] == "components"
    ]
    return step


def check_of(values: Mapping[str, Any] | None = None, *, upgrade: bool = False) -> dict[str, Any]:
    """Return the step that checks the components in the hook of the migrations."""
    return job_check_of("migrate", values, upgrade=upgrade)


def after_the_realm(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the step of the Job that checks the components once the realm is applied."""
    return job_check_of("components", values)


@pytest.mark.parametrize("version", ["1.35.0", "1.35.6", "1.36.2", "1.37.2"])
def test_the_chart_installs_on_every_version_of_kubernetes_from_1_35(version: str) -> None:
    assert chart.render(options=[f"--kube-version={version}"])


@pytest.mark.parametrize("version", ["1.34.9", "1.29.0", "1.27.4"])
def test_the_chart_is_refused_on_a_cluster_older_than_1_35_and_says_why(version: str) -> None:
    with pytest.raises(chart.ChartError, match="kubeVersion"):
        chart.render(options=[f"--kube-version={version}"])


def test_the_chart_declares_the_oldest_version_of_kubernetes_that_is_maintained() -> None:
    declared = yaml.safe_load((chart.CHART / "Chart.yaml").read_text(encoding="utf-8"))
    assert declared["kubeVersion"] == ">=1.35.0-0"


@pytest.mark.story("US-2850")
def test_the_drain_of_the_pods_waits_by_the_native_action_sleep_of_the_hook() -> None:
    objects = rendered()
    serving = [
        container
        for item in of_kind(objects, "Deployment").values()
        for container in containers(item)
        if "lifecycle" in container
    ]
    assert len(serving) == 4
    for container in serving:
        assert container["lifecycle"] == {"preStop": {"sleep": {"seconds": 10}}}


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


@pytest.mark.parametrize("upgrade", [False, True])
def test_before_the_migrations_postgresql_is_checked_at_an_installation_and_an_upgrade(
    upgrade: bool,
) -> None:
    # The Redis and the Keycloak of the chart are read after the realm, so that an installation
    # whose realm failed, resumed by `helm upgrade --install`, is not stopped by a Keycloak that
    # cannot be read before the realm is applied.
    assert check_of(upgrade=upgrade)["command"] == [
        "waterfall-check-components",
        "--component",
        "postgresql",
    ]


@pytest.mark.parametrize("upgrade", [False, True])
def test_the_redis_of_the_operator_is_checked_before_the_migrations(upgrade: bool) -> None:
    command = [
        "waterfall-check-components",
        "--component",
        "postgresql",
        "--component",
        "redis",
    ]
    assert check_of(PROVIDED, upgrade=upgrade)["command"] == command


def test_keycloak_and_the_redis_of_the_chart_are_checked_after_the_realm_is_applied() -> None:
    assert after_the_realm()["command"] == [
        "waterfall-check-components",
        "--component",
        "keycloak",
        "--component",
        "redis",
    ]
    # The Redis of the operator was read before the migrations: only Keycloak is left.
    assert after_the_realm(PROVIDED)["command"] == [
        "waterfall-check-components",
        "--component",
        "keycloak",
    ]
    variables = environment(after_the_realm())
    assert {"WATERFALL_REDIS_URL", "WATERFALL_KEYCLOAK_BACKCHANNEL"} <= variables.keys()


def test_the_check_after_the_realm_runs_between_the_realm_and_the_bootstrap_at_both_events() -> (
    None
):
    jobs = of_kind(rendered(), "Job")

    def hook(name: str) -> tuple[set[str], int]:
        annotations = jobs[name]["metadata"]["annotations"]
        events = set(annotations["helm.sh/hook"].split(","))
        return events, int(annotations["helm.sh/hook-weight"])

    realm, components, install = hook("realm"), hook("components"), hook("install")
    assert components[0] == {"post-install", "post-upgrade"} == realm[0]
    assert realm[1] < components[1] < install[1]
    # Its Job fails the release, as the log of a Job that gives up does: no more than six runs.
    assert jobs["components"]["spec"]["backoffLimit"] == jobs["realm"]["spec"]["backoffLimit"]
