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
"""

from typing import TYPE_CHECKING, Any

from wftools import chart

if TYPE_CHECKING:
    from collections.abc import Mapping

NAMESPACE = "data"
KEYS = "waterfall-operator"
"""The Secret of the operator, in the namespace of the platform: the chart reads every key of it."""
MANAGER = "wftools.charttrial"
POSTGRES = "postgres"
REDIS = "redis"
STORAGE = "storage"
COMPONENTS = (POSTGRES, REDIS, STORAGE)


def host(component: str) -> str:
    """Return the name of the service of a component, as the pods of any namespace resolve it."""
    return f"{component}.{NAMESPACE}.svc.cluster.local"


def _labels(component: str) -> dict[str, str]:
    return {"app.kubernetes.io/name": component, "app.kubernetes.io/managed-by": MANAGER}


def _workload(
    component: str,
    image: str,
    port: int,
    container: Mapping[str, Any],
    volumes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a Service and the Deployment of a component, one pod, its probes as a command."""
    labels = _labels(component)
    selector = {"app.kubernetes.io/name": component}
    probe: dict[str, Any] = {"exec": container["probe"], "periodSeconds": 2, "timeoutSeconds": 3}
    pod_container = {
        "name": component,
        "image": image,
        "imagePullPolicy": "IfNotPresent",
        **{key: value for key, value in container.items() if key != "probe"},
        "ports": [{"name": component, "containerPort": port}],
        "readinessProbe": probe,
    }
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
                        "containers": [pod_container],
                        "volumes": volumes,
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
    garage = (chart.CHART / "files" / "garage.toml").read_text(encoding="utf-8")
    objects: list[dict[str, Any]] = [
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE}},
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "garage", "namespace": NAMESPACE},
            "data": {"garage.toml": garage},
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
            ],
            "env": [
                _env("POSTGRES_USER", "postgres"),
                _env("POSTGRES_PASSWORD", given["WATERFALL_POSTGRES_ADMIN_PASSWORD"]),
            ],
            "volumeMounts": [{"name": "data", "mountPath": "/var/lib/postgresql"}],
            "probe": {"command": ["pg_isready", "--host", "127.0.0.1", "--username", "postgres"]},
        },
        [{"name": "data", "emptyDir": {}}],
    )
    objects += _workload(
        REDIS,
        image["redis"],
        6379,
        {
            "command": ["sh", "-c", "exec redis-server --requirepass \"$REDISCLI_AUTH\" --save ''"],
            "env": [_env("REDISCLI_AUTH", given["WATERFALL_REDIS_PASSWORD"])],
            "probe": {"command": ["sh", "-c", "redis-cli ping | grep -q PONG"]},
        },
        [],
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
        [{"name": "data", "emptyDir": {}}, {"name": "garage", "configMap": {"name": "garage"}}],
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
    """
    values = {key: value for key, value in base.items() if key != "secrets"}
    values["secrets"] = {"existingSecret": KEYS}
    values["postgresql"] = {"enabled": False, "host": host(POSTGRES)}
    values["redis"] = {"enabled": False, "host": host(REDIS)}
    values["storage"] = {"enabled": False, "address": f"http://{host(STORAGE)}:3900"}
    egress = {"postgresql": [peer(POSTGRES)], "storage": [peer(STORAGE)]}
    values["restoreTest"] = {**base.get("restoreTest", {}), "egress": egress}
    return values
