# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The data components an operator provides, as the trial of the chart poses them (US-2800/L2)."""

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import chart, chartdata, charttrial
from wftools.charttrial import Tools, Trial, TrialError
from wftools.production import Platform, ProductionError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-ARC-0050-A"), pytest.mark.story("US-2800")]

PLATFORM = Platform("waterfall.localhost", 41443, 0)


def by_kind(objects: list[dict[str, Any]], kind: str) -> dict[str, dict[str, Any]]:
    return {item["metadata"]["name"]: item for item in objects if item["kind"] == kind}


def test_the_three_components_run_the_images_the_chart_pins_behind_the_mirror() -> None:
    drawn = charttrial.drawn_secrets()
    shipped = chart.defaults()
    objects = chartdata.manifests(drawn, "mirror.example/")
    deployments = by_kind(objects, "Deployment")
    assert set(deployments) == set(chartdata.COMPONENTS)
    for component, key in (("postgres", "postgresql"), ("redis", "redis"), ("storage", "storage")):
        container = deployments[component]["spec"]["template"]["spec"]["containers"][0]
        assert container["image"] == f"mirror.example/{shipped[key]['image']}"
    # Garage behind the proxy in TLS the chart runs beside its own (US-2840).
    _, proxy = deployments["storage"]["spec"]["template"]["spec"]["containers"]
    assert proxy["image"] == f"mirror.example/{shipped['transport']['proxyImage']}"
    assert {item["metadata"]["namespace"] for item in objects if item["kind"] != "Namespace"} == {
        chartdata.NAMESPACE
    }


def test_the_components_are_set_as_the_platform_asks_and_with_the_secrets_drawn() -> None:
    drawn = charttrial.drawn_secrets()
    objects = chartdata.manifests(drawn, "")
    deployments = by_kind(objects, "Deployment")

    def container(component: str) -> dict[str, Any]:
        return deployments[component]["spec"]["template"]["spec"]["containers"][0]

    def env(component: str) -> dict[str, str]:
        return {item["name"]: item["value"] for item in container(component)["env"]}

    # The server of the platform: 1 024 locks per transaction, the connections of the chart.
    assert "max_locks_per_transaction=1024" in container("postgres")["args"]
    assert "max_connections=300" in container("postgres")["args"]
    assert env("postgres")["POSTGRES_PASSWORD"] == drawn["WATERFALL_POSTGRES_ADMIN_PASSWORD"]
    assert env("redis")["REDISCLI_AUTH"] == drawn["WATERFALL_REDIS_PASSWORD"]
    assert env("storage")["GARAGE_DEFAULT_SECRET_KEY"] == drawn["WATERFALL_STORAGE_SECRET"]
    assert env("storage")["GARAGE_RPC_SECRET"] == drawn["WATERFALL_STORAGE_RPC_SECRET"]
    assert env("storage")["GARAGE_DEFAULT_ACCESS_KEY"] == chart.defaults()["storage"]["accessKey"]
    ports = {
        name: item["spec"]["ports"][0]["port"] for name, item in by_kind(objects, "Service").items()
    }
    assert ports == {"postgres": 5432, "redis": 6379, "storage": 3900}


def test_the_operator_values_name_each_component_by_its_service_and_the_operator_secret() -> None:
    base = {"images": {"tag": "abc"}, "secrets": {"values": {"K": "v"}}, "api": {"replicas": 1}}
    values = chartdata.provided_values(base)
    assert values["images"] == {"tag": "abc"}
    assert values["api"] == {"replicas": 1}
    assert values["secrets"] == {"existingSecret": chartdata.KEYS}
    assert values["postgresql"] == {"enabled": False, "host": "postgres.data.svc.cluster.local"}
    assert values["redis"] == {"enabled": False, "host": "redis.data.svc.cluster.local"}
    assert values["storage"] == {
        "enabled": False,
        "address": "https://storage.data.svc.cluster.local:3900",
    }
    # Their certificates are checked against the roots the operator gives apart (US-2840).
    assert values["transport"] == {"providedAuthority": chartdata.ROOTS}
    # The pod of the test of a restoration goes out to the pods of the two components alone.
    postgres, storage = (values["restoreTest"]["egress"][key] for key in ("postgresql", "storage"))
    assert postgres == [chartdata.peer(chartdata.POSTGRES)]
    assert storage == [chartdata.peer(chartdata.STORAGE)]
    assert storage[0]["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"] == "data"
    # The values the trial installed the first time are not touched.
    assert base["secrets"] == {"values": {"K": "v"}}


@pytest.mark.chart
def test_the_operator_values_render_the_chart_without_a_component_of_its_own() -> None:
    rendered = chart.helm(
        ["template", chart.RELEASE], chartdata.provided_values(chart.chain_values())
    )
    assert "StatefulSet" in rendered
    assert "name: waterfall-postgres" not in rendered
    assert "name: waterfall-redis" not in rendered
    assert "name: waterfall-storage" not in rendered
    assert "@postgres.data.svc.cluster.local:5432/waterfall" in rendered


@pytest.mark.chart
def test_the_components_are_started_as_the_chart_starts_its_own() -> None:
    """The server and the cache of the operator run with the options of those of the chart."""
    objects = [
        item
        for item in yaml.safe_load_all(chart.render(None, chart.RELEASE))
        if item and item["kind"] in {"StatefulSet", "Deployment"}
    ]
    own = {
        item["metadata"]["labels"]["app.kubernetes.io/component"]: item["spec"]["template"]["spec"][
            "containers"
        ][0]
        for item in objects
    }
    provided = by_kind(chartdata.manifests(charttrial.drawn_secrets(), ""), "Deployment")

    def container(component: str) -> dict[str, Any]:
        return provided[component]["spec"]["template"]["spec"]["containers"][0]

    chart_args = own["postgres"]["args"]
    # The connections are the chart's default in both; the lock option is the one to compare.
    assert container("postgres")["args"] == chart_args
    assert container("redis")["command"] == own["redis"]["command"]


def test_the_trial_poses_the_components_then_makes_the_secret_from_a_file(tmp_path: Path) -> None:
    ran: list[list[str]] = []

    def run(command: list[str]) -> int:
        ran.append(command)
        return 0

    trial = Trial(
        Tools(["kind"], ["kubectl"], ["helm"]), run, lambda _: (0, ""), tmp_path, PLATFORM
    )
    drawn = charttrial.drawn_secrets()
    trial.provide(drawn, "")
    applied, *made, roots, rollout, secret = ran
    assert applied[:3] == ["kubectl", "apply", "--filename"]
    # The certificate of each component, which the authority of the trial issued for its name, and
    # the root of them for the platform (US-2840).
    assert [command[6] for command in made] == [
        chartdata.certificates(component) for component in chartdata.COMPONENTS
    ]
    assert made[0][7:] == [
        f"--from-file=tls.crt={tmp_path / 'postgres.crt'}",
        f"--from-file=tls.key={tmp_path / 'postgres.key'}",
        f"--from-file=ca.crt={tmp_path / 'ca.crt'}",
    ]
    assert roots[-2:] == [chartdata.ROOTS, f"--from-file=ca.crt={tmp_path / 'ca.crt'}"]
    issued = (tmp_path / "storage.ext").read_text(encoding="utf-8")
    assert "subjectAltName=DNS:storage.data.svc.cluster.local" in issued
    listed = json.loads((tmp_path / "data.json").read_text(encoding="utf-8"))
    assert listed["kind"] == "List"
    assert rollout[:5] == ["kubectl", "--namespace", chartdata.NAMESPACE, "rollout", "status"]
    # Every key of the platform is in the Secret, read from a file: not one value in a command.
    assert secret[-1] == f"--from-env-file={tmp_path / 'secret.env'}"
    assert not any(value in " ".join(secret) for value in drawn.values())
    lines = (tmp_path / "secret.env").read_text(encoding="utf-8").splitlines()
    assert {line.split("=", 1)[0] for line in lines} == set(chart.SECRET_KEYS)


def _provided_trial(tmp_path: Path, answers: dict[str, str]) -> Trial:
    def read(command: list[str]) -> tuple[int, str]:
        said = " ".join(command)
        return 0, next((out for key, out in answers.items() if key in said), "")

    return Trial(Tools(["kind"], ["kubectl"], ["helm"]), lambda _: 0, read, tmp_path, PLATFORM)


def test_the_installation_on_the_operator_data_holds_when_the_chart_made_none_and_migrated_first(
    tmp_path: Path,
) -> None:
    trial = _provided_trial(
        tmp_path,
        {
            "completionTime": "2026-11-20T10:00:05Z",
            "creationTimestamp": "2026-11-20T10:00:09Z",
        },
    )
    trial.hold_provided()


def test_a_component_of_the_chart_beside_those_of_the_operator_is_refused(tmp_path: Path) -> None:
    trial = _provided_trial(tmp_path, {"--selector": "pod/waterfall-redis-1\n"})
    with pytest.raises(TrialError, match="the chart made its own pod/waterfall-redis-1"):
        trial.hold_provided()


def test_migrations_that_ended_after_the_installation_began_are_refused(tmp_path: Path) -> None:
    trial = _provided_trial(
        tmp_path,
        {
            "completionTime": "2026-11-20T10:00:20Z",
            "creationTimestamp": "2026-11-20T10:00:09Z",
        },
    )
    with pytest.raises(ProductionError, match="the migrations ended at"):
        trial.hold_provided()
