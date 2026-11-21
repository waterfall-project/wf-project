# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration on the cluster of the trial of the chart (US-2930, WF-EXP-0060).

The chart installed on its own data components (``wftools.charttrial``), the trial plays the test as
the platform plans it under Kubernetes, and holds that its environment is reachable by no one and
does not outlive it:

- the schedule deposits a backup *scheduled*, which the test alone restores — the schedule made due
  as under Compose (``wftools.restoretest_trial``), the CronJob of the scheduler run once by a Job
  of its own —, and the trial waits for it listed verified;
- the scheduler run again deposits the test, and the worker makes its Job: its pod is found, its API
  listening on its loopback, and then held closed — it declares no port and mounts no token of the
  cluster, no Service selects it, and a pod of the namespace reaches none of its ports;
- the test ends, and neither its Job nor its pod remains; the production holds a test that
  succeeded, inscribed since the trial began.
"""

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from wftools import chart, restoretest_trial
from wftools.restoration_trial import PATIENCE, PAUSE, Clock, TrialError

TESTER = "app.kubernetes.io/component=restore-test"
"""The label of the pod of the test, which its Job and the NetworkPolicy name."""
PORTS = (5432, 8000, 8080, 9000)
"""The ports of the PostgreSQL, the API and Keycloak of the test, which no one may reach."""
PROBE = (
    "import socket, sys\n"
    "reached = []\n"
    "for port in sys.argv[2:]:\n"
    "    try:\n"
    "        socket.create_connection((sys.argv[1], int(port)), timeout=3).close()\n"
    "        reached.append(port)\n"
    "    except OSError:\n"
    "        pass\n"
    "print('reached:' + ','.join(reached))\n"
)
"""What a pod of the namespace runs against the pod of the test: the ports it reaches."""
LISTENING = "import socket; socket.create_connection(('127.0.0.1', 8000), timeout=3).close()"
"""What the container of the API of the test runs: whether it listens, on its loopback."""
TESTED = (
    "SELECT succeeded FROM restore_test WHERE finished_at >= '{since}' "
    "ORDER BY finished_at DESC LIMIT 1"
)
"""Whether the latest test inscribed since an instant succeeded: ``t``."""
TEST_PATIENCE = 2400.0
"""How long, in seconds, the test may take on the cluster: a restoration, Keycloak and the API."""

Read = Callable[[list[str]], tuple[int, str]]


def _output(read: Read, command: list[str], what: str) -> str:
    code, output = read(command)
    if code != 0:
        message = f"{what} failed ({code})"
        raise TrialError(message)
    return output.strip()


def selected(selector: Mapping[str, str], labels: Mapping[str, str]) -> bool:
    """Tell whether a selector of a Service selects a pod of these labels; an empty one, none."""
    return bool(selector) and all(labels.get(key) == value for key, value in selector.items())


def check_closed(pod: Mapping[str, Any], services: list[Mapping[str, Any]]) -> None:
    """Hold that the pod of the test declares no port, mounts no token, no Service selects it."""
    spec = cast("dict[str, Any]", pod["spec"])
    every = [*spec.get("initContainers", []), *spec["containers"]]
    declared = [each["name"] for each in every if each.get("ports")]
    if declared:
        message = f"the containers {', '.join(declared)} of the test declare ports"
        raise TrialError(message)
    if spec.get("automountServiceAccountToken") is not False or spec.get("hostNetwork"):
        message = "the pod of the test mounts a token of the cluster, or is on the node's network"
        raise TrialError(message)
    labels = cast("dict[str, str]", pod["metadata"].get("labels", {}))
    selecting = [
        each["metadata"]["name"]
        for each in services
        if selected(each.get("spec", {}).get("selector") or {}, labels)
    ]
    if selecting:
        message = f"the Services {', '.join(selecting)} select the pod of the test"
        raise TrialError(message)


def reached(said: str) -> list[str]:
    """Read the ports the probe reached, from what it printed."""
    for line in said.splitlines():
        if line.startswith("reached:"):
            return [port for port in line.removeprefix("reached:").split(",") if port]
    message = f"the probe said nothing of the ports it reached: {said!r}"
    raise TrialError(message)


@dataclass(frozen=True, slots=True)
class RestoreTestTrial:
    """The test of a restoration on the chart installed: ``kubectl`` on its namespace.

    ``image`` is the image the probe runs, one the cluster holds.
    """

    kubectl: list[str]
    read: Read
    image: str
    clock: Clock = field(default_factory=Clock)

    def sql(self, statement: str) -> list[str]:
        """Return the command that runs a statement on the database of Waterfall, as postgres."""
        return [
            *self.kubectl,
            "exec",
            f"statefulset/{chart.RELEASE}-postgres",
            "--",
            "psql",
            "--username=postgres",
            "--dbname=waterfall",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            f"--command={statement}",
        ]

    def schedule(self, name: str) -> list[list[str]]:
        """Return the commands that run the CronJob of the scheduler once, and wait for its end."""
        return [
            [*self.kubectl, "create", "job", name, f"--from=cronjob/{chart.RELEASE}-scheduler"],
            [*self.kubectl, "wait", "--for=condition=complete", f"job/{name}", "--timeout=5m"],
        ]

    def hold(self) -> None:
        """Have the platform plan the test and hold its environment closed, then gone."""
        since = _output(self.read, self.sql(restoretest_trial.NOW), "reading the instant")
        restoretest_trial.deposited_backup(
            self.sql, self.schedule("trial-schedule-backup"), self.read, self.clock
        )
        for command in self.schedule("trial-schedule-restore-test"):
            _output(self.read, command, "the schedule of the test")
        pod = self.running()
        services = _output(
            self.read, [*self.kubectl, "get", "services", "--output", "json"], "list the Services"
        )
        check_closed(pod, json.loads(services)["items"])
        print("  the pod of the test declares no port, mounts no token, no Service selects it")
        self.unreachable(pod)
        self.gone()
        tested = _output(
            self.read, self.sql(TESTED.format(since=since)), "read the tests of a restoration"
        )
        if tested != "t":
            message = "the production holds no test of a restoration that succeeded since the trial"
            raise TrialError(message)
        print("  the production inscribed the test, which succeeded")

    def pods(self) -> list[dict[str, Any]]:
        """Return the pods of the test there are."""
        listing = _output(
            self.read,
            [*self.kubectl, "get", "pods", "--selector", TESTER, "--output", "json"],
            "list the pods of the test",
        )
        return cast("list[dict[str, Any]]", json.loads(listing)["items"])

    def running(self) -> dict[str, Any]:
        """Wait for the pod of the test to run its API, listening; return the pod."""
        deadline = self.clock.now() + TEST_PATIENCE
        while self.clock.now() < deadline:
            for pod in self.pods():
                name = pod["metadata"]["name"]
                probe = [*self.kubectl, "exec", name, "-c", "api", "--", "python3", "-c", LISTENING]
                if pod.get("status", {}).get("phase") == "Running" and self.read(probe)[0] == 0:
                    print(f"  the worker made the Job of the test; {name} runs its API")
                    return pod
            self.clock.pause(PAUSE)
        message = f"no pod of the test ran its API in {TEST_PATIENCE:.0f} s"
        raise TrialError(message)

    def unreachable(self, pod: Mapping[str, Any]) -> None:
        """Hold that a pod of the namespace reaches none of the ports of the test, its API up."""
        address = cast("str", pod["status"]["podIP"])
        probe = [
            *self.kubectl,
            "run",
            "trial-restore-test-probe",
            f"--image={self.image}",
            "--restart=Never",
            "--rm",
            "--attach",
            "--quiet",
            "--command",
            "--",
            "python3",
            "-c",
            PROBE,
            address,
            *(str(port) for port in PORTS),
        ]
        if found := reached(_output(self.read, probe, "probe the pod of the test")):
            message = f"a pod of the namespace reaches the ports {', '.join(found)} of the test"
            raise TrialError(message)
        print(f"  a pod of the namespace reaches none of the ports {PORTS} of the test")

    def gone(self) -> None:
        """Wait for the Job of the test and its pod to be deleted once the test has ended."""
        deadline = self.clock.now() + TEST_PATIENCE + PATIENCE
        while self.clock.now() < deadline:
            left = _output(
                self.read,
                [*self.kubectl, "get", "jobs,pods", "--selector", TESTER, "--output", "name"],
                "list the Job and the pod of the test",
            )
            if not left:
                print("  neither the Job of the test nor its pod remains")
                return
            self.clock.pause(PAUSE)
        message = "the Job of the test or its pod remains after the test"
        raise TrialError(message)
