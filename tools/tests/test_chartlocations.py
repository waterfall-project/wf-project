# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API and the worker read the same file of external locations, in the chart and the Compose.

The copy of a scheduled backup to an external location (WF-ADM-0170, US-2910/L7, #4655): the API
lists and tests the locations a file declares, the worker copies to them, and a file that differed
between the two would make each copy find its location unreachable. The file holds the keys of the
S3 storages, so it is a secret, mounted in the pods of both and named by the same variable
``WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE``, in the chart (the marker ``chart``, ``make
test-chart``) and in ``compose.prod.yaml`` and ``compose.service.yaml`` alike.
"""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_chart import Objects, environment, of_kind, pod, rendered

from wftools import REPOSITORY

VARIABLE = "WATERFALL_EXTERNAL_BACKUP_LOCATIONS_FILE"
PROVIDED = "WATERFALL_EXTERNAL_LOCATIONS_FILE"
COMPOSE = REPOSITORY / "deploy" / "compose"
LOCATIONS = {
    "nas-siege": {
        "kind": "mounted_share",
        "description": "Partage du NAS du siège",
        "directory": "/mnt/nas",
    },
    "secours-lyon": {
        "kind": "s3",
        "address": "https://s3.secours.example",
        "bucket": "waterfall",
        "access_key": "AKIAEXEMPLE",
        "secret_key": "secret-d-exemple",
    },
}
SHARE_VOLUME = {"name": "nas", "nfs": {"server": "nas.example", "path": "/waterfall"}}
SHARE_MOUNT = {"name": "nas", "mountPath": "/mnt/nas"}


def given(**changes: Any) -> dict[str, Any]:
    """Give the values of a chart that declares locations, the changes made to them."""
    return {"backups": {"externalLocations": {"locations": LOCATIONS, **changes}}}


def container(objects: Objects, component: str) -> dict[str, Any]:
    """Return the first container of a Deployment."""
    return pod(of_kind(objects, "Deployment")[component])["containers"][0]


def mounted(objects: Objects, component: str) -> tuple[str, str, dict[str, Any]]:
    """Return what a pod reads the file by: its variable, the path of the mount, its volume."""
    spec = pod(of_kind(objects, "Deployment")[component])
    path = str(environment(container(objects, component))[VARIABLE])
    (mount,) = (
        each
        for each in container(objects, component)["volumeMounts"]
        if each["name"] == "external-locations"
    )
    (volume,) = (each for each in spec["volumes"] if each["name"] == "external-locations")
    assert path == f"{mount['mountPath']}/locations.json"
    assert mount["readOnly"] is True
    return path, mount["name"], volume


@pytest.mark.chart
@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
def test_the_api_and_the_worker_of_the_chart_read_the_same_file_from_one_secret() -> None:
    # « Une sauvegarde planifiée avec copie externe se retrouve sur l'emplacement paramétré » sur
    # une installation déployée : the file the API lists and the worker copies by is one Secret,
    # which the chart makes from the locations it is given, mounted read-only in both pods.
    objects = rendered(given())
    api = mounted(objects, "api")
    worker = mounted(objects, "worker")
    assert api == worker
    secret = of_kind(objects, "Secret")["external-locations"]
    assert api[2]["secret"]["secretName"] == secret["metadata"]["name"]
    assert api[2]["secret"]["items"] == [{"key": "locations.json", "path": "locations.json"}]
    assert json.loads(secret["stringData"]["locations.json"]) == LOCATIONS
    # Readable by the group of the user of the image, not by the others.
    assert api[2]["secret"]["defaultMode"] == 0o440
    for component in ("api", "worker"):
        spec = pod(of_kind(objects, "Deployment")[component])
        assert spec["securityContext"]["fsGroup"] == 1000
        assert spec["securityContext"]["runAsNonRoot"] is True


@pytest.mark.chart
@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
def test_a_secret_the_operator_makes_is_mounted_in_both_pods_and_the_chart_makes_none() -> None:
    objects = rendered(given(locations={}, existingSecret="locations-de-l-exploitant"))
    for component in ("api", "worker"):
        assert mounted(objects, component)[2]["secret"]["secretName"] == "locations-de-l-exploitant"
    assert "external-locations" not in of_kind(objects, "Secret")


@pytest.mark.chart
@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
def test_without_locations_nothing_is_mounted_and_the_variable_is_not_set() -> None:
    objects = rendered()
    for component in ("api", "worker"):
        assert VARIABLE not in environment(container(objects, component))
        spec = pod(of_kind(objects, "Deployment")[component])
        assert "external-locations" not in [each["name"] for each in spec["volumes"]]
    assert "external-locations" not in of_kind(objects, "Secret")


@pytest.mark.chart
@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
def test_a_share_is_mounted_in_the_api_and_the_worker_alike() -> None:
    # A location of the nature mounted_share names a folder that must be there, in the pod that
    # tests it and in the pod that copies: the operator's volumes go to both.
    objects = rendered(given(volumes=[SHARE_VOLUME], volumeMounts=[SHARE_MOUNT]))
    for component in ("api", "worker"):
        spec = pod(of_kind(objects, "Deployment")[component])
        assert SHARE_VOLUME in spec["volumes"]
        assert SHARE_MOUNT in container(objects, component)["volumeMounts"]


@pytest.mark.chart
@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
def test_the_worker_of_the_chart_bounds_the_copy_as_the_compose_does() -> None:
    # #4656: the operating parameter that bounds a copy, one hour, on the worker of both.
    compose = yaml.safe_load((COMPOSE / "compose.prod.yaml").read_text(encoding="utf-8"))
    name = "WATERFALL_EXTERNAL_COPY_TIMEOUT_SECONDS"
    variables = environment(container(rendered(), "worker"))
    assert variables[name] == "3600"
    assert compose["services"]["worker"]["environment"][name] == f"${{{name}:-3600}}"
    assert name not in environment(container(rendered(), "api"))


def read(name: str) -> dict[str, Any]:
    return yaml.safe_load((COMPOSE / name).read_text(encoding="utf-8"))


@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
@pytest.mark.parametrize(
    ("file", "source"),
    [
        ("compose.prod.yaml", f"${{{PROVIDED}:-./external-locations.none.json}}"),
        ("compose.service.yaml", "./service-external-locations.json"),
    ],
)
def test_the_api_and_the_worker_of_the_compose_mount_the_same_file_of_locations(
    file: str, source: str
) -> None:
    # The same secret, the same variable, the same path, in the two services; the file is the one
    # the operator names, or the one that declares none.
    compose = read(file)
    api, worker = compose["services"]["api"], compose["services"]["worker"]
    assert api["secrets"] == worker["secrets"] == ["external-locations"]
    assert compose["secrets"] == {"external-locations": {"file": source}}
    expected = "/run/secrets/external-locations"
    assert api["environment"][VARIABLE] == worker["environment"][VARIABLE] == expected


def test_the_file_of_locations_that_declares_none_is_an_empty_object() -> None:
    assert json.loads((COMPOSE / "external-locations.none.json").read_text("utf-8")) == {}


@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.story("US-2910")
def test_the_service_platform_declares_a_share_both_services_mount_at_its_directory() -> None:
    # #4667: the location mounted_share, a folder of the volume external-share which the API tests
    # and the worker copies to; the paths of the front choose it, test it and find the copy there.
    declared = json.loads((COMPOSE / "service-external-locations.json").read_text("utf-8"))
    assert set(declared) == {"mounted_share"}
    assert declared["mounted_share"]["kind"] == "mounted_share"
    directory = declared["mounted_share"]["directory"]
    compose = read("compose.service.yaml")
    for service in ("api", "worker"):
        assert f"external-share:{directory}" in compose["services"][service]["volumes"]
    assert "external-share" in compose["volumes"]
    secret = Path(COMPOSE / "service-external-locations.json").read_text("utf-8")
    assert "secret_key" not in secret
