# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An upgrade does not restart the data components: their pods name no version (US-2850).

« Une mise à jour de la version N à la version N+1 s'exécute sans qu'aucune requête n'échoue et sans
qu'aucun utilisateur ne soit déconnecté. » (WF-EXP-0030-A). A container of initialisation that ran
the image of Waterfall changed the pods of PostgreSQL, Redis, the storage and the supervision at
each version, and Kubernetes recreated them: Redis lost every session. Their certificates are now
issued by a hook into Secrets their pods mount (the author's decision of 2026-11-26, #4089, option
C): rendered under two versions — the digests of the three images of Waterfall and the version of
the chart, all that names one — their workloads are the same. That the hook writes a Secret only
when due is held by the tests of ``waterfall.platform.authority_secrets``. Selected by the marker
``chart`` (``make test-chart``): they need Helm, which the tools leave out.
"""

import hashlib
import shutil
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_chart import Objects, containers, of_kind, pod, rendered

from wftools import chart

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [
    pytest.mark.chart,
    pytest.mark.requirement("WF-EXP-0030-A"),
    pytest.mark.story("US-2850"),
]

# The data components and the supervision, by their workloads.
CERTIFIED = {
    "postgres": "statefulsets",
    "redis": "deployments",
    "storage": "statefulsets",
    "prometheus": "statefulsets",
    "alertmanager": "deployments",
    "grafana": "deployments",
}
KINDS = {"statefulsets": "StatefulSet", "deployments": "Deployment"}
NEXT = {
    name: f"sha256:{hashlib.sha256(f'{name} N+1'.encode()).hexdigest()}"
    for name in chart.CHAIN_DIGESTS
}
"""The digests of a next version of the three images of Waterfall."""
PROVIDED: dict[str, Any] = {
    "secrets": {"existingSecret": "operator", "values": None},
    "postgresql": {"enabled": False, "host": "postgres.data.svc"},
    "redis": {"enabled": False, "host": "redis.data.svc"},
    "storage": {"enabled": False, "address": "https://storage.data.svc:3900"},
    "restoreTest": {"enabled": False},
    "transport": {"providedAuthority": "operator-roots"},
    "prometheus": {"enabled": False},
    "grafana": {"prometheusUrl": "https://prometheus.operator:9090"},
}
"""The values of an operator who provides the data components and the collection."""


@pytest.fixture(scope="module")
def objects() -> Objects:
    return rendered()


def workload(objects: Objects, component: str) -> dict[str, Any]:
    return of_kind(objects, KINDS[CERTIFIED[component]])[component]


def hooked(objects: Objects, kind: str) -> dict[str, Any]:
    return of_kind(objects, kind)["certificates"]


def next_chart(folder: Path) -> Path:
    """Copy the chart, its files followed, under a next version of the chart and of Waterfall."""
    copied = folder / "waterfall"
    shutil.copytree(chart.CHART, copied)
    described = copied / "Chart.yaml"
    text = described.read_text(encoding="utf-8")
    text = text.replace("\nversion: 0.1.0\n", "\nversion: 0.2.0\n")
    text = text.replace('\nappVersion: "0.1.0"\n', '\nappVersion: "0.2.0"\n')
    described.write_text(text, encoding="utf-8")
    assert yaml.safe_load(text)["version"] == "0.2.0"
    return copied


def test_the_data_components_are_the_same_under_two_versions_of_waterfall(
    objects: Objects, tmp_path: Path
) -> None:
    # A version of Waterfall is its three images, pinned by their digests: the chart has no tag
    # (values.yaml, images.digests), and the version of the chart, which its labels name.
    text = chart.render({"images": {"digests": NEXT}}, chart=next_chart(tmp_path))
    upgraded = [document for document in yaml.safe_load_all(text) if document]
    for component in CERTIFIED:
        assert workload(upgraded, component)["spec"] == workload(objects, component)["spec"], (
            component
        )
    # The version does change what it should: the API is replaced, and the hook runs N+1.
    api = of_kind(objects, "Deployment")["api"]["spec"]
    assert of_kind(upgraded, "Deployment")["api"]["spec"] != api
    (issuing,) = pod(hooked(upgraded, "Job"))["containers"]
    assert issuing["image"].endswith(NEXT["waterfall"])
    labels = workload(upgraded, "redis")["metadata"]["labels"]
    assert labels["app.kubernetes.io/version"] == "0.2.0"


def test_no_pod_of_a_data_component_runs_an_image_of_waterfall(objects: Objects) -> None:
    registry = chart.defaults()["images"]["registry"]
    for component in CERTIFIED:
        images = [each["image"] for each in containers(workload(objects, component))]
        assert images, component
        assert not [image for image in images if image.startswith(registry)], component
        text = yaml.safe_dump(workload(objects, component)["spec"])
        assert not [digest for digest in chart.CHAIN_DIGESTS.values() if digest in text]


def test_the_hook_certifies_each_data_component_after_the_authority_and_before_the_rest(
    objects: Objects,
) -> None:
    job = hooked(objects, "Job")
    annotations = job["metadata"]["annotations"]
    assert annotations["helm.sh/hook"] == "pre-install,pre-upgrade"
    weights = {
        (item["kind"], item["metadata"]["name"]): int(
            item["metadata"]["annotations"]["helm.sh/hook-weight"]
        )
        for item in objects
        if "helm.sh/hook" in item["metadata"].get("annotations", {})
    }
    issuing = weights.pop(("Job", "waterfall-certificates"))
    assert weights.pop(("Secret", "waterfall-authority")) < issuing
    granting = [
        weights.pop((kind, "waterfall-certificates"))
        for kind in ("ServiceAccount", "Role", "RoleBinding")
    ]
    # The migrations, the buckets, the realm and the bootstrap reach the data components after it.
    assert max(granting) < issuing < min(weights.values())
    spec = pod(job)
    assert spec["serviceAccountName"] == "waterfall-certificates"
    (container,) = spec["containers"]
    assert container["command"] == [
        "waterfall-authority",
        "secrets",
        "--provided=/authority",
        *(f"{resource}/waterfall-{component}" for component, resource in CERTIFIED.items()),
    ]
    (authority,) = spec["volumes"]
    assert authority["secret"]["secretName"] == "waterfall-authority"
    assert [item["key"] for item in authority["secret"]["items"]] == ["ca.crt", "ca.key"]
    # Each Secret the hook writes is the one its workload mounts.
    for component in CERTIFIED:
        volumes = {each["name"]: each for each in pod(workload(objects, component))["volumes"]}
        assert volumes["certificates"]["secret"]["secretName"] == f"waterfall-{component}-tls"


def test_the_account_of_the_hook_writes_the_secrets_of_the_certificates_alone(
    objects: Objects,
) -> None:
    role = hooked(objects, "Role")
    secrets = [f"waterfall-{component}-tls" for component in CERTIFIED]
    restarted = {
        resource: [f"waterfall-{c}" for c, r in CERTIFIED.items() if r == resource]
        for resource in ("deployments", "statefulsets")
    }
    # A creation cannot be bound to a name; the reading and the writing of a Secret, and the
    # restart of a workload after a renewal, are.
    assert role["rules"] == [
        {"apiGroups": [""], "resources": ["secrets"], "verbs": ["create"]},
        {
            "apiGroups": [""],
            "resources": ["secrets"],
            "resourceNames": secrets,
            "verbs": ["get", "update"],
        },
        *(
            {
                "apiGroups": ["apps"],
                "resources": [resource],
                "resourceNames": names,
                "verbs": ["patch"],
            }
            for resource, names in restarted.items()
        ),
    ]
    binding = hooked(objects, "RoleBinding")
    assert binding["roleRef"]["name"] == role["metadata"]["name"]
    assert [subject["name"] for subject in binding["subjects"]] == ["waterfall-certificates"]
    # The account and its rights go once the hooks have succeeded.
    for kind in ("ServiceAccount", "Role", "RoleBinding"):
        policy = hooked(objects, kind)["metadata"]["annotations"]["helm.sh/hook-delete-policy"]
        assert policy == "before-hook-creation,hook-succeeded", kind


def test_the_components_the_operator_provides_are_not_certified() -> None:
    objects = rendered(PROVIDED)
    (container,) = pod(hooked(objects, "Job"))["containers"]
    assert container["command"][3:] == [
        "deployments/waterfall-alertmanager",
        "deployments/waterfall-grafana",
    ]
    rules = hooked(objects, "Role")["rules"]
    assert rules[1]["resourceNames"] == ["waterfall-alertmanager-tls", "waterfall-grafana-tls"]
    assert [rule["resources"] for rule in rules[2:]] == [["deployments"]]
