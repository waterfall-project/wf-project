# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slot of a worktree: its ports, its projects of Compose and the tags of its images (US-1100).

The tool is run as the Makefile runs it, ``python3 slots.py claim``, in repositories of git made
for the test — a main repository and worktrees of it —, with ``XDG_RUNTIME_DIR`` on a temporary
directory: no test touches the register of the workstation. Docker, pnpm and uv are stand-ins on
the ``PATH`` that write what they are asked and the variables they are given: the Makefile is
tried by what it hands its commands, nothing is started.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from wftools import REPOSITORY, slots

SLOTS = REPOSITORY / "tools" / "src" / "wftools" / "slots.py"
MAKEFILE = REPOSITORY / "Makefile"
# Writes its name, its arguments and the variables of the slots it is given, to its log; fails
# with the code in FAIL_CODE, if any.
STAND_IN = """#!/bin/sh
{ echo "$(basename "$0") $*"; env | grep -E '^(WATERFALL|E2E)_' | sort; } >> "$STAND_IN_LOG"
exit "${FAIL_CODE:-0}"
"""
OUTER = ("MAKEFLAGS", "MAKELEVEL", "MFLAGS", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "TESTS")


class Workstation:
    """A main repository, its worktrees, a register of slots and stand-ins of Docker, pnpm, uv."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.main = root / "main"
        self.log = root / "stand-in.log"
        self.register = root / "run" / "waterfall-slots"
        bin_directory = root / "bin"
        bin_directory.mkdir()
        for name in ("docker", "pnpm", "uv"):
            stand_in = bin_directory / name
            stand_in.write_text(STAND_IN)
            stand_in.chmod(0o755)
        kept = {
            name: value
            for name, value in os.environ.items()
            if name not in OUTER and not name.startswith(("WATERFALL_", "E2E_", "COMPOSE_"))
        }
        self.environment = kept | {
            "PATH": f"{bin_directory}{os.pathsep}{os.environ['PATH']}",
            "XDG_RUNTIME_DIR": str(root / "run"),
            "STAND_IN_LOG": str(self.log),
        }
        self.main.mkdir()
        self.git(self.main, "init", "--quiet")
        self.git(self.main, "commit", "--quiet", "--allow-empty", "--message", "start")
        (self.main / "frontend").mkdir()

    def git(self, directory: Path, *arguments: str) -> None:
        identity = ["-c", "user.name=test", "-c", "user.email=test@waterfall.test"]
        subprocess.run(
            ["git", *identity, *arguments],
            cwd=directory,
            env=self.environment,
            check=True,
            capture_output=True,
        )

    def worktree(self, name: str) -> Path:
        """Add a worktree of the main repository, in a detached head, as the harness does."""
        path = self.root / name
        self.git(self.main, "worktree", "add", "--quiet", "--detach", str(path))
        (path / "frontend").mkdir()
        return path

    def tool(
        self, directory: Path, *arguments: str, extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SLOTS), *arguments],
            cwd=directory,
            env=self.environment | (extra or {}),
            capture_output=True,
            text=True,
            check=False,
        )

    def make(
        self, directory: Path, *arguments: str, extra: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run the Makefile of the repository in the directory, on the tool of the repository."""
        return subprocess.run(
            [
                "make",
                "--no-print-directory",
                "-f",
                str(MAKEFILE),
                f"SLOTS={sys.executable} {SLOTS}",
                *arguments,
            ],
            cwd=directory,
            env=self.environment | (extra or {}),
            capture_output=True,
            text=True,
            check=False,
        )

    def logged(self) -> str:
        """Return what the stand-ins were asked, and forget it."""
        said = self.log.read_text() if self.log.exists() else ""
        self.log.unlink(missing_ok=True)
        return said


@pytest.fixture
def workstation(tmp_path: Path) -> Workstation:
    return Workstation(tmp_path)


def docker_asked(said: str) -> list[str]:
    return [line for line in said.splitlines() if line.startswith("docker")]


def all_ports(slot: int) -> set[int]:
    return set(slots.ports(slot).values()) | set(slots.front_ports(slot))


def test_no_port_belongs_to_two_slots_from_0_to_9() -> None:
    """US-1100: no port of the table belongs to two slots, from 0 to 9, nor twice to one."""
    owner: dict[int, int] = {}
    for slot in range(10):
        own = all_ports(slot)
        # The first front is a port of the table and of the fronts: every other port is apart.
        assert len(own) == len(slots.ports(slot)) - 1 + slots.FRONTS
        for port in own:
            assert port not in owner, f"port {port} of slot {slot} is slot {owner.get(port)}'s"
            owner[port] = slot
    assert max(owner) < 32768, "under the ephemeral ports of Linux"


@pytest.mark.parametrize("slot", range(1, 10))
def test_a_slot_has_the_ports_of_its_block(slot: int) -> None:
    """US-1100: at slot i of 1 to 9, the ports are in the block 20000 + 100·i, by the table."""
    first = 20000 + 100 * slot
    assert slots.ports(slot) == {
        "WATERFALL_TEST_POSTGRES_PORT": first,
        "WATERFALL_TEST_REDIS_PORT": first + 1,
        "WATERFALL_TEST_STORAGE_PORT": first + 2,
        "WATERFALL_POSTGRES_PORT": first + 10,
        "WATERFALL_REDIS_PORT": first + 11,
        "WATERFALL_API_PORT": first + 12,
        "WATERFALL_KEYCLOAK_PORT": first + 13,
        "WATERFALL_MAILPIT_PORT": first + 14,
        "WATERFALL_PROXY_PORT": first + 15,
        "E2E_API_PORT": first + 20,
        "E2E_FRONT_PORT": first + 40,
    }
    assert slots.front_ports(slot) == range(first + 40, first + 80)
    assert slots.names(slot) == {
        "WATERFALL_SERVICE_PROJECT": f"waterfall-service-s{slot}",
        "WATERFALL_TEST_PROJECT": f"waterfall-test-s{slot}",
        "WATERFALL_KEYCLOAK_IMAGE": f"waterfall-keycloak-s{slot}",
        "WATERFALL_FRONT_CHECK_IMAGE": f"waterfall-front:check-s{slot}",
    }


def test_slot_0_keeps_the_ports_and_names_of_before() -> None:
    """US-1100: at slot 0, the ports and names of before, and 20000 to 20002 for the tests."""
    assert slots.ports(0) == {
        "WATERFALL_TEST_POSTGRES_PORT": 20000,
        "WATERFALL_TEST_REDIS_PORT": 20001,
        "WATERFALL_TEST_STORAGE_PORT": 20002,
        "WATERFALL_POSTGRES_PORT": 5432,
        "WATERFALL_REDIS_PORT": 6379,
        "WATERFALL_API_PORT": 8000,
        "WATERFALL_KEYCLOAK_PORT": 8443,
        "WATERFALL_MAILPIT_PORT": 8025,
        "WATERFALL_PROXY_PORT": 4210,
        "E2E_API_PORT": 4110,
        "E2E_FRONT_PORT": 3100,
    }
    assert slots.names(0) == {
        "WATERFALL_SERVICE_PROJECT": "waterfall-service",
        "WATERFALL_TEST_PROJECT": "waterfall-test",
        "WATERFALL_KEYCLOAK_IMAGE": "waterfall-keycloak",
        "WATERFALL_FRONT_CHECK_IMAGE": "waterfall-front:check",
    }


def test_two_of_three_slots_asked_together_are_taken_at_two(workstation: Workstation) -> None:
    """US-1100: with N = 2, three worktrees ask for a slot at once: two get one, the third fails."""
    trees = [workstation.worktree(f"lot{i}") for i in range(3)]
    environment = workstation.environment | {"WATERFALL_SLOTS": "2"}
    asked = [
        subprocess.Popen(
            [sys.executable, str(SLOTS), "claim"],
            cwd=tree,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for tree in trees
    ]
    answers = [run.communicate(timeout=60) for run in asked]
    codes = sorted(run.returncode for run in asked)
    assert codes == [0, 0, 1]
    taken = slots.holders(workstation.register)
    assert sorted(taken) == [1, 2]
    holders = {holder.worktree for holder in taken.values()}
    refused = next(error for run, (_, error) in zip(asked, answers, strict=True) if run.returncode)
    assert "all 2 slot(s) are taken" in refused
    assert all(holder in refused for holder in holders)
    listed = workstation.make(workstation.main, "slots", extra={"WATERFALL_SLOTS": "2"}).stdout
    assert listed.startswith("WATERFALL_SLOTS=2\n")
    assert all(f"slot {slot}: {taken[slot].worktree}" in listed for slot in (1, 2))


def test_a_worktree_gets_back_the_slot_it_holds(workstation: Workstation) -> None:
    """US-1100: make slot gives a worktree the slot it holds already, and removes nothing then."""
    tree = workstation.worktree("lot")
    first = workstation.make(tree, "slot", extra={"WATERFALL_SLOTS": "3"})
    assert first.returncode == 0
    assert f"slot 1 taken: {tree}" in first.stdout
    assert "ports 20100 to 20199" in first.stdout
    workstation.logged()
    again = workstation.make(tree, "slot", extra={"WATERFALL_SLOTS": "3"})
    assert f"slot 1 already held: {tree}" in again.stdout
    assert workstation.logged() == ""
    assert workstation.tool(tree, "which").stdout == "1\n"


def test_the_register_holds_the_worktree_and_the_moment(workstation: Workstation) -> None:
    """US-1100: the file of a slot holds the path of its worktree and when it was taken."""
    tree = workstation.worktree("lot")
    workstation.tool(tree, "claim")
    path, taken, *rest = (workstation.register / "1").read_text().splitlines()
    assert path == str(tree)
    assert taken.startswith("20")
    assert taken.endswith("+00:00")
    assert rest == []


def test_the_main_repository_is_at_slot_0(workstation: Workstation) -> None:
    """US-1100: the main repository is at slot 0; make slot takes nothing for it."""
    assert workstation.tool(workstation.main, "which").stdout == "0\n"
    claimed = workstation.make(workstation.main, "slot")
    assert claimed.returncode == 0
    assert "slot 0" in claimed.stdout
    assert slots.holders(workstation.register) == {}
    released = workstation.make(workstation.main, "slot-release")
    assert released.returncode == 0
    assert workstation.logged() == "", "the main repository's platform is not removed"


def test_a_worktree_without_a_slot_is_told_make_slot(workstation: Workstation) -> None:
    """US-1100: in a linked worktree without a slot, which fails saying make slot."""
    tree = workstation.worktree("lot")
    which = workstation.tool(tree, "which")
    assert which.returncode == 1
    assert "make slot" in which.stderr
    released = workstation.make(tree, "slot-release")
    assert released.returncode == 0
    assert "holds no slot" in released.stdout


def test_an_abandoned_slot_is_taken_after_what_it_holds_is_removed(
    workstation: Workstation,
) -> None:
    """US-1100: a slot whose worktree no longer exists is free; what it held is removed first."""
    gone = workstation.worktree("gone")
    assert workstation.tool(gone, "claim").returncode == 0
    shutil.rmtree(gone)
    workstation.logged()
    tree = workstation.worktree("lot")
    listed = workstation.tool(tree, "list").stdout
    assert f"slot 1: {gone}" in listed
    assert "its worktree no longer exists" in listed
    claimed = workstation.tool(tree, "claim")
    assert claimed.returncode == 0
    assert "slot 1 taken" in claimed.stdout
    assert docker_asked(workstation.logged()) == [
        "docker compose -p waterfall-service-s1 down --volumes",
        "docker compose -p waterfall-test-s1 down --volumes",
    ]
    assert slots.holders(workstation.register)[1].worktree == str(tree)


def test_release_removes_the_projects_of_the_slot_then_frees_it(workstation: Workstation) -> None:
    """US-1100: make slot-release removes the containers and volumes of the slot, then frees it."""
    tree = workstation.worktree("lot")
    workstation.make(tree, "slot")
    workstation.logged()
    released = workstation.make(tree, "slot-release")
    assert released.returncode == 0
    assert "slot 1 released" in released.stdout
    assert docker_asked(workstation.logged()) == [
        "docker compose -p waterfall-service-s1 down --volumes",
        "docker compose -p waterfall-test-s1 down --volumes",
    ]
    assert slots.holders(workstation.register) == {}


def test_a_slot_whose_projects_cannot_be_removed_stays_taken(workstation: Workstation) -> None:
    """US-1100: when Docker cannot remove what the slot holds, it is not freed, and it says so."""
    tree = workstation.worktree("lot")
    workstation.tool(tree, "claim")
    released = workstation.tool(tree, "release", extra={"FAIL_CODE": "3"})
    assert released.returncode == 1
    assert "down --volumes failed with code 3" in released.stderr
    assert slots.holders(workstation.register)[1].worktree == str(tree)


def test_the_register_falls_back_on_tmp_without_a_runtime_directory() -> None:
    """US-1100: without XDG_RUNTIME_DIR, the register is in /tmp, as the heavy locks are."""
    assert slots.register({}) == Path(os.sep, "tmp", "waterfall-slots")
    assert slots.register({"XDG_RUNTIME_DIR": "/run/user/7"}) == Path("/run/user/7/waterfall-slots")


def test_a_target_of_a_worktree_without_a_slot_stops_saying_make_slot(
    workstation: Workstation,
) -> None:
    """US-1100: in a linked worktree without a slot, a target that needs one fails saying so."""
    tree = workstation.worktree("lot")
    for target in ("service-logs", "check-front-image", "build-keycloak"):
        stopped = workstation.make(tree, target)
        assert stopped.returncode != 0
        assert "run make slot" in stopped.stderr
    assert workstation.logged() == "", "nothing ran"
    assert workstation.make(tree, "lint-front").returncode == 0, "a target without ports runs"


def test_the_targets_of_a_slot_get_its_ports_and_names(workstation: Workstation) -> None:
    """US-1100: at slot 1, the service platform, the paths and the images are on its block."""
    tree = workstation.worktree("lot")
    workstation.tool(tree, "claim")
    workstation.logged()
    assert workstation.make(tree, "service-logs").returncode == 0
    said = workstation.logged()
    assert docker_asked(said)[0].endswith("-p waterfall-service-s1 logs --no-color")
    for line in (
        "WATERFALL_POSTGRES_PORT=20110",
        "WATERFALL_REDIS_PORT=20111",
        "WATERFALL_API_PORT=20112",
        "WATERFALL_KEYCLOAK_PORT=20113",
        "WATERFALL_MAILPIT_PORT=20114",
        "WATERFALL_PROXY_PORT=20115",
        "WATERFALL_KEYCLOAK_IMAGE=waterfall-keycloak-s1",
    ):
        assert line in said.splitlines()
    assert workstation.make(tree, "e2e", "TESTS=x", "E2E_DEV_SERVER=1").returncode == 0
    said = workstation.logged()
    assert "E2E_API_PORT=20120" in said.splitlines()
    assert "E2E_FRONT_PORT=20140" in said.splitlines()
    assert workstation.make(tree, "check-front-image").returncode == 0
    assert "WATERFALL_FRONT_CHECK_IMAGE=waterfall-front:check-s1" in workstation.logged()
    assert workstation.make(tree, "build-keycloak").returncode == 0
    assert "--tag waterfall-keycloak-s1 deploy/keycloak" in workstation.logged()


def test_a_port_the_environment_gives_wins(workstation: Workstation) -> None:
    """US-1100: the Makefile gives a port of the slot only when the environment does not."""
    tree = workstation.worktree("lot")
    workstation.tool(tree, "claim")
    workstation.logged()
    workstation.make(tree, "service-logs", extra={"WATERFALL_API_PORT": "18000"})
    said = workstation.logged().splitlines()
    assert "WATERFALL_API_PORT=18000" in said
    assert "WATERFALL_REDIS_PORT=20111" in said


def test_the_main_repository_keeps_its_ports_and_names(workstation: Workstation) -> None:
    """US-1100: in the main repository, the targets get the ports and names of before."""
    assert workstation.make(workstation.main, "service-logs").returncode == 0
    said = workstation.logged()
    assert docker_asked(said)[0].endswith("-p waterfall-service logs --no-color")
    assert "WATERFALL_API_PORT=8000" in said.splitlines()
    assert "WATERFALL_KEYCLOAK_PORT=8443" in said.splitlines()
    workstation.make(workstation.main, "e2e", "TESTS=x", "E2E_DEV_SERVER=1")
    said = workstation.logged().splitlines()
    assert "E2E_API_PORT=4110" in said
    assert "E2E_FRONT_PORT=3100" in said


def test_the_production_trial_runs_at_slot_0_alone(workstation: Workstation) -> None:
    """US-1100: make production-trial refuses to run outside slot 0, saying so, before anything."""
    tree = workstation.worktree("lot")
    for claimed in (False, True):
        if claimed:
            workstation.tool(tree, "claim")
        workstation.logged()
        refused = workstation.make(tree, "production-trial")
        assert refused.returncode != 0
        assert "runs at slot 0 alone" in refused.stderr
        assert workstation.logged() == ""
    assert workstation.make(workstation.main, "production-trial").returncode == 0
    assert "-m wftools.production" in workstation.logged()


def test_the_front_check_image_follows_the_environment() -> None:
    """US-1100: wftools.frontimage tags its image WATERFALL_FRONT_CHECK_IMAGE, given by make."""
    environment = {**os.environ, "WATERFALL_FRONT_CHECK_IMAGE": "waterfall-front:check-s4"}
    read = [sys.executable, "-c", "from wftools import frontimage; print(frontimage.IMAGE)"]
    tagged = subprocess.run(read, env=environment, capture_output=True, text=True, check=True)
    assert tagged.stdout == "waterfall-front:check-s4\n"
    environment.pop("WATERFALL_FRONT_CHECK_IMAGE")
    tagged = subprocess.run(read, env=environment, capture_output=True, text=True, check=True)
    assert tagged.stdout == "waterfall-front:check\n"
