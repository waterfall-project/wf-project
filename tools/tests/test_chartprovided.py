# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chart on the data components the operator provides, and scaled (US-2800/L2).

PostgreSQL, Redis and the object storage each give way to an address and a secret of the operator's;
the migrations then run before the installation. Scaling the API changes one value and nothing a pod
reads. That a cluster installs the chart so, and takes the API from one instance to three under
requests none of which fails, is held by ``make chart-trial`` (wftools.charttrial). Selected by the
marker ``chart`` (``make test-chart``): they need Helm.
"""

import re
from typing import Any

import pytest
import yaml
from test_chart import (
    PRODUCTION,
    PUBLISHED,
    Objects,
    containers,
    environment,
    of_kind,
    pod,
    published,
    rendered,
)

from wftools.chart import ChartError

pytestmark = [pytest.mark.chart, pytest.mark.requirement("WF-ARC-0050-A")]

PROVIDED: dict[str, dict[str, Any]] = {
    "postgresql": {"enabled": False, "host": "postgres.data.svc", "port": 6432},
    "redis": {"enabled": False, "host": "redis.data.svc", "port": 6380},
    "storage": {"enabled": False, "address": "https://s3.data.svc:9000"},
    "secrets": {"existingSecret": "operator", "values": None},
    # The roots of the certificates of the components of the operator (US-2840).
    "transport": {"providedAuthority": "operator-roots"},
    "restoreTest": {
        "egress": {
            "postgresql": [{"ipBlock": {"cidr": "10.0.0.5/32"}}],
            "storage": [{"ipBlock": {"cidr": "10.0.0.6/32"}}],
        }
    },
}
PINNED = re.compile(r"@sha256:[0-9a-f]{64}$")
CHART_OWN = {"postgres", "redis", "storage"}
# What an address of PostgreSQL asks: TLS, the certificate and its name checked (US-2840).
VERIFIED = "?sslmode=verify-full&sslrootcert=/trust/root.crt"


def main(item: dict[str, Any]) -> dict[str, Any]:
    """Return the variables of the container a workload runs for itself, not its initialisation."""
    return environment(pod(item)["containers"][0])


def components(objects: Objects, kind: str) -> set[str]:
    """Return the components that have an object of a kind."""
    return set(of_kind(objects, kind))


def test_the_three_data_components_are_the_chart_s_own_unless_the_operator_provides_them() -> None:
    objects = rendered()
    assert components(objects, "Service") >= CHART_OWN
    assert {"postgres", "storage"} <= components(objects, "StatefulSet")
    assert "redis" in components(objects, "Deployment")


ONE_BY_ONE: list[tuple[dict[str, Any], set[str]]] = [
    ({"postgresql": PROVIDED["postgresql"]}, {"redis", "storage"}),
    ({"redis": PROVIDED["redis"]}, {"postgres", "storage"}),
    ({"storage": PROVIDED["storage"]}, {"postgres", "redis"}),
    (PROVIDED, set()),
]


@pytest.mark.parametrize(
    ("given", "left"),
    ONE_BY_ONE,
    ids=["postgresql", "redis", "storage", "all three"],
)
def test_each_data_component_is_disabled_alone_for_an_address_and_a_secret_of_the_operator(
    given: dict[str, Any], left: set[str]
) -> None:
    values = dict(given)
    # The migrations of a PostgreSQL of the operator's run before the installation: its Secret too.
    values["secrets"] = PROVIDED["secrets"]
    # The pod of the test of a restoration reaches it at the peers the operator names (US-2930).
    values["restoreTest"] = PROVIDED["restoreTest"]
    values["transport"] = PROVIDED["transport"]
    objects = rendered(values)
    served = (
        components(objects, "Service")
        | components(objects, "StatefulSet")
        | components(objects, "Deployment")
    )
    assert CHART_OWN & served == left
    # The platform still reads the Secret of the operator, key by key, for every component.
    (api,) = pod(of_kind(objects, "Deployment")["api"])["containers"]
    assert environment(api)["WATERFALL_REDIS_PASSWORD"] == {
        "secretKeyRef": {"name": "operator", "key": "WATERFALL_REDIS_PASSWORD"}
    }


def test_every_service_reaches_the_data_components_at_the_addresses_of_the_operator() -> None:
    objects = rendered(PROVIDED)
    for component in ("api", "worker", "restore"):
        variables = main(of_kind(objects, "Deployment")[component])
        assert variables["WATERFALL_REDIS_URL"] == (
            "rediss://:$(WATERFALL_REDIS_PASSWORD)@redis.data.svc:6380/0"
            "?ssl_ca_certs=/trust/root.crt"
        ), component
        assert variables["WATERFALL_STORAGE_ADDRESS"] == "https://s3.data.svc:9000", component
    api = main(of_kind(objects, "Deployment")["api"])
    assert api["WATERFALL_DATABASE_URL"].endswith(f"@postgres.data.svc:6432/waterfall{VERIFIED}")
    worker = main(of_kind(objects, "Deployment")["worker"])
    backup = worker["WATERFALL_BACKUP_DATABASE_URL"]
    assert backup.endswith(f"@postgres.data.svc:6432/waterfall{VERIFIED}")
    backup = worker["WATERFALL_KEYCLOAK_DATABASE_URL"]
    assert backup.endswith(f"@postgres.data.svc:6432/keycloak{VERIFIED}")
    keycloak = main(of_kind(objects, "Deployment")["keycloak"])
    assert keycloak["KC_DB_URL"] == f"jdbc:postgresql://postgres.data.svc:6432/keycloak{VERIFIED}"
    restore = main(of_kind(objects, "Deployment")["restore"])
    owner = restore["WATERFALL_KEYCLOAK_DATABASE_URL"]
    assert owner.endswith(f"@postgres.data.svc:6432/keycloak{VERIFIED}")
    # The waits and the steps of the database sign in to the server of the operator, as the
    # administrator it names.
    for wait in (
        step
        for step in containers(of_kind(objects, "Deployment")["api"])
        if step["name"] == "wait-for-database"
    ):
        assert environment(wait)["PGHOST"] == "postgres.data.svc"
        assert environment(wait)["PGPORT"] == "6432"
    install = main(of_kind(objects, "Job")["install"])
    owner = install["WATERFALL_DATABASE_URL"]
    assert owner.endswith(f"@postgres.data.svc:6432/waterfall{VERIFIED}")


def test_the_buckets_are_made_on_the_storage_of_the_operator() -> None:
    (buckets,) = pod(of_kind(rendered(PROVIDED), "Job")["buckets"])["containers"]
    assert environment(buckets)["STORAGE_ADDRESS"] == "https://s3.data.svc:9000"


def test_the_steps_of_the_database_sign_in_as_the_administrator_the_operator_names() -> None:
    objects = rendered({**PROVIDED, "postgresql": {**PROVIDED["postgresql"], "adminUser": "dba"}})
    for step in containers(of_kind(objects, "Job")["migrate"]):
        if step["name"] not in {"migrate", "transport"}:
            assert environment(step)["PGUSER"] == "dba", step["name"]
            assert environment(step)["PGPORT"] == "6432", step["name"]


def test_the_migrations_run_before_the_installation_on_a_postgresql_of_the_operator() -> None:
    def events(objects: Objects) -> dict[str, str]:
        return {
            kind: item["metadata"]["annotations"]["helm.sh/hook"]
            for kind, item in (
                of_kind(objects, "Job") | {"files": of_kind(objects, "ConfigMap")["hook-files"]}
            ).items()
            if "annotations" in item["metadata"]
        }

    ours, theirs = events(rendered()), events(rendered(PROVIDED))
    assert ours["migrate"] == ours["files"] == "post-install,pre-upgrade"
    assert theirs["migrate"] == theirs["files"] == "pre-install,pre-upgrade"
    # The rest stays after the installation: the buckets, the realm, the bootstrap.
    assert theirs["buckets"] == "post-install,pre-upgrade"
    assert theirs["realm"] == "post-install,post-upgrade"
    assert theirs["install"] == "post-install"


def test_the_files_of_a_hook_before_the_installation_are_a_configmap_made_for_it() -> None:
    objects = rendered(PROVIDED)
    migrate = of_kind(objects, "Job")["migrate"]
    claimed = {
        volume["configMap"]["name"] for volume in pod(migrate)["volumes"] if "configMap" in volume
    }
    hook = of_kind(objects, "ConfigMap")["hook-files"]
    assert claimed == {hook["metadata"]["name"]}
    annotations = hook["metadata"]["annotations"]
    # Made before the Job, removed once the hooks have run; never the ConfigMap of the chart, which
    # does not exist before the installation.
    assert int(annotations["helm.sh/hook-weight"]) < int(
        migrate["metadata"]["annotations"]["helm.sh/hook-weight"]
    )
    assert annotations["helm.sh/hook-delete-policy"] == "before-hook-creation,hook-succeeded"
    assert hook["metadata"]["name"] != of_kind(objects, "ConfigMap")["files"]["metadata"]["name"]


def test_a_postgresql_of_the_operator_needs_the_secret_of_the_operator_too() -> None:
    values = {**PROVIDED, "secrets": {"existingSecret": ""}}
    with pytest.raises(ChartError, match=r"secrets\.existingSecret"):
        rendered(values)
    # The chart's own PostgreSQL does not: its Secret is made with the other objects.
    assert rendered({"secrets": {"existingSecret": ""}})


@pytest.mark.parametrize(
    ("given", "named"),
    [
        ({"postgresql": {"enabled": False}}, r"postgresql\.host"),
        ({"redis": {"enabled": False}}, r"redis\.host"),
        ({"storage": {"enabled": False}}, r"storage\.address"),
    ],
    ids=["postgresql", "redis", "storage"],
)
def test_a_component_provided_without_its_address_stops_the_rendering_naming_it(
    given: dict[str, Any], named: str
) -> None:
    with pytest.raises(ChartError, match=named):
        rendered({**given, "secrets": PROVIDED["secrets"], "transport": PROVIDED["transport"]})


@pytest.mark.parametrize(
    ("api", "fails"),
    [
        ({"replicas": 1, "processes": 1}, False),
        ({"replicas": 3, "processes": 2}, False),
        # 15 x 3 x 3 + 200 = 335, over the 300 of the default.
        ({"replicas": 3, "processes": 3}, True),
        ({"replicas": 4, "processes": 2}, True),
    ],
)
def test_the_connections_of_postgresql_cover_the_instances_of_the_api_or_the_rendering_stops(
    api: dict[str, int], fails: bool
) -> None:
    if not fails:
        assert rendered({"api": api})
        return
    with pytest.raises(ChartError, match=r"postgresql\.maxConnections: 300 connections"):
        rendered({"api": api})
    # Raised, it passes; the operator's PostgreSQL is sized by the operator.
    assert rendered({"api": api, "postgresql": {"maxConnections": 500}})
    assert rendered({"api": api, **PROVIDED})


def test_the_api_scales_from_one_instance_to_three_by_one_value_that_no_pod_reads() -> None:
    """Only `api.replicas` changes: no checksum, no flag, no other object follows it.

    The authority the chart makes is drawn at each rendering, and made once, at the installation:
    an upgrade never writes it again (US-2840).
    """
    one, three = rendered({"api": {"replicas": 1}}), rendered({"api": {"replicas": 3}})
    assert len(one) == len(three)
    differences = [
        (a["kind"], a["metadata"]["name"], a["spec"].get("replicas"), b["spec"].get("replicas"))
        for a, b in zip(one, three, strict=True)
        if a != b and a["metadata"]["name"] != "waterfall-authority"
    ]
    assert differences == [("Deployment", "waterfall-api", 1, 3)]


@pytest.mark.story("US-2800")
def test_the_chart_and_the_compose_of_production_designate_the_same_images() -> None:
    """Every image the chart renders is one of the Compose's, and every one the chart can run is.

    Propre à l'US : « le chart et le Compose de production désignent chaque image par son
    empreinte, non par une étiquette (#3726) » : the images of the chain by the digest the
    publication writes — WATERFALL_DIGEST_<NAME> of .env, images.digests.<name> of the values —,
    those of third parties by the digest written beside their tag.
    """
    compose = {
        re.sub(r"\$\{WATERFALL_MIRROR:-\}", "", service["image"])
        for service in yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"].values()
    }
    pinned = {
        re.sub(PUBLISHED, lambda found: published(found.group(1)), image) for image in compose
    }
    assert all(PINNED.search(image) for image in pinned), pinned

    def images(values: dict[str, Any]) -> set[str]:
        return {
            container["image"]
            for item in rendered(values)
            if item["kind"] in {"Deployment", "StatefulSet", "Job", "CronJob"}
            for container in containers(item)
        }

    every = images({})
    # Caddy is the door of the Compose, and the proxy in TLS of its front and its storage: the
    # chart runs the proxies alone, the ingress is its door (US-2840).
    assert every == pinned
    # Provided components or not, nothing the chart runs is an image the Compose does not name.
    assert images(PROVIDED) <= pinned
    # A mirror is a prefix of the third parties alone, as WATERFALL_MIRROR is in the Compose.
    mirrored = images({"images": {"mirror": "mirror.example/"}})
    assert {image for image in mirrored if image.startswith("mirror.example/")} == {
        f"mirror.example/{image}" for image in every if not image.startswith("ghcr.io/")
    }


@pytest.mark.story("US-2800")
@pytest.mark.parametrize(
    ("values", "named"),
    [
        ({"images": {"digests": {"waterfall": "0.3.0"}}}, r"images\.digests\.waterfall"),
        ({"images": {"digests": {"front": ""}}}, r"images\.digests\.front"),
        ({"images": {"digests": {"keycloak": "sha256:abc"}}}, r"images\.digests\.keycloak"),
        ({"redis": {"image": "redis:8-alpine"}}, r"redis:8-alpine: an image is designated"),
    ],
    ids=["a tag", "nothing", "a digest cut short", "a third party by its tag"],
)
def test_the_chart_refuses_an_image_designated_otherwise_than_by_its_digest(
    values: dict[str, Any], named: str
) -> None:
    with pytest.raises(ChartError, match=named):
        rendered(values)
