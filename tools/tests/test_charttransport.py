# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chart encrypts every exchange between its services, as the Compose does (US-2840).

« Aucune connexion en clair n'est acceptée par un composant de la plateforme, hors le point de
métriques, qui n'est pas joignable hors du cluster. » (WF-SEC-0010-A). What the rendered objects say
is held here: each server serves in TLS alone, with the certificate for the name of its Service
that a container of initialisation of its pod issues — or, for a data component and the supervision,
that its Secret holds (US-2850) —, under the authority of the platform — the operator's, or
the one the chart makes once, at the installation —; each client checks it against the roots of its
pod; a data component the operator provides is checked against the roots the operator gives apart,
without which the chart does not render (the author's decisions of 2026-11-22 on #4087). The
ingress reaches the front, Keycloak and Grafana in HTTPS, an Ingress for each. Selected by the
marker ``chart`` (``make test-chart``): they need Helm.
"""

import re
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_chart import Objects, containers, environment, of_kind, pod, rendered

from wftools.chart import ChartError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.chart, pytest.mark.requirement("WF-SEC-0010-A")]

ROOTS = "/trust/root.crt"
VERIFIED = f"?sslmode=verify-full&sslrootcert={ROOTS}"
# Each server of the chart whose pod issues its certificate: its workload, the container that
# serves, and the user it runs as, which owns its key.
SERVERS = {
    "api": ("Deployment", "api", "1000:1000"),
    "keycloak": ("Deployment", "keycloak", "1000:0"),
    "front": ("Deployment", "front-proxy", "1000:1000"),
}
# Each data component and the supervision, whose certificate is a Secret: its workload, the
# container that serves, and the group of its pod, which reads its key.
CERTIFIED = {
    "postgres": ("StatefulSet", "postgres", 999),
    "redis": ("Deployment", "redis", 999),
    "storage": ("StatefulSet", "storage-proxy", 1000),
    "prometheus": ("StatefulSet", "prometheus", 65534),
    "alertmanager": ("Deployment", "alertmanager", 65534),
    "grafana": ("Deployment", "grafana", 472),
}
OPERATOR: dict[str, Any] = {"secrets": {"existingSecret": "operator", "values": None}}
EGRESS = [{"ipBlock": {"cidr": "10.0.0.5/32"}}]
# Each data component the operator may provide, alone: the values that give it.
PROVIDED: dict[str, dict[str, Any]] = {
    "postgresql": {
        **OPERATOR,
        "postgresql": {"enabled": False, "host": "postgres.data.svc"},
        "restoreTest": {"egress": {"postgresql": EGRESS}},
    },
    "redis": {**OPERATOR, "redis": {"enabled": False, "host": "redis.data.svc"}},
    "storage": {
        **OPERATOR,
        "storage": {"enabled": False, "address": "https://storage.data.svc:3900"},
        "restoreTest": {"egress": {"storage": EGRESS}},
    },
}


@pytest.fixture(scope="module")
def objects() -> Objects:
    return rendered()


def workloads(objects: Objects) -> list[dict[str, Any]]:
    return [item for item in objects if item["kind"] in {"Deployment", "StatefulSet", "Job"}]


def named(item: dict[str, Any], name: str) -> dict[str, Any]:
    (found,) = [each for each in containers(item) if each["name"] == name]
    return found


def mounts(container: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {mount["mountPath"]: mount for mount in container.get("volumeMounts", [])}


def test_each_server_serves_with_the_certificate_its_pod_issues_for_the_name_of_its_service(
    objects: Objects,
) -> None:
    for component, (kind, server, user) in SERVERS.items():
        item = of_kind(objects, kind)[component]
        init = named(item, "transport")
        script = init["command"][-1]
        assert "waterfall-authority --provided=/authority " in script, component
        assert script.rstrip().endswith(f"waterfall-{component}:{user}"), component
        uid, gid = (int(part) for part in user.split(":"))
        security = init["securityContext"]
        assert (security["runAsUser"], security["runAsGroup"]) == (uid, gid), component
        tls = mounts(named(item, server))["/tls"]
        assert (tls["name"], tls["subPath"], tls["readOnly"]) == (
            "certificates",
            f"waterfall-{component}",
            True,
        ), component
        # The key of the authority: the container of initialisation alone mounts it.
        holding = [
            each["name"]
            for each in containers(item)
            if any(mount["name"] == "authority" for mount in each.get("volumeMounts", []))
        ]
        assert holding == ["transport"], component
        volumes = {volume["name"]: volume for volume in pod(item)["volumes"]}
        assert volumes["authority"]["secret"]["secretName"] == "waterfall-authority"
        assert volumes["certificates"]["emptyDir"]["medium"] == "Memory"


def test_each_data_component_serves_with_the_certificate_its_secret_holds_for_its_service(
    objects: Objects,
) -> None:
    for component, (kind, server, group) in CERTIFIED.items():
        item = of_kind(objects, kind)[component]
        assert "initContainers" not in pod(item) or [
            each["name"] for each in pod(item)["initContainers"]
        ] == ["postgres-volume"], component
        tls = mounts(named(item, server))["/tls"]
        assert (tls["name"], tls["readOnly"], "subPath" in tls) == ("certificates", True, False)
        volumes = {volume["name"]: volume for volume in pod(item)["volumes"]}
        assert set(volumes) & {"authority", "roots", "trust"} == set(), component
        # 0440, readable by the group of the pod alone, in which the server runs.
        assert volumes["certificates"]["secret"] == {
            "secretName": f"waterfall-{component}-tls",
            "defaultMode": 0o440,
        }, component
        assert pod(item)["securityContext"]["fsGroup"] == group, component


def test_no_server_listens_in_the_clear(objects: Objects) -> None:
    postgres = named(of_kind(objects, "StatefulSet")["postgres"], "postgres")["args"]
    for option in ("ssl=on", "ssl_cert_file=/tls/tls.crt", "hba_file=/files/pg_hba.conf"):
        assert option in postgres
    files = of_kind(objects, "ConfigMap")["files"]["data"]["pg_hba.conf"]
    assert re.search(r"^hostnossl\s+all\s+all\s+all\s+reject$", files, re.MULTILINE)
    redis = named(of_kind(objects, "Deployment")["redis"], "redis")["command"][-1]
    assert "--port 0 --tls-port 6379" in redis
    keycloak = environment(named(of_kind(objects, "Deployment")["keycloak"], "keycloak"))
    assert keycloak["KC_HTTP_ENABLED"] == "false"
    # One instance, which opens no port of a cluster, where JGroups would speak in the clear.
    assert keycloak["KC_CACHE"] == "local"
    api = environment(named(of_kind(objects, "Deployment")["api"], "api"))
    assert (api["WATERFALL_PORT"], api["WATERFALL_TLS_CERTIFICATE"]) == ("8443", "/tls/tls.crt")
    # The front and Garage on the loopback of their pods, behind their proxies in TLS.
    front = environment(named(of_kind(objects, "Deployment")["front"], "front"))
    assert front["HOSTNAME"] == "127.0.0.1"
    # Its proxy is given no upstream: the Caddyfile of the Compose falls back on the loopback.
    proxy = named(of_kind(objects, "Deployment")["front"], "front-proxy")
    assert "WATERFALL_FRONT_UPSTREAM" not in environment(proxy)
    served = of_kind(objects, "ConfigMap")["front"]["data"]["Caddyfile.front"]
    assert "reverse_proxy {$WATERFALL_FRONT_UPSTREAM:127.0.0.1:3000}" in served
    garage = of_kind(objects, "ConfigMap")["storage"]["data"]
    assert 'api_bind_addr = "127.0.0.1:3902"' in garage["garage.toml"]
    assert 'rpc_bind_addr = "127.0.0.1:3901"' in garage["garage.toml"]
    assert "reverse_proxy 127.0.0.1:3902" in garage["Caddyfile.storage"]
    grafana = environment(named(of_kind(objects, "Deployment")["grafana"], "grafana"))
    assert grafana["GF_SERVER_PROTOCOL"] == "https"
    prometheus = named(of_kind(objects, "StatefulSet")["prometheus"], "prometheus")
    assert "--web.config.file=/etc/prometheus/web.yml" in prometheus["args"]
    served = yaml.safe_load(of_kind(objects, "ConfigMap")["prometheus"]["data"]["web.yml"])
    assert served["tls_server_config"]["cert_file"] == "/tls/tls.crt"
    manager = named(of_kind(objects, "Deployment")["alertmanager"], "alertmanager")
    assert "--web.config.file=/etc/waterfall/alertmanager-web.yml" in manager["args"]
    # Every probe of a server reaches it in HTTPS.
    for item in workloads(objects):
        for each in containers(item):
            for probe in ("readinessProbe", "livenessProbe", "startupProbe"):
                if "httpGet" in each.get(probe, {}):
                    assert each[probe]["httpGet"]["scheme"] == "HTTPS", each["name"]


def test_every_client_reaches_its_server_encrypted_and_checks_it_against_the_roots(
    objects: Objects,
) -> None:
    found = 0
    for item in [*workloads(objects), *(i for i in objects if i["kind"] == "CronJob")]:
        for each in containers(item):
            variables = environment(each)
            for variable, value in variables.items():
                if not isinstance(value, str):
                    continue
                where = (item["metadata"]["name"], each["name"], variable)
                if value.startswith(("postgresql://", "jdbc:postgresql://")):
                    assert value.endswith(VERIFIED), where
                    found += 1
                elif value.startswith("redis"):
                    assert value.startswith("rediss://"), where
                    found += 1
                assert not value.startswith("http://"), where
            if "WATERFALL_DATABASE_URL" in variables:
                assert variables["WATERFALL_TLS_AUTHORITY"] == ROOTS, each["name"]
                assert mounts(each)["/trust"]["readOnly"] is True, each["name"]
            if "PGHOST" in variables:
                assert (variables["PGSSLMODE"], variables["PGSSLROOTCERT"]) == (
                    "verify-full",
                    ROOTS,
                )
    assert found
    # Keycloak reaches the front on its back channel in HTTPS, trusting the roots (TFX-17).
    keycloak = environment(named(of_kind(objects, "Deployment")["keycloak"], "keycloak"))
    assert keycloak["KC_TRUSTSTORE_PATHS"] == ROOTS
    realm = environment(named(of_kind(objects, "Job")["realm"], "realm"))
    assert realm["WATERFALL_FRONT_BACKCHANNEL"] == "https://waterfall-front:3443"
    assert realm["KEYCLOAK_URL"] == "https://waterfall-keycloak:8443/auth"
    assert realm["WATERFALL_TLS_AUTHORITY"] == ROOTS
    front = environment(named(of_kind(objects, "Deployment")["front"], "front"))
    assert front["WATERFALL_API_ADDRESS"] == "https://waterfall-api:8443"
    assert front["NODE_EXTRA_CA_CERTS"] == ROOTS
    (buckets,) = pod(of_kind(objects, "Job")["buckets"])["containers"]
    assert environment(buckets)["STORAGE_AUTHORITY"] == ROOTS
    configuration = yaml.safe_load(
        of_kind(objects, "ConfigMap")["prometheus"]["data"]["prometheus.yml"]
    )
    (manager,) = configuration["alerting"]["alertmanagers"]
    assert (manager["scheme"], manager["tls_config"]) == ("https", {"ca_file": "/tls/ca.crt"})


def test_the_metrics_stay_in_http_on_ports_neither_a_service_nor_the_ingress_routes(
    objects: Objects,
) -> None:
    # TFX-09: the headless Services of Prometheus alone name the ports of the metrics.
    routed = {
        port["port"]
        for component, item in of_kind(objects, "Service").items()
        if not component.endswith("-metrics")
        for port in item["spec"]["ports"]
    }
    assert not {8000, 9100} & routed
    api = environment(named(of_kind(objects, "Deployment")["api"], "api"))
    assert api["WATERFALL_METRICS_PORT"] == "8000"


def test_the_authority_is_made_once_at_the_installation_unless_the_operator_gives_one(
    objects: Objects,
) -> None:
    authority = of_kind(objects, "Secret")["authority"]
    annotations = authority["metadata"]["annotations"]
    # Before any other object, and never at an upgrade: the root stays the same.
    assert annotations["helm.sh/hook"] == "pre-install"
    weights = [
        int(item["metadata"]["annotations"]["helm.sh/hook-weight"])
        for item in objects
        if "helm.sh/hook" in item["metadata"].get("annotations", {}) and item is not authority
    ]
    assert int(annotations["helm.sh/hook-weight"]) < min(weights)
    assert set(authority["data"]) == {"ca.crt", "ca.key"}
    given = rendered({"transport": {"authority": "operator-authority"}})
    assert "authority" not in of_kind(given, "Secret")
    api = of_kind(given, "Deployment")["api"]
    volumes = {volume["name"]: volume for volume in pod(api)["volumes"]}
    assert volumes["authority"]["secret"]["secretName"] == "operator-authority"


@pytest.mark.parametrize("component", PROVIDED)
def test_a_component_provided_without_the_roots_of_its_certificate_stops_the_rendering(
    component: str,
) -> None:
    # D1 (b): no silent fall back on another root, whichever data component the operator provides.
    provided = PROVIDED[component]
    with pytest.raises(ChartError, match=r"transport\.providedAuthority"):
        rendered(provided)
    given = rendered({**provided, "transport": {"providedAuthority": "operator-roots"}})
    roots = {
        volume["name"]: volume for volume in pod(of_kind(given, "Deployment")["api"])["volumes"]
    }
    assert roots["roots"]["projected"]["sources"] == [
        {
            "secret": {
                "name": "waterfall-authority",
                "items": [{"key": "ca.crt", "path": "platform.crt"}],
            }
        },
        {
            "secret": {
                "name": "operator-roots",
                "items": [{"key": "ca.crt", "path": "provided.crt"}],
            }
        },
    ]
    # The roots of the pod: that of the platform, followed by those the operator gives.
    init = named(of_kind(given, "Deployment")["api"], "transport")
    assert f'for root in /roots/*.crt; do cat "$root"; echo; done > {ROOTS}' in init["command"][-1]


def test_the_roots_of_the_pod_are_never_glued_one_to_the_next(tmp_path: Path) -> None:
    # A root whose file does not end with a line feed is followed by one, that the next begins a
    # line of its own: else "-----END CERTIFICATE----------BEGIN CERTIFICATE-----" is no PEM.
    given = rendered({**PROVIDED["redis"], "transport": {"providedAuthority": "operator-roots"}})
    script = named(of_kind(given, "Deployment")["api"], "transport")["command"][-1]
    line = next(each for each in script.splitlines() if "/roots/" in each)
    roots, trust = tmp_path / "roots", tmp_path / "trust"
    roots.mkdir()
    trust.mkdir()
    pem = "-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----"
    (roots / "platform.crt").write_text(pem, encoding="utf-8")
    (roots / "provided.crt").write_text(pem + "\n", encoding="utf-8")
    command = line.replace("/roots/", f"{roots}/").replace(ROOTS, str(trust / "root.crt"))
    subprocess.run(["sh", "-c", f"set -eu; {command}"], check=True)
    written = (trust / "root.crt").read_text(encoding="utf-8")
    assert re.findall(r"^-----(BEGIN|END) CERTIFICATE-----$", written, re.MULTILINE) == [
        "BEGIN",
        "END",
        "BEGIN",
        "END",
    ]


def test_the_ingress_reaches_each_server_in_https_an_ingress_for_each(objects: Objects) -> None:
    # D2 (a): the annotations of each, those of every ingress and its own; the check of the
    # certificate is the controller's configuration (docs/exploitation/chiffrement-chart.md).
    values = {
        "ingress": {
            "annotations": {"every": "one"},
            "backends": {"keycloak": {"annotations": {"backend-protocol": "HTTPS"}}},
        }
    }
    ingresses = {
        item["metadata"]["name"]: item for item in rendered(values) if item["kind"] == "Ingress"
    }
    assert set(ingresses) == {
        "waterfall-ingress-front",
        "waterfall-ingress-keycloak",
        "waterfall-ingress-grafana",
    }
    assert ingresses["waterfall-ingress-keycloak"]["metadata"]["annotations"] == {
        "every": "one",
        "backend-protocol": "HTTPS",
    }
    assert ingresses["waterfall-ingress-front"]["metadata"]["annotations"] == {"every": "one"}
    services = of_kind(objects, "Service")
    for ingress in ingresses.values():
        for rule in ingress["spec"]["rules"]:
            for path in rule["http"]["paths"]:
                backend = path["backend"]["service"]
                assert backend["port"] == {"name": "https"}
                component = backend["name"].removeprefix("waterfall-")
                names = [port["name"] for port in services[component]["spec"]["ports"]]
                assert "https" in names, component
