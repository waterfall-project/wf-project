# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration under Kubernetes: its Job, closed and deleted (US-2930, WF-EXP-0060).

The environment of the test holds a copy of the production not anonymised (WF-EXP-0010). The chart,
rendered by Helm (marker ``chart``), describes its Job: one pod whose services listen on its
loopback, which declares no port, which no Service selects and a NetworkPolicy closes — nothing in,
out to named peers alone —, deleted with its volumes once the test has ended; and the scheduler,
which makes it, may create Jobs and nothing else, the worker nothing. That it holds on a cluster
is the trial of the chart (``wftools.chartrestoretest``), whose steps are held here against a
``kubectl`` that answers as a test tells it.
"""

import json
from typing import Any

import pytest
import yaml

from wftools import REPOSITORY, chart, chartrestoretest, restoretest_trial
from wftools.chart import ChartError
from wftools.chartrestoretest import RestoreTestTrial
from wftools.restoration_trial import Clock, TrialError

pytestmark = pytest.mark.story("US-2930")

COMPOSE = REPOSITORY / "deploy" / "compose"
TESTER = {
    "app.kubernetes.io/name": "waterfall",
    "app.kubernetes.io/instance": chart.RELEASE,
    "app.kubernetes.io/component": "restore-test",
}
SIDECARS = ("postgres", "keycloak", "api")
POSTGRES = {"app.kubernetes.io/component": "postgres"}
STORAGE = {"app.kubernetes.io/component": "storage"}

Objects = list[dict[str, Any]]


def rendered(values: dict[str, Any] | None = None) -> Objects:
    return [item for item in yaml.safe_load_all(chart.render(values)) if item]


def named(objects: Objects, kind: str, name: str) -> dict[str, Any]:
    (found,) = [
        item for item in objects if item["kind"] == kind and item["metadata"]["name"] == name
    ]
    return found


def job_of(objects: Objects) -> dict[str, Any]:
    """Return the Job the scheduler makes, as the chart describes it to it."""
    configmap = named(objects, "ConfigMap", "waterfall-restore-test")
    return json.loads(configmap["data"]["job.json"])


def container(spec: dict[str, Any], name: str) -> dict[str, Any]:
    (found,) = [
        each for each in [*spec["initContainers"], *spec["containers"]] if each["name"] == name
    ]
    return found


def environment(each: dict[str, Any]) -> dict[str, Any]:
    return {variable["name"]: variable.get("value") for variable in each.get("env", [])}


@pytest.fixture(scope="module")
def objects() -> Objects:
    return rendered()


@pytest.mark.chart
@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_test_is_one_pod_whose_services_listen_on_its_loopback_and_declare_no_port(
    objects: Objects,
) -> None:
    # « L'environnement du test n'est joignable par aucun utilisateur » : the PostgreSQL, the
    # Keycloak and the API of the test are sidecars of the pod of the test, on its loopback.
    spec = job_of(objects)["spec"]["template"]["spec"]
    assert [each["name"] for each in spec["containers"]] == ["restore-test"]
    for name in SIDECARS:
        assert container(spec, name)["restartPolicy"] == "Always", name
    every = [*spec["initContainers"], *spec["containers"]]
    assert not [each["name"] for each in every if each.get("ports")]
    assert spec["automountServiceAccountToken"] is False
    assert spec["enableServiceLinks"] is False
    assert not spec.get("hostNetwork")
    assert "listen_addresses=127.0.0.1" in container(spec, "postgres")["command"][-1]
    assert environment(container(spec, "keycloak"))["KC_HTTP_HOST"] == "127.0.0.1"
    # The API listens on the address of WATERFALL_HOST, the loopback when it is not given.
    assert "WATERFALL_HOST" not in environment(container(spec, "api"))
    tester = environment(container(spec, "restore-test"))
    # In TLS, under the authority of the test (US-2840).
    assert tester["WATERFALL_RESTORE_TEST_API_ADDRESS"] == "https://127.0.0.1:8000"
    assert tester["WATERFALL_RESTORE_TEST_PATIENCE"] == "1800"


@pytest.mark.chart
@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.story("US-2840")
def test_the_key_of_the_authority_of_the_test_stays_in_the_container_that_makes_it(
    objects: Objects,
) -> None:
    # The clients mount the root alone, each server its own certificate: none reads kept/, the key.
    spec = job_of(objects)["spec"]["template"]["spec"]
    whole: list[str] = []
    parts: dict[str, list[str]] = {}
    for each in [*spec["initContainers"], *spec["containers"]]:
        for mount in each.get("volumeMounts", []):
            if mount["name"] != "test-authority":
                continue
            if "subPath" in mount:
                parts.setdefault(each["name"], []).append(mount["subPath"])
            else:
                whole.append(each["name"])
    assert whole == ["restore-test-authority"]
    assert parts == {
        "postgres": ["certificates/restore-test-postgres"],
        "keycloak": ["trust", "certificates/restore-test-keycloak"],
        "api": ["trust", "certificates/restore-test-api"],
        "restore-test": ["trust"],
    }


@pytest.mark.chart
@pytest.mark.requirement("WF-EXP-0060-A")
def test_no_service_selects_the_pod_of_the_test_and_a_network_policy_lets_nothing_in(
    objects: Objects,
) -> None:
    labels = job_of(objects)["spec"]["template"]["metadata"]["labels"]
    assert labels == TESTER
    services = [item for item in objects if item["kind"] == "Service"]
    assert services
    assert not [
        item["metadata"]["name"]
        for item in services
        if chartrestoretest.selected(item["spec"].get("selector") or {}, labels)
    ]
    policy = named(objects, "NetworkPolicy", "waterfall-restore-test")["spec"]
    assert policy["podSelector"]["matchLabels"] == TESTER
    assert policy["policyTypes"] == ["Ingress", "Egress"]
    assert policy["ingress"] == []
    # Out, each rule names where it leads: the DNS of the cluster, the PostgreSQL and the storage
    # of the production, by their pods; no rule without its `to`, which would lead anywhere.
    egress = policy["egress"]
    assert all(rule.get("to") for rule in egress)
    led = {
        tuple((port["protocol"], port["port"]) for port in rule["ports"]): rule["to"]
        for rule in egress
    }
    assert led == {
        (("UDP", 53), ("TCP", 53)): [
            {
                "namespaceSelector": {
                    "matchLabels": {"kubernetes.io/metadata.name": "kube-system"}
                },
                "podSelector": {"matchLabels": {"k8s-app": "kube-dns"}},
            }
        ],
        (("TCP", 5432),): [{"podSelector": {"matchLabels": {**TESTER, **POSTGRES}}}],
        (("TCP", 3900),): [{"podSelector": {"matchLabels": {**TESTER, **STORAGE}}}],
    }


@pytest.mark.chart
@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_job_its_pod_and_its_volumes_are_deleted_once_the_test_has_ended(
    objects: Objects,
) -> None:
    # « … et n'existe plus après le test. » : deleted at once, never tried again, bounded; its
    # databases and its password on volumes of the pod alone.
    job = job_of(objects)["spec"]
    assert job["ttlSecondsAfterFinished"] == 0
    assert job["backoffLimit"] == 0
    assert job["activeDeadlineSeconds"] == 21600
    spec = job["template"]["spec"]
    assert spec["restartPolicy"] == "Never"
    volumes = {volume["name"]: volume for volume in spec["volumes"]}
    assert volumes["shared"]["emptyDir"]["medium"] == "Memory"
    assert set(volumes["databases"]) == {"name", "emptyDir"}
    assert set(volumes["files"]) == {"name", "configMap"}


@pytest.mark.chart
@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_scheduler_alone_may_create_jobs_and_the_worker_holds_no_right_of_the_cluster(
    objects: Objects,
) -> None:
    # The scheduler runs a fixed command and reads no file of a user; the worker reads the imports:
    # the token that may create a Job — any pod, any Secret of the namespace — is the scheduler's.
    role = named(objects, "Role", "waterfall-restore-test")
    assert role["rules"] == [{"apiGroups": ["batch"], "resources": ["jobs"], "verbs": ["create"]}]
    binding = named(objects, "RoleBinding", "waterfall-restore-test")
    assert binding["roleRef"]["name"] == "waterfall-restore-test"
    assert [subject["name"] for subject in binding["subjects"]] == ["waterfall-scheduler"]
    accounts = [item["metadata"]["name"] for item in objects if item["kind"] == "ServiceAccount"]
    assert accounts == ["waterfall-scheduler"]
    assert len([item for item in objects if item["kind"] == "RoleBinding"]) == 1
    scheduler = named(objects, "CronJob", "waterfall-scheduler")
    spec = scheduler["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == "waterfall-scheduler"
    (schedule,) = spec["containers"]
    assert schedule["command"] == ["waterfall-worker", "schedule"]
    assert environment(schedule)["WATERFALL_RESTORE_TEST_JOB"] == "/restore-test/job.json"
    assert environment(schedule)["WATERFALL_RESTORE_TEST_INTERVAL"] == "2592000"
    (mount,) = [mount for mount in schedule["volumeMounts"] if mount["name"] == "restore-test"]
    assert (mount["mountPath"], mount["readOnly"]) == ("/restore-test", True)
    worker = named(objects, "Deployment", "waterfall-worker")["spec"]["template"]["spec"]
    assert "serviceAccountName" not in worker
    assert "WATERFALL_RESTORE_TEST_JOB" not in environment(worker["containers"][0])


@pytest.mark.chart
def test_the_databases_of_the_test_are_made_as_under_compose(objects: Objects) -> None:
    configmap = named(objects, "ConfigMap", "waterfall-restore-test")
    said = (COMPOSE / "restore-test-database.sql").read_text(encoding="utf-8").rstrip("\n")
    assert configmap["data"]["restore-test-database.sql"] == said


@pytest.mark.chart
def test_without_the_test_the_chart_makes_none_of_it() -> None:
    objects = rendered({"restoreTest": {"enabled": False}})
    assert not [
        item["metadata"]["name"] for item in objects if "restore-test" in item["metadata"]["name"]
    ]
    assert not [item for item in objects if item["kind"] in {"ServiceAccount", "RoleBinding"}]
    scheduler = named(objects, "CronJob", "waterfall-scheduler")
    spec = scheduler["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    assert "serviceAccountName" not in spec
    (schedule,) = spec["containers"]
    assert "WATERFALL_RESTORE_TEST_JOB" not in environment(schedule)
    assert "WATERFALL_RESTORE_TEST_INTERVAL" not in environment(schedule)


PROVIDED_STORAGE = [{"ipBlock": {"cidr": "10.0.0.6/32"}}]
PROVIDED_POSTGRES = [{"ipBlock": {"cidr": "10.0.0.5/32"}}]
# The roots of the certificates of the components of the operator (US-2840).
TRUSTED = {"providedAuthority": "operator-roots"}


@pytest.mark.chart
@pytest.mark.requirement("WF-EXP-0060-A")
@pytest.mark.parametrize(
    ("address", "port"),
    [("https://s3.example.org", 443), ("http://s3.example.org", 80), ("http://s3:9000", 9000)],
)
def test_the_test_leaves_for_the_storage_an_operator_provides_at_its_peers_and_its_port(
    address: str, port: int
) -> None:
    objects = rendered(
        {
            "storage": {"enabled": False, "address": address},
            "postgresql": {"enabled": False, "host": "db.example.org", "port": 6432},
            "secrets": {"existingSecret": "operator", "values": None},
            "transport": TRUSTED,
            "restoreTest": {
                "egress": {"storage": PROVIDED_STORAGE, "postgresql": PROVIDED_POSTGRES}
            },
        }
    )
    egress = named(objects, "NetworkPolicy", "waterfall-restore-test")["spec"]["egress"]
    assert all(rule.get("to") for rule in egress)
    led = {rule["ports"][0]["port"]: rule["to"] for rule in egress}
    assert led[port] == PROVIDED_STORAGE
    assert led[6432] == PROVIDED_POSTGRES


@pytest.mark.chart
@pytest.mark.requirement("WF-EXP-0060-A")
@pytest.mark.parametrize(
    ("given", "said"),
    [
        (
            {
                "storage": {"enabled": False, "address": "https://s3.example.org"},
                "transport": TRUSTED,
            },
            r"restoreTest\.egress\.storage",
        ),
        (
            {
                "postgresql": {"enabled": False, "host": "db.example.org"},
                "secrets": {"existingSecret": "operator", "values": None},
                "transport": TRUSTED,
            },
            r"restoreTest\.egress\.postgresql",
        ),
    ],
    ids=["storage", "postgresql"],
)
def test_a_component_provided_without_its_peers_stops_the_rendering_rather_than_let_the_copy_out(
    given: dict[str, Any], said: str
) -> None:
    with pytest.raises(ChartError, match=said):
        rendered(given)


POD = {
    "metadata": {"name": "waterfall-restore-test-0193a0b2-x", "labels": TESTER},
    "spec": {
        "automountServiceAccountToken": False,
        "initContainers": [{"name": "postgres"}],
        "containers": [{"name": "restore-test"}],
    },
    "status": {"phase": "Running", "podIP": "10.244.0.42"},
}
SINCE = "2026-11-21 19:00:00+00"
DECOY_ADDRESS = "10.244.0.77"


class Cluster:
    """A ``kubectl`` that answers as a test tells it, and keeps what it was asked."""

    def __init__(
        self,
        *,
        reached: str = "",
        left: list[str] | None = None,
        tested: str = "t",
        services: list[dict[str, Any]] | None = None,
        confined: tuple[str, str] = ("5432", ""),
    ) -> None:
        self.reached = reached
        # What the pod of the test reaches on 5432: the PostgreSQL of the production, the decoy.
        self.production, self.escaped = confined
        self.left = left or [""]
        self.tested = tested
        self.services = services or []
        self.ran: list[str] = []

    def read(self, command: list[str]) -> tuple[int, str]:
        said = " ".join(command)
        self.ran.append(said)
        answers: dict[str, str] = {
            restoretest_trial.NOW: SINCE,
            restoretest_trial.VERIFIED: "1",
            restoretest_trial.OPEN: "0",
            "get pods --selector": json.dumps({"items": [POD]}),
            "get services": json.dumps({"items": self.services}),
            "trial-restore-test-probe": f"reached:{self.reached}\n",
            "restore_test WHERE": self.tested,
        }
        if "get jobs,pods" in said:
            return 0, self.left.pop(0) if len(self.left) > 1 else self.left[0]
        if f"get pod {chartrestoretest.DECOY}" in said:
            return 0, DECOY_ADDRESS
        if said.endswith(f"{DECOY_ADDRESS} 5432"):
            return 0, f"reached:{self.escaped}\n"
        if said.endswith("waterfall-postgres 5432"):
            return 0, f"reached:{self.production}\n"
        for marker, answer in answers.items():
            if marker in said:
                return 0, answer
        return 0, ""


def trial_on(cluster: Cluster) -> RestoreTestTrial:
    clock = Clock(now=iter(range(100_000)).__next__, pause=lambda _seconds: None)
    return RestoreTestTrial(["kubectl", "-n", "waterfall"], cluster.read, "image:tag", clock)


@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_trial_plans_the_test_finds_it_closed_then_gone_and_inscribed() -> None:
    cluster = Cluster(left=["job.batch/waterfall-restore-test-0193a0b2", ""])
    trial_on(cluster).hold()
    created = [said for said in cluster.ran if "create job" in said]
    scheduler = "--from=cronjob/waterfall-scheduler"
    assert created == [
        f"kubectl -n waterfall create job trial-schedule-backup {scheduler}",
        f"kubectl -n waterfall create job trial-schedule-restore-test {scheduler}",
    ]
    (probe,) = [said for said in cluster.ran if "trial-restore-test-probe" in said]
    assert probe.endswith("10.244.0.42 5432 8000 8080 9000")
    assert "--image=image:tag" in probe
    assert sum("get jobs,pods" in said for said in cluster.ran) == 2
    assert any(f"finished_at >= '{SINCE}'" in said for said in cluster.ran)
    # The decoy started before the test, probed from the pod of the test, then deleted.
    decoy = chartrestoretest.DECOY
    started = next(i for i, said in enumerate(cluster.ran) if f"run {decoy}" in said)
    scheduled = next(i for i, said in enumerate(cluster.ran) if "schedule-restore-test" in said)
    assert started < scheduled
    pod = "exec waterfall-restore-test-0193a0b2-x -c api"
    probes = [said for said in cluster.ran if pod in said and said.endswith(" 5432")]
    assert [said.split()[-2] for said in probes] == ["waterfall-postgres", DECOY_ADDRESS]
    assert f"kubectl -n waterfall delete pod {decoy} --wait=false --ignore-not-found" in cluster.ran


@pytest.mark.requirement("WF-EXP-0060-A")
def test_a_pod_of_the_test_that_reaches_a_pod_the_policy_does_not_name_fails_the_trial() -> None:
    cluster = Cluster(confined=("5432", "5432"))
    with pytest.raises(TrialError, match="does not name"):
        trial_on(cluster).hold()
    decoy = chartrestoretest.DECOY
    assert f"kubectl -n waterfall delete pod {decoy} --wait=false --ignore-not-found" in cluster.ran


def test_a_probe_that_reaches_not_even_the_production_fails_the_trial() -> None:
    # Else a probe that reaches nothing would say the test confined.
    with pytest.raises(TrialError, match="does not reach the PostgreSQL"):
        trial_on(Cluster(confined=("", ""))).hold()


def test_a_port_of_the_test_reached_from_the_namespace_fails_the_trial() -> None:
    with pytest.raises(TrialError, match="reaches the ports 8000 of the test"):
        trial_on(Cluster(reached="8000")).hold()


def test_a_service_that_selects_the_pod_of_the_test_fails_the_trial() -> None:
    service = {"metadata": {"name": "exposed"}, "spec": {"selector": TESTER}}
    with pytest.raises(TrialError, match="Services exposed select the pod"):
        trial_on(Cluster(services=[service])).hold()


def test_a_test_that_did_not_succeed_fails_the_trial() -> None:
    with pytest.raises(TrialError, match="no test of a restoration that succeeded"):
        trial_on(Cluster(tested="f")).hold()


def test_a_job_that_outlives_the_test_fails_the_trial() -> None:
    with pytest.raises(TrialError, match="remains after the test"):
        trial_on(Cluster(left=["pod/waterfall-restore-test-0193a0b2-x"])).hold()


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"automountServiceAccountToken": True}, "mounts a token"),
        ({"hostNetwork": True}, "network"),
        ({"containers": [{"name": "restore-test", "ports": [{"containerPort": 8000}]}]}, "ports"),
    ],
)
def test_a_pod_of_the_test_that_opens_itself_fails_the_trial(
    change: dict[str, Any], said: str
) -> None:
    pod = {**POD, "spec": {**POD["spec"], **change}}
    with pytest.raises(TrialError, match=said):
        chartrestoretest.check_closed(pod, [])


def test_an_empty_selector_selects_no_pod_and_the_probe_says_what_it_reached() -> None:
    assert chartrestoretest.selected({}, TESTER) is False
    assert chartrestoretest.selected({"app.kubernetes.io/component": "api"}, TESTER) is False
    assert chartrestoretest.reached("noise\nreached:5432,8000\n") == ["5432", "8000"]
    with pytest.raises(TrialError, match="said nothing"):
        chartrestoretest.reached("pod deleted")
