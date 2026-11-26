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
# An image the chain publishes, in the Compose: by the digest .env gives it (#3726).
PUBLISHED = re.compile(
    r"^\$\{WATERFALL_REGISTRY:-ghcr\.io/waterfall-project\}/"
    r"(\w+)@\$\{WATERFALL_DIGEST_(\w+):\?[^}]*\}$"
)

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


def published(name: str) -> str:
    """Return an image the chain publishes, as the chart designates it with the chain's values."""
    return f"ghcr.io/waterfall-project/{name}@{chart.CHAIN_DIGESTS[name]}"


@pytest.mark.story("US-2830")
def test_the_worker_of_the_chart_keeps_what_the_worker_of_the_compose_keeps(
    objects: Objects,
) -> None:
    # propre à US-2830 : « background_task_retention_days est un paramètre d'exploitation » :
    # the two retentions of the purge are set on the worker of the chart as on the Compose's.
    # And, of US-2850, the wait of a task of a kind the worker does not run.
    names = (
        "WATERFALL_UNDO_RETENTION_HOURS",
        "WATERFALL_BACKGROUND_TASK_RETENTION_DAYS",
        "WATERFALL_UNKNOWN_KIND_WAIT_SECONDS",
    )
    compose = services()["worker"]["environment"]
    (container,) = pod(of_kind(objects, "Deployment")["worker"])["containers"]
    variables = environment(container)
    for name in names:
        assert variables[name] == re.sub(r"\$\{[A-Z_]+:-(.*)\}", r"\1", compose[name])


def test_the_front_listens_on_the_loopback_alone_whatever_kubernetes_sets_hostname(
    objects: Objects,
) -> None:
    # Kubernetes sets HOSTNAME to the name of the pod over the ENV of the image (#826). The front
    # listens on the loopback of its pod alone, behind its proxy in TLS (US-2840, #4508).
    front, _ = pod(of_kind(objects, "Deployment")["front"])["containers"]
    assert ipaddress.ip_address(environment(front)["HOSTNAME"]).is_loopback
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
    # The front, and its proxy in TLS beside it (US-2840).
    assert images["front"] == [
        published("front"),
        MIRRORED.sub("", services()["front-proxy"]["image"]),
    ]
    assert images["api"] == images["worker"] == [published("waterfall")]
    # The restoration, with the application of the realm beside it (#955), never two at once.
    assert images["restore"] == [
        published("waterfall"),
        published("keycloak"),
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
    # In TLS alone, those the ingress routes named https (US-2840); the metrics alone in HTTP.
    assert ports == {
        "front": {"https": 3443},
        "api": {"https": 8443},
        "keycloak": {"https": 8443, "management": 9000},
        "postgres": {"postgres": 5432},
        "redis": {"redis": 6379},
        "storage": {"s3": 3900},
        "prometheus": {"https": 9090},
        "alertmanager": {"https": 9093},
        "grafana": {"https": 3000},
        # Headless, by which Prometheus finds every instance (US-2880).
        "front-metrics": {"metrics": 9100},
        "api-metrics": {"metrics": 8000},
        "worker-metrics": {"metrics": 9100},
    }
    secret = of_kind(objects, "Secret")["secrets"]
    assert set(secret["stringData"]) == set(chart.SECRET_KEYS)
    volumes = {
        component: [claim["metadata"]["name"] for claim in item["spec"]["volumeClaimTemplates"]]
        for component, item in of_kind(objects, "StatefulSet").items()
    }
    assert volumes == {"postgres": ["data"], "storage": ["data"], "prometheus": ["data"]}


def test_the_ingress_serves_keycloak_under_auth_and_the_front_elsewhere(objects: Objects) -> None:
    # One Ingress for each server behind it, each in HTTPS (US-2840): the longest path wins
    # across them, as within one.
    ingresses = [item for item in objects if item["kind"] == "Ingress"]
    assert len(ingresses) == 3
    rules = [rule for ingress in ingresses for rule in ingress["spec"]["rules"]]
    assert {rule["host"] for rule in rules} == {"waterfall.localhost"}
    routes = {
        (path["path"], path["pathType"]): path["backend"]["service"]["name"]
        for rule in rules
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
        # The certificates of the data components, before anything reaches them (US-2850).
        "certificates": ("pre-install,pre-upgrade", -26),
        "migrate": ("post-install,pre-upgrade", -10),
        "buckets": ("post-install,pre-upgrade", -10),
        "realm": ("post-install,post-upgrade", 0),
        "install": ("post-install", 10),
    }
    (realm,) = pod(jobs["realm"])["containers"]
    assert realm["command"] == ["/opt/keycloak/bin/apply-realm"]
    keycloak_realm = services()["keycloak-realm"]["environment"]
    left = {"KC_DB_URL", "KC_DB_USERNAME", "KC_DB_PASSWORD"}
    assert set(keycloak_realm) - left <= set(environment(realm))


def test_the_migrations_run_in_the_order_of_the_compose_as_the_roles_it_names(
    objects: Objects,
) -> None:
    # After the roots of the pod, which its container of initialisation writes (US-2840).
    steps = {
        container["name"]: container
        for container in containers(of_kind(objects, "Job")["migrate"])
        if container["name"] != "transport"
    }
    assert list(steps) == [
        "waterfall-database",
        "keycloak-database",
        "backup-database-role",
        "components",
        "migrate",
        "service-database-role",
    ]
    # The buckets are a hook of their own, which the storage of the chart may not precede.
    (buckets,) = pod(of_kind(objects, "Job")["buckets"])["containers"]
    assert buckets["name"] == "storage-buckets"
    assert environment(buckets)["STORAGE_ADDRESS"] == "https://waterfall-storage:3900"
    assert environment(steps["migrate"])["WATERFALL_DATABASE_URL"].startswith(
        "postgresql://waterfall:$(WATERFALL_POSTGRES_PASSWORD)@"
    )
    # The restoration reads the database as its owner, as the Compose does for migrate alone.
    roles = {"api": "waterfall_service", "worker": "waterfall_service", "restore": "waterfall"}
    for name, role in roles.items():
        deployment = of_kind(objects, "Deployment")[name]
        wait = next(c for c in containers(deployment) if c["name"] == "wait-for-database")
        assert environment(wait)["PGUSER"] == role, name


@pytest.mark.story("US-2800")
def test_the_tasks_planned_are_one_cronjob_that_runs_the_one_command_of_the_schedule(
    objects: Objects,
) -> None:
    # propre à US-2800 : « les tâches planifiées (PBS-5.3) sont des CronJobs, qui n'exécutent que
    # la commande du worker qui inscrit une tâche et la met en file (TFX-10) » : the command the
    # loop of the Compose runs, every five minutes, never two at once, and no storage to reach.
    loop = services()["scheduler"]["command"][-1]
    (job,) = [item for item in objects if item["kind"] == "CronJob"]
    (container,) = pod(job)["containers"]
    assert container["command"] == ["waterfall-worker", "schedule"]
    assert "waterfall-worker schedule" in loop
    assert job["spec"]["schedule"] == "*/5 * * * *"
    assert job["spec"]["concurrencyPolicy"] == "Forbid"
    variables = environment(container)
    assert not [name for name in variables if "STORAGE" in name or "KEYCLOAK" in name]
    assert {"WATERFALL_DATABASE_URL", "WATERFALL_REDIS_URL"} <= variables.keys()
    assert variables["WATERFALL_PURGE_INTERVAL"] == "600"
    # US-3040: the reading of the accounts is scheduled by the database, not by a variable.
    assert not [name for name in variables if "IDENTITY_SYNC" in name]


def test_the_chart_reads_the_images_of_the_compose(objects: Objects) -> None:
    ours = {
        published(match.group(1))
        for service in services().values()
        if (match := PUBLISHED.match(service["image"]))
    }
    # Caddy is the door of the Compose: the ingress is the chart's. It is also the proxy in TLS of
    # the storage and of the front, in their pods as in the Compose (US-2840).
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
    assert images == ours | third_parties


def test_the_files_the_chart_mounts_are_those_of_the_compose(objects: Objects) -> None:
    configmaps = of_kind(objects, "ConfigMap")
    # The hook has its own, of the steps of the database alone (hooks.yaml).
    assert set(configmaps["hook-files"]["data"]) < set(configmaps["files"]["data"])
    for files in (configmaps["files"], configmaps["hook-files"]):
        for name, content in files["data"].items():
            assert content == (COMPOSE / name).read_text(encoding="utf-8").rstrip("\n"), name


def test_no_pod_reads_the_variables_of_the_services_of_its_namespace(objects: Objects) -> None:
    workloads = [
        item for item in objects if item["kind"] in {"Deployment", "StatefulSet", "Job", "CronJob"}
    ]
    assert workloads
    assert all(pod(item)["enableServiceLinks"] is False for item in workloads)


def test_a_secret_of_the_operator_replaces_the_one_the_chart_makes() -> None:
    objects = rendered({"secrets": {"existingSecret": "operator", "values": None}})
    assert "secrets" not in of_kind(objects, "Secret")
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


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_front_trusts_the_authority_it_is_given() -> None:
    # Its server reaches the API, Redis, and Keycloak through the ingress, trusting the root of
    # the platform: a certificate of the domain the authority of the operator signs is trusted.
    objects = rendered({"transport": {"authority": "local-root"}})
    front = pod(of_kind(objects, "Deployment")["front"])
    assert environment(front["containers"][0])["NODE_EXTRA_CA_CERTS"] == "/trust/root.crt"
    volumes = {volume["name"]: volume for volume in front["volumes"]}
    assert volumes["roots"]["projected"]["sources"] == [
        {"secret": {"name": "local-root", "items": [{"key": "ca.crt", "path": "platform.crt"}]}}
    ]
    assert of_kind(objects, "Secret").keys() == {"secrets"}
