# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The services of the tests of a slot, started by the Makefile for the tests that need them.

(US-1110.)

The tool is run as the Makefile runs it, ``python3 slots.py run --services …``, in the repositories
of git made for the test by ``test_worktree_slots``: a main repository and worktrees of it, each
with a Makefile that includes the one of the repository, and the stand-ins of Docker, pnpm and uv
on the ``PATH``, which write what they are asked and the variables they are given. Nothing is
started: the tests tell what the Makefile asks of Docker, in which order, and what the tests are
given.
"""

import fcntl
import os
import re
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest
from test_worktree_slots import MAKEFILE, SLOTS, Workstation, docker_asked

from wftools import REPOSITORY, mirror, slots

if TYPE_CHECKING:
    from pathlib import Path

COMPOSE_TEST = REPOSITORY / "deploy" / "compose" / "compose.test.yaml"
COMPOSE_SERVICE = REPOSITORY / "deploy" / "compose" / "compose.service.yaml"
UP = "docker compose -f deploy/compose/compose.test.yaml -p {project} up --detach --wait{services}"
BACK_URLS = [
    "WATERFALL_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:{postgres}/postgres",
    "WATERFALL_TEST_REDIS_URL=redis://127.0.0.1:{redis}/0",
    "WATERFALL_TEST_STORAGE_URL=http://{credentials}@127.0.0.1:{storage}",
]


@pytest.fixture
def workstation(tmp_path: Path) -> Workstation:
    return Workstation(tmp_path)


def lot(workstation: Workstation, *, claimed: bool = True) -> Path:
    """Add a worktree that runs the Makefile of the repository, with a slot unless told not."""
    tree = workstation.worktree("lot")
    (tree / "Makefile").write_text(f"include {MAKEFILE}\n")
    (tree / "tools").symlink_to(REPOSITORY / "tools")
    (tree / "backend").mkdir()
    if claimed:
        assert workstation.tool(tree, "claim").returncode == 0
    workstation.logged()
    return tree


def run_make(
    workstation: Workstation, tree: Path, *arguments: str, extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", *arguments],
        cwd=tree,
        env=workstation.environment | (extra or {}),
        capture_output=True,
        text=True,
        check=False,
    )


def expected_urls(slot: int) -> list[str]:
    first = slots.block(slot)
    return [
        line.format(
            postgres=first,
            redis=first + 1,
            storage=first + 2,
            credentials=slots.TEST_STORAGE_CREDENTIALS,
        )
        for line in BACK_URLS
    ]


def test_make_test_services_starts_the_project_of_the_slot_on_its_ports(
    workstation: Workstation,
) -> None:
    """US-1110: make test-services starts the three services under the project of the slot."""
    tree = lot(workstation)
    assert run_make(workstation, tree, "test-services").returncode == 0
    said = workstation.logged()
    assert docker_asked(said) == [UP.format(project="waterfall-test-s1", services="")]
    for line in (
        "WATERFALL_TEST_POSTGRES_PORT=20100",
        "WATERFALL_TEST_REDIS_PORT=20101",
        "WATERFALL_TEST_STORAGE_PORT=20102",
    ):
        assert line in said.splitlines()


def test_make_test_services_down_removes_the_project_of_the_slot_and_its_volumes(
    workstation: Workstation,
) -> None:
    """US-1110: make test-services-down removes the services of the slot and their volumes."""
    tree = lot(workstation)
    assert run_make(workstation, tree, "test-services-down").returncode == 0
    assert docker_asked(workstation.logged()) == [
        "docker compose -f deploy/compose/compose.test.yaml -p waterfall-test-s1 down --volumes"
    ]


def test_the_main_repository_has_the_test_services_at_slot_0(workstation: Workstation) -> None:
    """US-1110: in the main repository, the project is waterfall-test, the ports 20000 to 20002."""
    (workstation.main / "Makefile").write_text(f"include {MAKEFILE}\n")
    (workstation.main / "tools").symlink_to(REPOSITORY / "tools")
    assert run_make(workstation, workstation.main, "test-services").returncode == 0
    said = workstation.logged()
    assert docker_asked(said) == [UP.format(project="waterfall-test", services="")]
    assert "WATERFALL_TEST_POSTGRES_PORT=20000" in said.splitlines()


@pytest.mark.parametrize("target", ["test-services", "test-services-down", "test-back"])
def test_a_worktree_without_a_slot_is_told_make_slot_and_starts_nothing(
    workstation: Workstation, target: str
) -> None:
    """US-1110: no slot, no services: the targets that need them say make slot, before anything."""
    tree = lot(workstation, claimed=False)
    stopped = run_make(workstation, tree, target, "TESTS=tests/test_x.py")
    assert stopped.returncode != 0
    assert "run make slot" in stopped.stderr
    assert workstation.logged() == ""


@pytest.mark.parametrize(
    ("target", "arguments"),
    [
        ("test-back", ["TESTS=tests/test_x.py"]),
        ("test-back", []),
        ("coverage-back", []),
    ],
)
def test_the_tests_of_the_back_have_their_services_started_and_their_urls_set(
    workstation: Workstation, target: str, arguments: list[str]
) -> None:
    """US-1110: the tests of the back, TESTS or not, start their services and read them."""
    tree = lot(workstation)
    assert run_make(workstation, tree, target, *arguments).returncode == 0
    lines = workstation.logged().splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("docker")]
    assert [lines[i] for i in starts] == [
        UP.format(project="waterfall-test-s1", services=" postgres redis storage")
    ]
    ran = next(i for i, line in enumerate(lines) if line.startswith("uv run"))
    assert starts[0] < ran, "the services start before the tests"
    assert set(expected_urls(1)) <= set(lines[ran:])


@pytest.mark.parametrize(
    ("target", "arguments"),
    [
        ("test-front", ["TESTS=src/x.test.ts"]),
        ("test-front", []),
        ("coverage-front", []),
    ],
)
def test_the_tests_of_the_front_have_their_redis_started_and_its_url_set(
    workstation: Workstation, target: str, arguments: list[str]
) -> None:
    """US-1110: the tests of the front, TESTS or not, start Redis alone and read it at the slot."""
    tree = lot(workstation)
    assert run_make(workstation, tree, target, *arguments).returncode == 0
    lines = workstation.logged().splitlines()
    assert docker_asked("\n".join(lines)) == [
        UP.format(project="waterfall-test-s1", services=" redis")
    ]
    ran = max(i for i, line in enumerate(lines) if line.startswith("pnpm"))
    assert "WATERFALL_TEST_REDIS_URL=redis://127.0.0.1:20101/0" in lines[ran:]
    assert not [line for line in lines[ran:] if line.startswith("WATERFALL_TEST_DATABASE")]


def test_a_variable_the_environment_gives_wins_and_its_service_is_not_started(
    workstation: Workstation,
) -> None:
    """US-1110: a WATERFALL_TEST_*_URL already set is kept, and its service not started."""
    tree = lot(workstation)
    given = {"WATERFALL_TEST_REDIS_URL": "redis://chain:6379/3"}
    assert run_make(workstation, tree, "test-back", "TESTS=tests/x.py", extra=given).returncode == 0
    lines = workstation.logged().splitlines()
    assert docker_asked("\n".join(lines)) == [
        UP.format(project="waterfall-test-s1", services=" postgres storage")
    ]
    assert "WATERFALL_TEST_REDIS_URL=redis://chain:6379/3" in lines
    assert expected_urls(1)[0] in lines
    assert expected_urls(1)[2] in lines


def test_the_chain_gives_every_variable_and_nothing_is_started_or_asked(
    workstation: Workstation,
) -> None:
    """US-1110: with the three variables given, as the chain does, no Docker, and no slot needed."""
    tree = lot(workstation, claimed=False)
    (workstation.root / "run").mkdir()  # the locks of the heavy runs
    given = {
        "WATERFALL_TEST_DATABASE_URL": "postgresql://postgres@localhost:5432/postgres",
        "WATERFALL_TEST_REDIS_URL": "redis://127.0.0.1:6379/0",
        "WATERFALL_TEST_STORAGE_URL": "http://key:secret@127.0.0.1:3900",
    }
    assert run_make(workstation, tree, "test-back", extra=given).returncode == 0
    lines = workstation.logged().splitlines()
    assert docker_asked("\n".join(lines)) == []
    assert {f"{name}={value}" for name, value in given.items()} <= set(lines)
    assert run_make(workstation, tree, "test-front", extra=given).returncode == 0
    assert docker_asked(workstation.logged()) == []


def test_a_port_the_environment_gives_is_the_one_the_url_names(workstation: Workstation) -> None:
    """US-1110: the URL follows a port the environment gives, which the Makefile uses as well."""
    tree = lot(workstation)
    extra = {"WATERFALL_TEST_REDIS_PORT": "26379"}
    assert run_make(workstation, tree, "test-front", "TESTS=x", extra=extra).returncode == 0
    lines = workstation.logged().splitlines()
    assert "WATERFALL_TEST_REDIS_PORT=26379" in lines
    assert "WATERFALL_TEST_REDIS_URL=redis://127.0.0.1:26379/0" in lines


def test_the_services_start_once_the_heavy_slot_is_taken_not_before(
    workstation: Workstation,
) -> None:
    """US-1110: a run that waits for a heavy slot starts its services after the wait, not before."""
    tree = lot(workstation)
    held = workstation.root / "run" / "waterfall-heavy.lock"
    descriptor = os.open(held, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    waiting = subprocess.Popen(
        ["make", "--no-print-directory", "test-back"],
        cwd=tree,
        env=workstation.environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(1.5)
        assert waiting.poll() is None, "the run waits for the slot"
        assert workstation.logged() == "", "no service is started while it waits"
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
    _, error = waiting.communicate(timeout=60)
    assert waiting.returncode == 0, error
    lines = workstation.logged().splitlines()
    assert lines[0].startswith("docker compose"), "the services start first"
    assert any(line.startswith("uv run") for line in lines[1:])


def test_a_failed_start_of_the_services_stops_before_the_tests(workstation: Workstation) -> None:
    """US-1110: when the services do not start, the tests are not run, and the failure is said."""
    tree = lot(workstation)
    failed = run_make(workstation, tree, "test-back", "TESTS=x", extra={"FAIL_CODE": "3"})
    assert failed.returncode != 0
    assert "slots: " in failed.stderr
    assert "failed with code" in failed.stderr
    assert not [line for line in workstation.logged().splitlines() if line.startswith("uv run")]


def test_run_refuses_an_unknown_service_and_a_run_that_asks_for_nothing(tmp_path: Path) -> None:
    """US-1110: run --services names db, redis and storage; run needs --heavy or --services."""
    environment = {**os.environ, "XDG_RUNTIME_DIR": str(tmp_path)}
    unknown = subprocess.run(
        [sys.executable, str(SLOTS), "run", "--services", "db,mongo", "--", "true"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert unknown.returncode == 2
    assert "mongo" in unknown.stderr
    nothing = subprocess.run(
        [sys.executable, str(SLOTS), "run", "--", "true"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert nothing.returncode == 2
    assert "needs --heavy, --services" in nothing.stderr


def test_the_compose_file_has_the_images_the_platform_has_and_the_ports_of_slot_0() -> None:
    """US-1110: the same pinned images as the platform, PostgreSQL 18 included, on localhost."""
    text = COMPOSE_TEST.read_text()
    platform = COMPOSE_SERVICE.read_text()
    images = re.findall(r"^\s+image: (\S+)$", text, flags=re.MULTILINE)
    assert len(images) == 3
    assert images[0].startswith(f"{mirror.MIRROR}/postgres:18-")
    for image in images:
        assert "@sha256:" in image
        assert image in platform
    published = re.findall(r'- "127\.0\.0\.1:\$\{(\w+):-(\d+)\}:', text)
    ports = slots.ports(0)
    assert [(name, int(port)) for name, port in published] == [
        (name, ports[name]) for name in slots.TEST_SERVICE_OFFSETS
    ]
    assert text.count("healthcheck:") == 3
    assert "POSTGRES_HOST_AUTH_METHOD: trust" in text
    assert "- /var/lib/postgresql\n" in text.split("tmpfs:")[1]


def test_the_storage_key_of_the_compose_file_is_the_one_of_the_url() -> None:
    """US-1110: the key the URL of the storage names is the one Garage is given."""
    text = COMPOSE_TEST.read_text()
    key, _, secret = slots.TEST_STORAGE_CREDENTIALS.partition(":")
    assert f"GARAGE_DEFAULT_ACCESS_KEY: {key}" in text
    assert f"GARAGE_DEFAULT_SECRET_KEY: {secret}" in text


def test_two_runs_of_one_worktree_start_the_test_services_one_at_a_time(
    workstation: Workstation,
) -> None:
    """US-1300: the second run waits under the lock of the slot, then finds the services started."""
    tree = lot(workstation)
    gate = workstation.root / "gate"
    environment = workstation.environment | {"STAND_IN_GATE": str(gate)}
    command = [sys.executable, str(SLOTS), "run", "--services", "redis", "--", "true"]
    first = subprocess.Popen(command, cwd=tree, env=environment, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 60
    while not workstation.log.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    second = subprocess.Popen(command, cwd=tree, env=environment, stderr=subprocess.PIPE, text=True)
    try:
        time.sleep(1.5)
        assert first.poll() is None
        assert second.poll() is None, "the second run waits for the first"
        assert len(docker_asked(workstation.log.read_text())) == 1, "one make test-services only"
    finally:
        gate.write_text("")
    _, first_error = first.communicate(timeout=60)
    _, second_error = second.communicate(timeout=60)
    assert first.returncode == 0, first_error
    assert second.returncode == 0, second_error
    assert "being started by another run; waiting" in second_error
    assert "waiting" not in first_error
    assert len(docker_asked(workstation.logged())) == 2, "the second finds them and does nothing"
    assert (workstation.root / "run" / "waterfall-test-services.1.lock").exists()
