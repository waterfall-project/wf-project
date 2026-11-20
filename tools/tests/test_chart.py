# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chart of Waterfall, rendered by Helm: what its objects say (US-2800).

The chart deploys what compose.prod.yaml deploys, from the same images, with the same settings and
the same roles of the database: these tests render it with the values of the chain and hold its
objects against the Compose. That it installs, bootstraps and lets its first administrator in is
held on a cluster, by ``make chart-trial`` in the full tier (wftools.charttrial). Selected by the
marker ``chart`` (``make test-chart``): they need Helm, which the tools leave out.
"""

import ipaddress
import re
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, chart
from wftools.chart import ChartError

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = [pytest.mark.chart, pytest.mark.requirement("WF-ARC-0050-A")]

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
MIRRORED = re.compile(r"^\$\{WATERFALL_MIRROR:-\}")
PUBLISHED = re.compile(r"^(ghcr\.io/waterfall-project/\w+):\$\{WATERFALL_IMAGE_TAG:\?[^}]*\}$")

Objects = list[dict[str, Any]]


def rendered(values: dict[str, Any] | None = None, release: str = chart.RELEASE) -> Objects:
    """Render the chart with the values of the chain and those given."""
    return [document for document in yaml.safe_load_all(chart.render(values, release)) if document]


@pytest.fixture(scope="module")
def objects() -> Objects:
    return rendered()


def of_kind(objects: Objects, kind: str) -> dict[str, dict[str, Any]]:
    """Return the objects of a kind, by their component."""
    return {
        item["metadata"]["labels"]["app.kubernetes.io/component"]: item
        for item in objects
        if item["kind"] == kind
    }


def pod(item: dict[str, Any]) -> dict[str, Any]:
    """Return the specification of the pods of a workload."""
    if item["kind"] == "CronJob":
        return item["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    return item["spec"]["template"]["spec"]


def containers(item: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield every container of a workload, those of its initialisation first."""
    spec = pod(item)
    yield from spec.get("initContainers", [])
    yield from spec["containers"]


def environment(container: dict[str, Any]) -> dict[str, Any]:
    """Return the variables of a container: a value, or where it is read from."""
    return {
        variable["name"]: variable.get("value", variable.get("valueFrom"))
        for variable in container.get("env", [])
    }


def services() -> dict[str, Any]:
    return yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]


def test_the_front_listens_on_every_interface_whatever_kubernetes_sets_hostname(
    objects: Objects,
) -> None:
    # Kubernetes sets HOSTNAME to the name of the pod over the ENV of the image (#826).
    (front,) = pod(of_kind(objects, "Deployment")["front"])["containers"]
    # Every interface: the address of none.
    assert ipaddress.ip_address(environment(front)["HOSTNAME"]).is_unspecified
    names = [variable["name"] for variable in front["env"]]
    assert names.count("HOSTNAME") == 1


def test_the_front_the_api_the_worker_and_the_restoration_are_deployments_of_their_own(
    objects: Objects,
) -> None:
    deployments = of_kind(objects, "Deployment")
    images = {
        component: [container["image"] for container in pod(deployments[component])["containers"]]
        for component in ("front", "api", "worker", "restore")
    }
    assert images["front"] == ["ghcr.io/waterfall-project/front:chain"]
    assert images["api"] == images["worker"] == ["ghcr.io/waterfall-project/waterfall:chain"]
    # The restoration, with the application of the realm beside it (#955), never two at once.
    assert images["restore"] == [
        "ghcr.io/waterfall-project/waterfall:chain",
        "ghcr.io/waterfall-project/keycloak:chain",
    ]
    assert deployments["restore"]["spec"]["replicas"] == 1
    assert deployments["restore"]["spec"]["strategy"] == {"type": "Recreate"}


def test_the_api_and_the_worker_multiply_by_a_value() -> None:
    objects = rendered({"api": {"replicas": 3, "processes": 2}, "worker": {"replicas": 2}})
    deployments = of_kind(objects, "Deployment")
    assert deployments["api"]["spec"]["replicas"] == 3
    assert deployments["worker"]["spec"]["replicas"] == 2


def test_scaling_the_api_does_not_change_the_pod_of_postgres() -> None:
    """The connections are a value of their own: a scaled API must not restart the database."""

    def postgres(values: dict[str, Any]) -> dict[str, Any]:
        return pod(of_kind(rendered(values), "StatefulSet")["postgres"])

    one = postgres({"api": {"replicas": 1}})
    three = postgres({"api": {"replicas": 3, "processes": 2}})
    assert one == three
    assert "max_connections=300" in one["containers"][0]["args"]
    custom = postgres({"postgresql": {"maxConnections": 500}})
    assert "max_connections=500" in custom["containers"][0]["args"]


def test_a_long_release_keeps_every_cronjob_name_within_52_characters() -> None:
    objects = rendered(release="r" * 40)
    names = [item["metadata"]["name"] for item in objects if item["kind"] == "CronJob"]
    assert names
    assert all(len(name) <= 52 for name in names), names


def test_the_restoration_waits_for_the_owner_of_the_database_it_reads() -> None:
    (restore,) = [
        item
        for item in rendered()
        if item["kind"] == "Deployment"
        and item["metadata"]["labels"]["app.kubernetes.io/component"] == "restore"
    ]
    wait = next(c for c in pod(restore)["initContainers"] if c["name"] == "wait-for-database")
    env = {item["name"]: item for item in wait["env"]}
    assert env["PGUSER"]["value"] == "waterfall"
    assert env["PGPASSWORD"]["valueFrom"]["secretKeyRef"]["key"] == "WATERFALL_POSTGRES_PASSWORD"


def test_the_chart_describes_the_services_the_ingress_the_secrets_and_the_volumes(
    objects: Objects,
) -> None:
    ports = {
        component: {port["name"]: port["port"] for port in item["spec"]["ports"]}
        for component, item in of_kind(objects, "Service").items()
    }
    assert ports == {
        "front": {"http": 3000},
        "api": {"http": 8000},
        "keycloak": {"http": 8080, "management": 9000},
        "postgres": {"postgres": 5432},
        "redis": {"redis": 6379},
        "storage": {"s3": 3900},
        "prometheus": {"http": 9090},
        "alertmanager": {"http": 9093},
        "grafana": {"http": 3000},
        # Headless, by which Prometheus finds every instance (US-2880).
        "front-metrics": {"metrics": 9100},
        "api-metrics": {"http": 8000},
        "worker-metrics": {"metrics": 9100},
    }
    (secret,) = of_kind(objects, "Secret").values()
    assert set(secret["stringData"]) == set(chart.SECRET_KEYS)
    volumes = {
        component: [claim["metadata"]["name"] for claim in item["spec"]["volumeClaimTemplates"]]
        for component, item in of_kind(objects, "StatefulSet").items()
    }
    assert volumes == {"postgres": ["data"], "storage": ["data"], "prometheus": ["data"]}


def test_the_ingress_serves_keycloak_under_auth_and_the_front_elsewhere(objects: Objects) -> None:
    (ingress,) = of_kind(objects, "Ingress").values()
    (rule,) = ingress["spec"]["rules"]
    assert rule["host"] == "waterfall.localhost"
    routes = {
        (path["path"], path["pathType"]): path["backend"]["service"]["name"]
        for path in rule["http"]["paths"]
    }
    assert routes == {
        ("/", "Prefix"): "waterfall-front",
        ("/auth", "Prefix"): "waterfall-keycloak",
        # The dashboard of the operator, with an account of its own (US-2880, TFX-15).
        ("/grafana", "Prefix"): "waterfall-grafana",
        ("/auth/callback", "Exact"): "waterfall-front",
        ("/auth/sign-out", "Exact"): "waterfall-front",
        # The console and the realm master, which the front has no page for, never Keycloak.
        ("/auth/admin", "Prefix"): "waterfall-front",
        ("/auth/realms/master", "Prefix"): "waterfall-front",
    }


def test_the_realm_is_applied_by_a_hook_after_each_installation_and_upgrade(
    objects: Objects,
) -> None:
    jobs = of_kind(objects, "Job")
    hooks = {
        component: (
            item["metadata"]["annotations"]["helm.sh/hook"],
            int(item["metadata"]["annotations"]["helm.sh/hook-weight"]),
        )
        for component, item in jobs.items()
    }
    assert hooks == {
        "migrate": ("post-install,pre-upgrade", -10),
        "realm": ("post-install,post-upgrade", 0),
        "install": ("post-install", 10),
    }
    (realm,) = pod(jobs["realm"])["containers"]
    assert realm["command"] == ["/opt/keycloak/bin/apply-realm"]
    keycloak_realm = services()["keycloak-realm"]["environment"]
    assert set(keycloak_realm) - {"KC_DB_URL", "KC_DB_USERNAME", "KC_DB_PASSWORD"} <= set(
        environment(realm)
    )


def test_the_migrations_run_in_the_order_of_the_compose_as_the_roles_it_names(
    objects: Objects,
) -> None:
    steps = {
        container["name"]: container for container in containers(of_kind(objects, "Job")["migrate"])
    }
    assert list(steps) == [
        "waterfall-database",
        "keycloak-database",
        "backup-database-role",
        "storage-buckets",
        "migrate",
        "service-database-role",
    ]
    assert environment(steps["migrate"])["WATERFALL_DATABASE_URL"].startswith(
        "postgresql://waterfall:$(WATERFALL_POSTGRES_PASSWORD)@"
    )
    # The restoration reads the database as its owner, as the Compose does for migrate alone.
    roles = {"api": "waterfall_service", "worker": "waterfall_service", "restore": "waterfall"}
    for name, role in roles.items():
        deployment = of_kind(objects, "Deployment")[name]
        url = environment(next(containers(deployment)))
        assert url["PGUSER"] == role, name


def test_the_tasks_planned_are_cronjobs_that_run_the_commands_of_the_scheduler(
    objects: Objects,
) -> None:
    loop = services()["scheduler"]["command"][-1]
    commands = {
        " ".join(next(containers(item))["command"]) for item in objects if item["kind"] == "CronJob"
    }
    assert commands == {"waterfall-worker purge", "waterfall-worker enqueue identity_sync"}
    assert all(command in loop for command in commands)


def test_the_chart_reads_the_images_of_the_compose(objects: Objects) -> None:
    published = {
        f"{match.group(1)}:chain"
        for service in services().values()
        if (match := PUBLISHED.match(service["image"]))
    }
    # Caddy is the door of the Compose alone: the ingress is the chart's.
    third_parties = {
        MIRRORED.sub("", service["image"])
        for name, service in services().items()
        if MIRRORED.match(service["image"]) and name != "caddy"
    }
    images = {
        container["image"]
        for item in objects
        if item["kind"] in {"Deployment", "StatefulSet", "Job", "CronJob"}
        for container in containers(item)
    }
    assert images == published | third_parties


def test_the_files_the_chart_mounts_are_those_of_the_compose(objects: Objects) -> None:
    files = of_kind(objects, "ConfigMap")["files"]
    for name, content in files["data"].items():
        assert content == (COMPOSE / name).read_text(encoding="utf-8").rstrip("\n"), name


def test_no_pod_reads_the_variables_of_the_services_of_its_namespace(objects: Objects) -> None:
    workloads = [
        item
        for item in objects
        if item["kind"] not in {"Service", "Secret", "ConfigMap", "Ingress"}
    ]
    assert workloads
    assert all(pod(item)["enableServiceLinks"] is False for item in workloads)


def test_a_secret_of_the_operator_replaces_the_one_the_chart_makes() -> None:
    objects = rendered({"secrets": {"existingSecret": "operator", "values": None}})
    assert of_kind(objects, "Secret") == {}
    (api,) = pod(of_kind(objects, "Deployment")["api"])["containers"]
    read = environment(api)["WATERFALL_SERVICE_DATABASE_PASSWORD"]
    assert read == {
        "secretKeyRef": {"name": "operator", "key": "WATERFALL_SERVICE_DATABASE_PASSWORD"}
    }


def test_a_value_the_chart_cannot_do_without_stops_the_rendering_naming_it() -> None:
    with pytest.raises(ChartError, match=r"secrets\.values\.WATERFALL_REDIS_PASSWORD"):
        rendered({"secrets": {"values": {"WATERFALL_REDIS_PASSWORD": ""}}})
    with pytest.raises(ChartError, match=r"platform\.domain"):
        rendered({"platform": {"domain": ""}})


def test_the_front_trusts_the_authority_it_is_given() -> None:
    objects = rendered({"transport": {"authority": "local-root"}})
    front = pod(of_kind(objects, "Deployment")["front"])
    assert environment(front["containers"][0])["NODE_EXTRA_CA_CERTS"] == "/authority/ca.crt"
    assert front["volumes"] == [
        {
            "name": "authority",
            "secret": {"secretName": "local-root", "items": [{"key": "ca.crt", "path": "ca.crt"}]},
        }
    ]
