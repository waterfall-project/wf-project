# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The production Compose encrypts every exchange between its services (US-2840).

« Aucune connexion en clair n'est acceptée par un composant de la plateforme, hors le point de
métriques, qui n'est pas joignable hors du cluster. » (WF-SEC-0010-A). What the files say is held
here: each server serves in TLS alone, with the certificate the authority of the platform issues
it, and each client checks it against the root. The platform itself is tried by
``make production-trial``, whose probe (``wftools.transport``) speaks in the clear to each server;
these tests hold what the trial concludes from what the probe answers.
"""

import ipaddress
import json
import re
from typing import Any

import pytest
import yaml

from wftools import REPOSITORY, transport
from wftools.transport import TransportError

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
LOCAL = COMPOSE / "compose.prod.local.yaml"
ROOT = "/trust/root.crt"
TRUST = "trust:/trust:ro"
VERIFIED = f"sslmode=verify-full&sslrootcert={ROOT}"
# Where each server reads its certificate, by the service that serves it.
SERVERS = {
    "postgres": "postgres",
    "redis": "redis",
    "api": "api",
    "keycloak": "keycloak",
    "storage": "storage-proxy",
}
# A variable that gives a service the address of another: Waterfall's, and their equivalents in the
# services of Keycloak's image and of the buckets of the storage.
ADDRESS = re.compile(r"^(WATERFALL_\w+_(URL|ADDRESS|BACKCHANNEL)|STORAGE_ADDRESS|KEYCLOAK_URL)$")
WATERFALL_IMAGE = "ghcr.io/waterfall-project/waterfall:"
# Where a client outside the back reads the root from: the server of Next, the curl of the buckets.
TRUSTING = {"front": "NODE_EXTRA_CA_CERTS", "storage-buckets": "STORAGE_AUTHORITY"}
# An address a service is given and does not reach: Caddy's is its own, where it sends HTTP to; it
# checks Keycloak, which it reaches, by its Caddyfile.
PUBLISHED = {"caddy": {"WATERFALL_ADDRESS"}}


def compose(path: str = "compose.prod.yaml") -> dict[str, Any]:
    """Read a Compose file."""
    return yaml.safe_load((COMPOSE / path).read_text(encoding="utf-8"))


def services() -> dict[str, Any]:
    """Read the services of the production platform."""
    return compose()["services"]


def environment(service: str) -> dict[str, str]:
    """Read the environment of a service, its anchors merged."""
    return {name: str(value) for name, value in services()[service].get("environment", {}).items()}


def addresses() -> list[tuple[str, str, str]]:
    """Give every address a service is given, as (service, variable, value)."""
    return [
        (name, variable, value)
        for name in services()
        for variable, value in environment(name).items()
        if re.match(r"^(postgresql|jdbc:postgresql|redis|rediss|https?)://", value)
    ]


def is_client(name: str, service: dict[str, Any]) -> bool:
    """Tell whether a service reaches another: given an address, or the back with an environment."""
    given = {variable for variable in service.get("environment", {}) if ADDRESS.match(variable)}
    of_the_back = str(service.get("image", "")).startswith(WATERFALL_IMAGE)
    return bool(given - PUBLISHED.get(name, set())) or (
        of_the_back and bool(service.get("environment"))
    )


def untrusting(found: dict[str, Any]) -> list[str]:
    """Name each client of the platform that is not given the root to check its servers against.

    Every service is read: one added with an address, or with the environment of the back, and
    without the root, is named.
    """
    faults: list[str] = []
    for name, service in found.items():
        variable = TRUSTING.get(name, "WATERFALL_TLS_AUTHORITY")
        if is_client(name, service) and service.get("environment", {}).get(variable) != ROOT:
            faults.append(f"{name} lacks {variable}")
    return faults


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_authority_issues_the_certificate_of_each_server_for_it_alone() -> None:
    authority = services()["authority"]
    command = authority["command"]
    assert command[0] == "waterfall-authority"
    served = {each.split(":")[0] for each in command if re.fullmatch(r"[a-z]+:\d+:\d+", each)}
    assert served == set(transport.SERVED) == set(SERVERS)
    for name, server in SERVERS.items():
        volume = f"certificates-{name}"
        assert f"{volume}:/certificates/{name}" in authority["volumes"]
        mounting = [
            service
            for service, found in services().items()
            if any(str(mount).startswith(f"{volume}:") for mount in found.get("volumes", []))
        ]
        # The authority writes it; its server alone reads it.
        assert sorted(mounting) == sorted(["authority", server]), volume
        assert f"{volume}:/tls:ro" in services()[server]["volumes"]
    # The root and its key: the authority's alone.
    holding = [
        service
        for service, found in services().items()
        if any(str(mount).startswith("authority:") for mount in found.get("volumes", []))
    ]
    assert holding == ["authority"]


@pytest.mark.requirement("WF-SEC-0010-A")
def test_postgresql_redis_keycloak_and_the_api_serve_in_tls_alone() -> None:
    found = services()
    script = found["postgres"]["entrypoint"][2]
    for option in (
        "-c ssl=on",
        "-c ssl_cert_file=/tls/tls.crt",
        "-c ssl_key_file=/tls/tls.key",
        "-c hba_file=/etc/waterfall/pg_hba.conf",
    ):
        assert option in script
    assert "./pg_hba.conf:/etc/waterfall/pg_hba.conf:ro" in found["postgres"]["volumes"]
    access = [
        line.split()
        for line in (COMPOSE / "pg_hba.conf").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    assert access == [
        ["local", "all", "all", "trust"],
        ["hostssl", "all", "all", "all", "scram-sha-256"],
        ["hostnossl", "all", "all", "all", "reject"],
    ]
    redis = found["redis"]["command"][2]
    assert (
        "--port 0 --tls-port 6379 --tls-cert-file /tls/tls.crt --tls-key-file /tls/tls.key" in redis
    )
    keycloak = environment("keycloak")
    assert keycloak["KC_HTTP_ENABLED"] == "false"
    assert (keycloak["KC_HTTPS_CERTIFICATE_FILE"], keycloak["KC_HTTPS_CERTIFICATE_KEY_FILE"]) == (
        "/tls/tls.crt",
        "/tls/tls.key",
    )
    # Its management, which answers its health check, on the loopback of its container alone.
    assert (keycloak["KC_HTTP_MANAGEMENT_SCHEME"], keycloak["KC_HTTP_MANAGEMENT_HOST"]) == (
        "http",
        "127.0.0.1",
    )
    # One instance, which opens no port of a cluster (7800, 57800).
    assert keycloak["KC_CACHE"] == "local"
    assert {"keycloak-cluster", "keycloak-cluster-detection"} <= set(transport.CLOSED)
    api = environment("api")
    assert (api["WATERFALL_TLS_CERTIFICATE"], api["WATERFALL_TLS_KEY"]) == (
        "/tls/tls.crt",
        "/tls/tls.key",
    )
    # In TLS on 8443; its metrics alone in HTTP, on 8000, where Prometheus collects them as the
    # chart's does (TFX-09).
    assert (api["WATERFALL_PORT"], api["WATERFALL_METRICS_PORT"]) == ("8443", "8000")
    collected = yaml.safe_load((COMPOSE / "prometheus.yml").read_text(encoding="utf-8"))
    (job,) = [job for job in collected["scrape_configs"] if job["job_name"] == "api"]
    assert (job["metrics_path"], job["dns_sd_configs"][0]["port"]) == ("/api/v1/metrics", 8000)


def image_environment(stage: str) -> dict[str, str]:
    """Read the variables the ENV of a stage of the image of the back sets."""
    dockerfile = (REPOSITORY / "backend" / "Dockerfile").read_text(encoding="utf-8")
    lines = re.MULTILINE | re.DOTALL
    (body,) = re.findall(rf"^FROM \S+ AS {stage}\n(.*?)(?=^FROM |\Z)", dockerfile, lines)
    found: dict[str, str] = {}
    for instruction in re.findall(r"^ENV (.*?)(?<!\\)\n", body, lines):
        found.update(re.findall(r"(\w+)=(\S+?)\"?(?:\s|\\|$)", instruction))
    return found


@pytest.mark.requirement("WF-SEC-0010-A")
def test_prometheus_reaches_the_metrics_of_the_api_where_its_processes_serve_them() -> None:
    # The port of the metrics listens on WATERFALL_HOST, the image's unless the Compose says it:
    # every interface of the container, where Prometheus, on the network of the platform, finds the
    # API by its name, at the port and the path it collects, in HTTP (TFX-09).
    served = {**image_environment("production"), **environment("api")}
    assert ipaddress.ip_address(served["WATERFALL_HOST"]).is_unspecified
    collected = yaml.safe_load((COMPOSE / "prometheus.yml").read_text(encoding="utf-8"))
    (job,) = [job for job in collected["scrape_configs"] if job["job_name"] == "api"]
    (found,) = job["dns_sd_configs"]
    assert found["names"] == ["api"]
    assert str(found["port"]) == served["WATERFALL_METRICS_PORT"] != served["WATERFALL_PORT"]
    assert (job["metrics_path"], job.get("scheme", "http")) == ("/api/v1/metrics", "http")
    # Both on the network of the platform, and the port published nowhere.
    for name in ("api", "prometheus"):
        assert set(services()[name].get("networks", ["default"])) == {"default"}, name
        assert "ports" not in services()[name], name


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_object_storage_is_reached_through_its_proxy_in_tls_alone() -> None:
    found = services()
    # Garage on a network of its own, which nothing leaves and which its proxy alone joins.
    assert found["storage"]["networks"] == {"storage": {"aliases": ["garage"]}}
    assert compose()["networks"]["storage"] == {"internal": True}
    joining = [name for name, service in found.items() if "storage" in service.get("networks", {})]
    assert sorted(joining) == ["storage", "storage-proxy"]
    proxy = found["storage-proxy"]
    assert proxy["networks"]["default"] == {"aliases": ["storage"]}
    caddyfile = (COMPOSE / "Caddyfile.storage").read_text(encoding="utf-8")
    assert re.search(
        r"https://:3900 \{\s*tls /tls/tls\.crt /tls/tls\.key\s*reverse_proxy garage:3900\s*\}",
        caddyfile,
    )
    buckets = environment("storage-buckets")
    assert (buckets["STORAGE_ADDRESS"], buckets["STORAGE_AUTHORITY"]) == (
        "https://storage:3900",
        ROOT,
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_every_client_reaches_its_server_encrypted_and_checks_it_against_the_root() -> None:
    found = addresses()
    assert found
    for service, variable, value in found:
        where = (service, variable)
        if value.startswith(("postgresql://", "jdbc:postgresql://")):
            assert value.endswith(f"?{VERIFIED}"), where
        elif value.startswith("redis"):
            assert value.startswith("rediss://"), where
        # The only addresses in HTTP: those of the browser's side, which Keycloak gives back to the
        # front by its back channel (TFX-17), out of this lot.
        elif value.startswith("http://"):
            assert (service, variable) == ("keycloak-realm", "WATERFALL_FRONT_BACKCHANNEL"), where
    for name, service in services().items():
        values = " ".join(environment(name).values())
        if ROOT in values:
            assert TRUST in service.get("volumes", []), name
    assert untrusting(services()) == []
    for name in ("waterfall-database", "service-database-role", "backup-database-role"):
        found_environment = environment(name)
        assert (found_environment["PGSSLMODE"], found_environment["PGSSLROOTCERT"]) == (
            "verify-full",
            ROOT,
        )
    front = environment("front")
    assert front["WATERFALL_API_ADDRESS"] == "https://api:8443"
    assert front["NODE_EXTRA_CA_CERTS"] == ROOT
    assert environment("keycloak-realm")["KEYCLOAK_URL"] == "https://keycloak:8443/auth"
    door = (COMPOSE / "Caddyfile.prod").read_text(encoding="utf-8")
    assert re.search(
        r"reverse_proxy https://keycloak:8443 \{\s*header_up Host \{host\}\s*transport http \{\s*"
        rf"tls_trust_pool file {ROOT}\s*\}}",
        door,
    )
    assert "keycloak:8080" not in door
    assert TRUST in services()["caddy"]["volumes"]


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_service_added_with_an_address_and_without_the_root_is_named() -> None:
    found = services()
    image = found["api"]["image"]
    # The front, its root taken away.
    front = environment("front")
    del front["NODE_EXTRA_CA_CERTS"]
    added = {
        **found,
        # A process of the back, given the environment of the back and nothing else.
        "reporting": {"image": image, "environment": {"WATERFALL_LOG_LEVEL": "INFO"}},
        # Another image, given an address of the platform.
        "exporter": {"image": "exporter:1", "environment": {"WATERFALL_DATABASE_URL": "x"}},
        "front": {**found["front"], "environment": front},
        # A service of no address, which reaches nothing of the platform.
        "quiet": {"image": "quiet:1", "environment": {"TZ": "UTC"}},
    }
    assert untrusting(added) == [
        "front lacks NODE_EXTRA_CA_CERTS",
        "reporting lacks WATERFALL_TLS_AUTHORITY",
        "exporter lacks WATERFALL_TLS_AUTHORITY",
    ]


def test_a_local_name_makes_the_front_trust_the_authority_of_caddy() -> None:
    # Besides the root of the platform, which the copy writes first.
    front = compose("compose.prod.local.yaml")["services"]["front"]
    assert front["environment"]["NODE_EXTRA_CA_CERTS"] == "/roots/roots.crt"
    assert "door-authority:/roots:ro" in front["volumes"]
    copy = " ".join(compose("compose.prod.local.yaml")["services"]["door-authority"]["command"])
    assert "cat /trust/root.crt /data/caddy/pki/authorities/local/root.crt > /roots/" in copy


REFUSED = {
    **dict.fromkeys(transport.SERVED, "refused"),
    **dict.fromkeys(transport.CLOSED, "unreached"),
    transport.METRICS: "metrics alone",
}


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_trial_holds_that_every_server_refuses_the_clear_and_serves_in_tls() -> None:
    transport.check_clear_refused(json.dumps(REFUSED))
    compile(transport.PROBE, "probe", "exec")


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.parametrize(
    ("name", "said", "fault"),
    [
        ("postgres", "accepted", "postgres accepted"),
        ("redis", "no tls", "redis no tls"),
        ("api", "unreached", "api unreached"),
        ("garage", "accepted", "garage accepted"),
        ("keycloak-management", "accepted", "keycloak-management accepted"),
        ("keycloak-cluster", "accepted", "keycloak-cluster accepted"),
        ("keycloak-cluster-detection", "accepted", "keycloak-cluster-detection accepted"),
        ("api-metrics", "accepted", "api-metrics accepted"),
    ],
)
def test_the_trial_fails_naming_a_server_that_does_not_refuse_the_clear(
    name: str, said: str, fault: str
) -> None:
    with pytest.raises(TransportError, match=f"not refused as it must be: {fault}"):
        transport.check_clear_refused(json.dumps({**REFUSED, name: said}))


def test_the_trial_fails_when_a_server_is_not_tried_or_the_probe_does_not_read() -> None:
    left = {name: verdict for name, verdict in REFUSED.items() if name != "storage"}
    with pytest.raises(TransportError, match="storage not tried"):
        transport.check_clear_refused(json.dumps(left))
    for output in ("Traceback (most recent call last):", "[]"):
        with pytest.raises(TransportError, match="the probe of the transport does not read"):
            transport.check_clear_refused(output)
