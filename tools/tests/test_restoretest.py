# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration under Compose: its isolation and its removal (US-2930, WF-EXP-0060).

The ephemeral platform holds a copy of the production not anonymised (WF-EXP-0010). Two things keep
it from outliving or leaving its place, and both are held here: the Compose file, resolved as
Compose reads it, exposes nothing; and ``restore-test.sh`` removes the platform with its volumes
before it starts, and whatever ends it, an interruption included. The script runs against a
``docker`` that writes down what it is asked.
"""

import contextlib
import json
import os
import shutil
import signal
import stat
import subprocess
import time
from typing import TYPE_CHECKING, Any

import pytest

from wftools import REPOSITORY, production, restoretest_trial
from wftools.restoration_trial import PATIENCE, Clock, TrialError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.story("US-2930")

COMPOSE = REPOSITORY / "deploy" / "compose"
FILE = COMPOSE / "compose.restore-test.yaml"
SCRIPT = COMPOSE / "restore-test.sh"
PROJECT = "waterfall-restore-test"
# The variables the Compose file requires, as ``make lint-compose`` stands them in.
STAND_IN = {
    "WATERFALL_DOMAIN": "waterfall.localhost",
    "WATERFALL_DIGEST_WATERFALL": "sha256:" + "0" * 64,
    "WATERFALL_DIGEST_KEYCLOAK": "sha256:" + "0" * 64,
    "WATERFALL_SERVICE_DATABASE_PASSWORD": "stand-in",
    "WATERFALL_STORAGE_SECRET": "stand-in",
    "WATERFALL_RESTORE_TEST_PASSWORD": "stand-in",
}
TESTER = "restore-test"
PRODUCTION_TRUST = "production-trust"
NO_DOCKER = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
UNEXECUTED = pytest.mark.unexecuted("skipped where docker is not installed")


def resolved() -> dict[str, Any]:
    """Read the Compose file of the test as Compose resolves it."""
    command = ["docker", "compose", "-f", str(FILE), "--profile", "restore-test"]
    done = subprocess.run(
        [*command, "config", "--format", "json"],
        env={**os.environ, **STAND_IN},
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)


@NO_DOCKER
@UNEXECUTED
def test_the_ephemeral_platform_exposes_nothing_and_shares_nothing_with_the_production() -> None:
    config = resolved()
    services = config["services"]
    assert config["name"] == PROJECT
    assert set(services) >= {TESTER, "restore-test-postgres", "restore-test-api"}
    for name, service in services.items():
        assert not service.get("ports"), f"{name} publishes a port"
        assert service.get("network_mode") != "host", f"{name} is on the network of the host"
    assert config["networks"]["ephemeral"]["internal"] is True
    external = [name for name, net in config["networks"].items() if net.get("external")]
    assert external == ["production"]
    joined = {
        name for name, service in services.items() if "production" in service.get("networks", {})
    }
    assert joined == {TESTER}
    for name, service in services.items():
        if name != TESTER:
            on_ephemeral = "ephemeral" in service.get("networks", {})
            assert on_ephemeral or service.get("network_mode") == "none", name


@NO_DOCKER
@UNEXECUTED
def test_the_volumes_of_the_ephemeral_platform_are_its_own_but_the_trust_of_the_production() -> (
    None
):
    config = resolved()
    volumes = config["volumes"]
    external = {key for key, volume in volumes.items() if volume.get("external")}
    assert external == {PRODUCTION_TRUST}
    for key, volume in volumes.items():
        if key not in external:
            assert volume["name"].startswith(f"{PROJECT}_"), key
    for name, service in config["services"].items():
        for mount in service.get("volumes", []):
            assert mount["type"] in {"volume", "bind"}
            if mount["type"] == "volume" and mount["source"] in external:
                assert mount.get("read_only") is True, f"{name} writes the trust of the production"
            if mount["type"] == "bind":
                assert mount.get("read_only") is True, f"{name} writes the files of the host"


def fake_docker(folder: Path, *, hold: bool) -> Path:
    """Put a ``docker`` that logs what it is asked in ``folder``; its ``wait`` holds if asked."""
    log = folder / "calls"
    docker = folder / "docker"
    holding = 'case "$*" in *" wait "*) exec sleep 20;; esac\n' if hold else ""
    docker.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n{holding}exit 0\n', encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    return log


def asked(log: Path) -> list[str]:
    """Read what Compose was asked, after its options: ``down --volumes …``, ``up …``."""
    if not log.exists():
        return []
    marker = "--profile restore-test "
    return [line.split(marker, 1)[1] for line in log.read_text().splitlines()]


def environment(folder: Path) -> dict[str, str]:
    """Put the fake ``docker`` at the head of the path."""
    return {**os.environ, "PATH": f"{folder}:{os.environ['PATH']}"}


def test_the_script_removes_what_a_test_interrupted_left_before_it_starts(tmp_path: Path) -> None:
    log = fake_docker(tmp_path, hold=False)
    done = subprocess.run(
        ["sh", str(SCRIPT)],
        env=environment(tmp_path),
        capture_output=True,
        check=False,
        timeout=60,
    )
    calls = asked(log)
    verbs = [call.split()[0] for call in calls]
    assert done.returncode == 0
    assert verbs[0] == "down"
    assert verbs.index("down") < verbs.index("up")
    assert verbs[-1] == "down"
    assert all("--volumes" in call for call in calls if call.startswith("down"))


def test_an_interrupted_script_removes_the_platform_with_its_volumes(tmp_path: Path) -> None:
    log = fake_docker(tmp_path, hold=True)
    script = subprocess.Popen(
        ["sh", str(SCRIPT)],
        env=environment(tmp_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not any(c.startswith("wait") for c in asked(log)):
            time.sleep(0.05)
        before = len(asked(log))
        os.kill(script.pid, signal.SIGTERM)
        assert script.wait(timeout=15) == 128 + signal.SIGTERM
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(script.pid, signal.SIGKILL)
    after = asked(log)[before:]
    assert after
    assert after[-1].startswith("down --volumes")
    assert "--remove-orphans" in after[-1]


# The instant the database says before the backup is deposited.
SINCE = "2026-11-21 01:02:03.456+00"


def ending(code: int) -> restoretest_trial.Run:
    """Run nothing, and say the status ``code``, as the script of the test would end."""

    def run(_command: list[str], _limit: float | None = None) -> int:
        return code

    return run


class Compose:
    """A Compose, a database and a Docker that answer as a test tells them."""

    def __init__(
        self,
        *,
        verified: str = "1",
        tested: str = "t",
        left: str | None = None,
        open_tasks: list[str] | None = None,
    ) -> None:
        self.verified = verified
        self.open_tasks = open_tasks or ["0"]
        self.tested = tested
        self.left = left
        self.ran: list[str] = []

    def read(self, command: list[str]) -> tuple[int, str]:
        said = " ".join(command)
        self.ran.append(said)
        if restoretest_trial.NOW in said:
            return 0, f"{SINCE}\n"
        if restoretest_trial.verified_since(SINCE) in said:
            return 0, self.verified + "\n"
        if restoretest_trial.OPEN in said:
            left = self.open_tasks.pop(0) if len(self.open_tasks) > 1 else self.open_tasks[0]
            return 0, left + "\n"
        if restoretest_trial.TESTED in said:
            return 0, self.tested + "\n"
        if self.left is not None and command[:2] == ["docker", self.left]:
            return 0, "abc123\n"
        return 0, ""


def test_a_backup_is_scheduled_by_making_it_due_and_running_the_schedule() -> None:
    compose = Compose()
    restoretest_trial.scheduled_backup(["compose"], compose.read)
    assert restoretest_trial.NOW in compose.ran[0]
    assert restoretest_trial.DUE in compose.ran[1]
    assert compose.ran[2] == "compose exec -T scheduler waterfall-worker schedule"


def test_only_a_backup_taken_since_the_trial_asked_counts_as_the_one_the_schedule_deposited() -> (
    None
):
    # #4650: a scheduled backup verified before the deposit is not the one the trial waits for.
    compose = Compose()
    restoretest_trial.scheduled_backup(["compose"], compose.read)
    counted = [said for said in compose.ran if restoretest_trial.VERIFIED in said]
    assert counted
    assert all(f"AND taken_at >= '{SINCE}'" in said for said in counted)


def test_a_schedule_that_deposits_no_verified_backup_fails_the_trial() -> None:
    clock = Clock(now=iter([0.0, 1.0, PATIENCE + 2]).__next__, pause=lambda _seconds: None)
    with pytest.raises(TrialError, match="no backup scheduled was listed verified"):
        restoretest_trial.scheduled_backup(["compose"], Compose(verified="0").read, clock)


def test_a_script_that_fails_fails_the_trial() -> None:
    with pytest.raises(TrialError, match=r"restore-test.sh failed \(1\)"):
        restoretest_trial.restore_test(["compose"], ending(1), Compose().read, "p")


def test_a_test_not_inscribed_as_succeeded_on_a_scheduled_backup_fails_the_trial() -> None:
    compose = Compose(tested="")
    with pytest.raises(TrialError, match="holds no test of a restoration that succeeded"):
        restoretest_trial.restore_test(["compose"], ending(0), compose.read, "p")


@pytest.mark.parametrize(
    ("verb", "kind"), [("ps", "container"), ("network", "network"), ("volume", "volume")]
)
def test_what_the_ephemeral_project_leaves_fails_the_trial(verb: str, kind: str) -> None:
    compose = Compose(left=verb)
    with pytest.raises(TrialError, match=f"leaves {kind} abc123"):
        restoretest_trial.restore_test(["compose"], ending(0), compose.read, "p")


def test_a_test_that_succeeded_and_left_nothing_passes() -> None:
    restoretest_trial.restore_test(["compose"], ending(0), Compose().read, "p")


def test_a_backup_listed_verified_whose_task_is_open_is_waited_for_until_it_ends() -> None:
    # The line is verified before the task ends: the manual backup would meet the lock held.
    compose = Compose(open_tasks=["1", "1", "0"])
    pauses: list[float] = []
    clock = Clock(now=iter(range(100)).__next__, pause=pauses.append)
    restoretest_trial.scheduled_backup(["compose"], compose.read, clock)
    assert len(pauses) == 2
    assert sum(restoretest_trial.OPEN in said for said in compose.ran) == 3


def test_a_backup_whose_task_never_ends_fails_the_trial() -> None:
    clock = Clock(now=iter([0.0, 1.0, 2.0, PATIENCE + 2]).__next__, pause=lambda _seconds: None)
    with pytest.raises(TrialError, match="its task ended"):
        restoretest_trial.scheduled_backup(["compose"], Compose(open_tasks=["1"]).read, clock)


def test_a_script_that_exceeds_its_bound_fails_the_trial_saying_so() -> None:
    def hangs(command: list[str], limit: float | None = None) -> int:
        raise subprocess.TimeoutExpired(command, limit or 0)

    with pytest.raises(TrialError, match=r"did not end in 5 s; it was asked to stop"):
        restoretest_trial.restore_test(["compose"], hangs, Compose().read, "p", 5.0)


def test_the_bound_asks_the_script_itself_to_stop_so_that_its_trap_removes_the_platform(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "trapped"
    script = f"trap 'echo term > {marker}; exit 143' TERM; while :; do sleep 0.1; done"
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        production.runner({"PATH": os.environ["PATH"]})(["env", "X=1", "sh", "-c", script], 1.0)
    assert marker.read_text() == "term\n"
    assert time.monotonic() - started < 30
