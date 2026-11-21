# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration under Kubernetes: its Job, closed and deleted (US-2930, WF-EXP-0060).

The environment of the test holds a copy of the production not anonymised (WF-EXP-0010). The chart,
rendered by Helm (marker ``chart``), describes its Job: one pod whose services listen on its
loopback, which declares no port, which no Service selects and a NetworkPolicy closes, deleted with
its volumes once the test has ended; and the worker, which makes it, may create Jobs and nothing
else. That it holds on a cluster is the trial of the chart (``wftools.chartrestoretest``), whose
steps are held here against a ``kubectl`` that answers as a test tells it.
"""

import json
from typing import Any

import pytest
import yaml

from wftools import REPOSITORY, chart, chartrestoretest, restoretest_trial
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

Objects = list[dict[str, Any]]


def rendered(values: dict[str, Any] | None = None) -> Objects:
    return [item for item in yaml.safe_load_all(chart.render(values)) if item]


def named(objects: Objects, kind: str, name: str) -> dict[str, Any]:
    (found,) = [
        item for item in objects if item["kind"] == kind and item["metadata"]["name"] == name
    ]
    return found


def job_of(objects: Objects) -> dict[str, Any]:
    """Return the Job the worker makes, as the chart describes it to it."""
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
    assert tester["WATERFALL_RESTORE_TEST_API_ADDRESS"] == "http://127.0.0.1:8000"
    assert tester["WATERFALL_RESTORE_TEST_PATIENCE"] == "1800"


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
    # Out, only the names, the PostgreSQL and the storage of the production, which the test reads.
    (egress,) = policy["egress"]
    assert "to" not in egress
    assert {(port["protocol"], port["port"]) for port in egress["ports"]} == {
        ("UDP", 53),
        ("TCP", 53),
        ("TCP", 5432),
        ("TCP", 3900),
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
def test_the_worker_may_create_jobs_and_nothing_else_and_reads_the_job_the_chart_describes(
    objects: Objects,
) -> None:
    role = named(objects, "Role", "waterfall-restore-test")
    assert role["rules"] == [{"apiGroups": ["batch"], "resources": ["jobs"], "verbs": ["create"]}]
    binding = named(objects, "RoleBinding", "waterfall-restore-test")
    assert binding["roleRef"]["name"] == "waterfall-restore-test"
    assert [subject["name"] for subject in binding["subjects"]] == ["waterfall-worker"]
    worker = named(objects, "Deployment", "waterfall-worker")["spec"]["template"]["spec"]
    assert worker["serviceAccountName"] == "waterfall-worker"
    (main,) = worker["containers"]
    assert environment(main)["WATERFALL_RESTORE_TEST_JOB"] == "/restore-test/job.json"
    (mount,) = main["volumeMounts"]
    assert (mount["mountPath"], mount["readOnly"]) == ("/restore-test", True)
    scheduler = named(objects, "CronJob", "waterfall-scheduler")
    (schedule,) = scheduler["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"]
    assert environment(schedule)["WATERFALL_RESTORE_TEST_INTERVAL"] == "2592000"


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
    worker = named(objects, "Deployment", "waterfall-worker")["spec"]["template"]["spec"]
    assert "serviceAccountName" not in worker
    assert "WATERFALL_RESTORE_TEST_JOB" not in environment(worker["containers"][0])
    scheduler = named(objects, "CronJob", "waterfall-scheduler")
    (schedule,) = scheduler["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"]
    assert "WATERFALL_RESTORE_TEST_INTERVAL" not in environment(schedule)


@pytest.mark.chart
@pytest.mark.parametrize(
    ("address", "port"),
    [("https://s3.example.org", 443), ("http://s3.example.org", 80), ("http://s3:9000", 9000)],
)
def test_the_test_leaves_for_the_port_of_the_storage_an_operator_provides(
    address: str, port: int
) -> None:
    objects = rendered({"storage": {"enabled": False, "address": address}})
    (egress,) = named(objects, "NetworkPolicy", "waterfall-restore-test")["spec"]["egress"]
    assert {"protocol": "TCP", "port": port} in egress["ports"]


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


class Cluster:
    """A ``kubectl`` that answers as a test tells it, and keeps what it was asked."""

    def __init__(
        self,
        *,
        reached: str = "",
        left: list[str] | None = None,
        tested: str = "t",
        services: list[dict[str, Any]] | None = None,
    ) -> None:
        self.reached = reached
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
