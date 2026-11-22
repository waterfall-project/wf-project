# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The data components an operator provides, as the trial of the chart poses them (US-2800/L2).

The chart leaves PostgreSQL, Redis and the object storage to the operator's when its values say so
(``enabled: false``, an address, the Secret of the operator): the trial installs it on that footing,
on the cluster it has already made, with these components posed beside it in a namespace of their
own, ``data``, by plain manifests and no chart. They are the images the chart pins, read from its
values, set as an operator would: PostgreSQL with the settings the platform asks of a server
(1 024 locks per transaction, the connections of the chart), a Redis with its password, Garage on
one node with the key and the secrets of the Secret. Nothing is kept: the volumes are
``emptyDir`` of a cluster deleted at the end.

Each serves in TLS alone, as the chart's own do (US-2840): PostgreSQL refuses the clear by the
``pg_hba.conf`` of the Compose, Redis opens no port in the clear, and Garage, which does not
encrypt, listens on the loopback of its pod behind the Caddy of the Compose. Their certificates are
those the trial issues for their names, under an authority of its own, in the Secret
``<component>-tls`` of the namespace; the platform checks them against the roots of ``ROOTS``, the
Secret the operator gives (``transport.providedAuthority``, the author's decision of 2026-11-22 on
#4087).
"""

from typing import TYPE_CHECKING, Any

from wftools import chart

if TYPE_CHECKING:
    from collections.abc import Mapping

NAMESPACE = "data"
KEYS = "waterfall-operator"
"""The Secret of the operator, in the namespace of the platform: the chart reads every key of it."""
ROOTS = "waterfall-data-roots"
"""The Secret of the operator whose key ca.crt is the root of the certificates of the components."""
TLS = "/tls"
"""Where each component reads its certificate, its key and the root, from its Secret."""
MANAGER = "wftools.charttrial"
POSTGRES = "postgres"
REDIS = "redis"
STORAGE = "storage"
COMPONENTS = (POSTGRES, REDIS, STORAGE)


def host(component: str) -> str:
    """Return the name of the service of a component, as the pods of any namespace resolve it."""
    return f"{component}.{NAMESPACE}.svc.cluster.local"


def certificates(component: str) -> str:
    """Return the Secret of the certificate of a component: tls.crt, tls.key and ca.crt."""
    return f"{component}-tls"


def _tls_volume(component: str, group: int | None) -> dict[str, Any]:
    """Return the volume of the certificate of a component, its key readable by its group alone.

    The files are root's; PostgreSQL takes a key of root's readable by its group, the group of
    the pod (``fsGroup``), and no one else.
    """
    secret: dict[str, Any] = {"secretName": certificates(component)}
    if group is not None:
        secret["defaultMode"] = 0o440
    return {"name": "tls", "secret": secret}


def _labels(component: str) -> dict[str, str]:
    return {"app.kubernetes.io/name": component, "app.kubernetes.io/managed-by": MANAGER}


def _workload(
    component: str,
    image: str,
    port: int,
    container: Mapping[str, Any],
    pod: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return a Service and the Deployment of a component, one pod, its probes as a command.

    ``pod`` is the rest of the specification of the pod: its volumes, its group, the containers
    beside the first.
    """
    labels = _labels(component)
    selector = {"app.kubernetes.io/name": component}
    probe: dict[str, Any] = {"exec": container["probe"], "periodSeconds": 2, "timeoutSeconds": 3}
    pod_container = {
        "name": component,
        "image": image,
        "imagePullPolicy": "IfNotPresent",
        **{key: value for key, value in container.items() if key != "probe"},
        "readinessProbe": probe,
    }
    beside = list(pod.get("containers", []))
    if not beside:
        pod_container["ports"] = [{"name": component, "containerPort": port}]
    extra = {key: value for key, value in pod.items() if key != "containers"}
    metadata = {"name": component, "namespace": NAMESPACE, "labels": labels}
    return [
        {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": metadata,
            "spec": {"selector": selector, "ports": [{"port": port, "targetPort": port}]},
        },
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": metadata,
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": selector},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "enableServiceLinks": False,
                        **extra,
                        "containers": [pod_container, *beside],
                    },
                },
            },
        },
    ]


def _env(name: str, value: str) -> dict[str, str]:
    return {"name": name, "value": value}


def manifests(given: Mapping[str, str], mirror: str) -> list[dict[str, Any]]:
    """Return the manifests of the three components, from the secrets drawn for the platform.

    ``mirror`` is the prefix of the third-party images, as ``images.mirror`` gives it to the chart.
    """
    shipped = chart.defaults()
    image = {
        name: f"{mirror}{shipped[name]['image']}" for name in ("postgresql", "redis", "storage")
    }
    files = chart.CHART / "files"
    # Garage on the loopback of its pod, behind its proxy in TLS, as the chart sets its own.
    garage = (
        (files / "garage.toml")
        .read_text(encoding="utf-8")
        .replace('"[::]:3900"', '"127.0.0.1:3902"')
        .replace('"[::]:3901"', '"127.0.0.1:3901"')
    )
    proxy = (
        (files / "Caddyfile.storage")
        .read_text(encoding="utf-8")
        .replace("reverse_proxy garage:3900", "reverse_proxy 127.0.0.1:3902")
    )
    objects: list[dict[str, Any]] = [
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE}},
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "garage", "namespace": NAMESPACE},
            "data": {
                "garage.toml": garage,
                "Caddyfile.storage": proxy,
                "pg_hba.conf": (files / "pg_hba.conf").read_text(encoding="utf-8"),
            },
        },
    ]
    connections = shipped["postgresql"]["maxConnections"]
    objects += _workload(
        POSTGRES,
        image["postgresql"],
        5432,
        {
            "args": [
                "postgres",
                "-c",
                "max_locks_per_transaction=1024",
                "-c",
                f"max_connections={connections}",
                "-c",
                "ssl=on",
                "-c",
                f"ssl_cert_file={TLS}/tls.crt",
                "-c",
                f"ssl_key_file={TLS}/tls.key",
                "-c",
                "hba_file=/files/pg_hba.conf",
            ],
            "env": [
                _env("POSTGRES_USER", "postgres"),
                _env("POSTGRES_PASSWORD", given["WATERFALL_POSTGRES_ADMIN_PASSWORD"]),
            ],
            "volumeMounts": [
                {"name": "data", "mountPath": "/var/lib/postgresql"},
                {"name": "garage", "mountPath": "/files", "readOnly": True},
                {"name": "tls", "mountPath": TLS, "readOnly": True},
            ],
            "probe": {"command": ["pg_isready", "--host", "127.0.0.1", "--username", "postgres"]},
        },
        {
            # The group of the user postgres of the image, which reads the key.
            "securityContext": {"fsGroup": 999},
            "volumes": [
                {"name": "data", "emptyDir": {}},
                {"name": "garage", "configMap": {"name": "garage"}},
                _tls_volume(POSTGRES, 999),
            ],
        },
    )
    objects += _workload(
        REDIS,
        image["redis"],
        6379,
        {
            "command": [
                "sh",
                "-c",
                (
                    "exec redis-server --requirepass \"$REDISCLI_AUTH\" --save '' --port 0"
                    f" --tls-port 6379 --tls-cert-file {TLS}/tls.crt --tls-key-file {TLS}/tls.key"
                    f" --tls-ca-cert-file {TLS}/ca.crt --tls-auth-clients no"
                ),
            ],
            "env": [_env("REDISCLI_AUTH", given["WATERFALL_REDIS_PASSWORD"])],
            "volumeMounts": [{"name": "tls", "mountPath": TLS, "readOnly": True}],
            "probe": {
                "command": [
                    "sh",
                    "-c",
                    f"redis-cli --tls --cacert {TLS}/ca.crt -h localhost ping | grep -q PONG",
                ]
            },
        },
        {
            # The user redis of the image, and its group, which reads the key.
            "securityContext": {"runAsUser": 999, "fsGroup": 1000},
            "volumes": [_tls_volume(REDIS, 1000)],
        },
    )
    objects += _workload(
        STORAGE,
        image["storage"],
        3900,
        {
            "command": ["/garage", "server", "--single-node", "--default-access-key"],
            "env": [
                _env("GARAGE_RPC_SECRET", given["WATERFALL_STORAGE_RPC_SECRET"]),
                _env("GARAGE_DEFAULT_ACCESS_KEY", shipped["storage"]["accessKey"]),
                _env("GARAGE_DEFAULT_SECRET_KEY", given["WATERFALL_STORAGE_SECRET"]),
            ],
            "volumeMounts": [
                {"name": "data", "mountPath": "/var/lib/garage"},
                {"name": "garage", "mountPath": "/etc/garage.toml", "subPath": "garage.toml"},
            ],
            "probe": {"command": ["/garage", "status"]},
        },
        {
            "volumes": [
                {"name": "data", "emptyDir": {}},
                {"name": "garage", "configMap": {"name": "garage"}},
                _tls_volume(STORAGE, None),
            ],
            "containers": [
                {
                    "name": "storage-proxy",
                    "image": f"{mirror}{shipped['transport']['proxyImage']}",
                    "imagePullPolicy": "IfNotPresent",
                    "command": [
                        "caddy",
                        "run",
                        "--config",
                        "/etc/caddy/Caddyfile.storage",
                        "--adapter",
                        "caddyfile",
                    ],
                    "ports": [{"name": STORAGE, "containerPort": 3900}],
                    "volumeMounts": [
                        {
                            "name": "garage",
                            "mountPath": "/etc/caddy/Caddyfile.storage",
                            "subPath": "Caddyfile.storage",
                        },
                        {"name": "tls", "mountPath": TLS, "readOnly": True},
                    ],
                }
            ],
        },
    )
    return objects


def peer(component: str) -> dict[str, Any]:
    """Return a component as a NetworkPolicy names it: its pods, in the namespace of the data."""
    return {
        "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": NAMESPACE}},
        "podSelector": {"matchLabels": _labels(component)},
    }


def provided_values(base: Mapping[str, Any]) -> dict[str, Any]:
    """Return the values of an installation on these components: the Secret of the operator's.

    The pod of the test of a restoration reaches the PostgreSQL and the storage by their pods alone.
    Their certificates are checked against the roots of ``ROOTS``.
    """
    values = {key: value for key, value in base.items() if key != "secrets"}
    values["secrets"] = {"existingSecret": KEYS}
    values["postgresql"] = {"enabled": False, "host": host(POSTGRES)}
    values["redis"] = {"enabled": False, "host": host(REDIS)}
    values["storage"] = {"enabled": False, "address": f"https://{host(STORAGE)}:3900"}
    values["transport"] = {**base.get("transport", {}), "providedAuthority": ROOTS}
    egress = {"postgresql": [peer(POSTGRES)], "storage": [peer(STORAGE)]}
    values["restoreTest"] = {**base.get("restoreTest", {}), "egress": egress}
    return values
