# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Every pod of the chart runs at the level « restricted » of the Pod Security Standards (US-2800).

The author's decision of 2026-11-22 on #4664: ``podDefaults`` gives each pod ``runAsNonRoot`` and
the profile seccomp of the runtime, ``containerSecurity`` gives each container no privilege gained
and no capability, the Job of the test of a restoration included, which the schedule makes from the
manifest the chart renders into its ConfigMap. A process the kubelet cannot hold against
``runAsNonRoot`` — an image that runs as root, or as a user it names by a name — does not start:
each container runs as a number it is given, or is an image of the chain, whose Dockerfile names a
number. No image of the chart needs an exception: the data components run as the user of their
image — PostgreSQL as postgres, from the start —, Garage and Caddy as a user of no name. Selected by
the marker ``chart`` (``make test-chart``).
"""

import json
import re
from typing import Any

import pytest
from test_chart import Objects, of_kind, pod, rendered

from wftools import REPOSITORY
from wftools.images import IMAGES, REGISTRY

pytestmark = [pytest.mark.chart, pytest.mark.story("US-2800")]

WORKLOADS = {"Deployment", "StatefulSet", "Job", "CronJob"}
# The volumes the level restricted allows a pod.
VOLUMES = {
    "configMap",
    "csi",
    "downwardAPI",
    "emptyDir",
    "ephemeral",
    "persistentVolumeClaim",
    "projected",
    "secret",
}
USER = re.compile(r"^USER\s+(\S+)\s*$", re.MULTILINE)


@pytest.fixture(scope="module")
def pods() -> dict[str, dict[str, Any]]:
    """Return the specification of every pod the chart renders, by name, the Job of the test too."""
    objects: Objects = rendered()
    found = {item["metadata"]["name"]: pod(item) for item in objects if item["kind"] in WORKLOADS}
    job = json.loads(of_kind(objects, "ConfigMap")["restore-test"]["data"]["job.json"])
    found[job["metadata"]["name"]] = job["spec"]["template"]["spec"]
    return found


def published_users() -> dict[str, int]:
    """Return the user each image of the chain runs as: the last USER of its Dockerfile."""
    users: dict[str, int] = {}
    for image in IMAGES:
        dockerfile = (REPOSITORY / image.context / "Dockerfile").read_text(encoding="utf-8")
        users[f"{REGISTRY}/{image.name}"] = int(USER.findall(dockerfile)[-1].split(":")[0])
    return users


def test_every_pod_runs_as_no_root_under_the_profile_seccomp_of_the_runtime(
    pods: dict[str, dict[str, Any]],
) -> None:
    # The chart's own pods, its hooks, its CronJob, and the Job of the test of a restoration.
    assert {"waterfall-postgres", "waterfall-migrate", "waterfall-restore-test"} <= pods.keys()
    for name, spec in pods.items():
        security = spec["securityContext"]
        assert security["runAsNonRoot"] is True, name
        assert security["seccompProfile"] == {"type": "RuntimeDefault"}, name
        assert security.get("runAsUser") != 0, name
        assert not {"hostNetwork", "hostPID", "hostIPC"} & spec.keys(), name
        for volume in spec.get("volumes", []):
            assert set(volume) - {"name"} <= VOLUMES, (name, volume["name"])


def test_every_container_gains_no_privilege_holds_no_capability_and_runs_as_a_number(
    pods: dict[str, dict[str, Any]],
) -> None:
    users = published_users()
    assert all(user > 0 for user in users.values()), users
    for name, spec in pods.items():
        for container in spec.get("initContainers", []) + spec["containers"]:
            where = f"{name}/{container['name']}"
            security = container["securityContext"]
            assert security["allowPrivilegeEscalation"] is False, where
            assert security["capabilities"] == {"drop": ["ALL"]}, where
            assert "privileged" not in security, where
            assert security.get("runAsNonRoot") is not False, where
            user = security.get("runAsUser", spec["securityContext"].get("runAsUser"))
            if user is None:
                image = container["image"].split("@", 1)[0]
                assert image in users, f"{where}: {container['image']} runs as no number given"
                user = users[image]
            assert user > 0, where


def test_the_servers_of_the_test_of_a_restoration_own_their_keys_without_root(
    pods: dict[str, dict[str, Any]],
) -> None:
    # The authority of the test makes the key of each server as the user it runs as, 1000, and
    # gives it to nobody else: PostgreSQL runs as that user, which reads the password of the test.
    spec = pods["waterfall-restore-test"]
    initial = {container["name"]: container for container in spec["initContainers"]}
    authority = initial["restore-test-authority"]
    assert "runAsUser" not in authority["securityContext"]
    assert [part for part in authority["command"] if part.startswith("restore-test-")] == [
        "restore-test-postgres:1000:1000",
        "restore-test-keycloak:1000:1000",
        "restore-test-api:1000:1000",
    ]
    assert initial["postgres"]["securityContext"]["runAsUser"] == 1000
