# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workers `make e2e-service` hands to Playwright, as the Makefile reads them (#3029, #3011).

`make -n` expands what it runs without running it: a prerequisite of the target, added by
`--eval`, prints the value of E2E_WORKERS the target would export, and the commands printed before
an error show what a refusal came too late to stop. The environment gives
neither WATERFALL_PROCESSORS nor E2E_WORKERS, the case of a developer who just types
`make e2e-service`.

The share comes from the tool of the slots, run by the ``python3`` of the workstation: under
another one than the tools', `make -n test-back` says the tool did not run and why (US-2450). A
warning of the tool does not spoil its share, and what it says instead of one is relayed as it is.
"""

import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from test_launch import older_python, oldest_interpreter

from wftools import REPOSITORY, slots

if TYPE_CHECKING:
    from pathlib import Path

SLOTS = REPOSITORY / "tools" / "src" / "wftools" / "slots.py"
PRINTING = "probe: ; @echo E2E_WORKERS=$(E2E_WORKERS)"


def bare(tmp_path: Path) -> dict[str, str]:
    """Return an environment that gives neither WATERFALL_PROCESSORS nor E2E_WORKERS."""
    outer = ("MAKEFLAGS", "MAKELEVEL", "MFLAGS", "TESTS", "WATERFALL_SLOTS")
    outer += ("WATERFALL_PROCESSORS", "E2E_WORKERS")
    environment = {k: v for k, v in os.environ.items() if k not in outer}
    return environment | slots.variables(0) | {"XDG_RUNTIME_DIR": str(tmp_path)}


def play(tmp_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Return `make -n e2e-service` run in an environment without the variables of the share."""
    return subprocess.run(
        [
            *("make", "-n", "--no-print-directory", "e2e-service", "TESTS=x", *arguments),
            *("--eval", PRINTING, "--eval", "e2e-service: probe"),
        ],
        cwd=REPOSITORY,
        env=bare(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )


def workers(done: subprocess.CompletedProcess[str]) -> str:
    """Return the value the target would export, which the printing recipe echoes."""
    lines = [line for line in done.stdout.splitlines() if line.startswith("echo E2E_WORKERS=")]
    assert len(lines) == 1, done.stderr
    return lines[0].removeprefix("echo E2E_WORKERS=")


def test_the_service_paths_default_their_workers_without_any_variable(tmp_path: Path) -> None:
    """#3029: with no WATERFALL_PROCESSORS, GNU make 4.4 no longer reads the share empty."""
    done = play(tmp_path)
    assert done.returncode == 0, done.stderr
    assert "must be a positive integer" not in done.stderr
    share = subprocess.run(
        [sys.executable, str(SLOTS), "processors"],
        env=bare(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert 1 <= int(workers(done)) <= 40
    assert workers(done) == workers(play(tmp_path, f"WATERFALL_PROCESSORS={share.strip()}"))


def test_a_share_that_is_no_integer_is_refused_before_any_command(tmp_path: Path) -> None:
    """#3011: no installation, no build precedes the refusal of WATERFALL_PROCESSORS=abc."""
    done = play(tmp_path, "WATERFALL_PROCESSORS=abc")
    assert done.returncode != 0
    assert "WATERFALL_PROCESSORS must be a positive integer, got 'abc'" in done.stderr
    assert done.stdout == ""


@pytest.mark.story("US-2500")
@pytest.mark.parametrize("target", ["check-service", "check-all"])
def test_a_share_that_is_no_integer_is_refused_by_the_full_tier_of_the_families(
    tmp_path: Path, target: str
) -> None:
    """[US-2500] #3104: TIER=full of check-service and check-all refuses a share of abc."""
    done = subprocess.run(
        ["make", "-n", "--no-print-directory", target, "TIER=full", "WATERFALL_PROCESSORS=abc"],
        cwd=REPOSITORY,
        env=bare(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode != 0
    assert "WATERFALL_PROCESSORS must be a positive integer, got 'abc'" in done.stderr
    assert done.stdout == ""


def test_an_empty_workers_on_the_command_line_does_not_count(tmp_path: Path) -> None:
    """#3011: E2E_WORKERS= falls back to the default, and a number given wins."""
    assert workers(play(tmp_path, "WATERFALL_PROCESSORS=8", "E2E_WORKERS=")) == "6"
    assert workers(play(tmp_path, "WATERFALL_PROCESSORS=8", "E2E_WORKERS=5")) == "5"


def test_an_empty_share_on_the_command_line_is_refused(tmp_path: Path) -> None:
    """#3011: WATERFALL_PROCESSORS= is given, empty, so `?=` keeps it and the refusal names it."""
    done = play(tmp_path, "WATERFALL_PROCESSORS=")
    assert done.returncode != 0
    assert "WATERFALL_PROCESSORS must be a positive integer, got ''" in done.stderr
    assert done.stdout == ""


def test_a_workers_given_by_the_environment_wins(tmp_path: Path) -> None:
    """#3011: E2E_WORKERS=5 of the environment prevails over the share."""
    done = subprocess.run(
        [
            *("make", "-n", "--no-print-directory", "e2e-service", "TESTS=x"),
            *("WATERFALL_PROCESSORS=8", "--eval", PRINTING, "--eval", "e2e-service: probe"),
        ],
        cwd=REPOSITORY,
        env=bare(tmp_path) | {"E2E_WORKERS": "5"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert workers(done) == "5"


def plan_back(tmp_path: Path, python: Path) -> subprocess.CompletedProcess[str]:
    """Return `make -n test-back`, the ``python3`` of the directory ``python`` first on the PATH."""
    path = f"{python}{os.pathsep}{os.environ.get('PATH', '')}"
    return subprocess.run(
        ["make", "-n", "--no-print-directory", "test-back"],
        cwd=REPOSITORY,
        env=bare(tmp_path) | {"PATH": path},
        capture_output=True,
        text=True,
        check=False,
    )


def says_the_tool_did_not_run(done: subprocess.CompletedProcess[str]) -> None:
    """Check the plan stops on the reason of the tool of the slots, not on a setting."""
    assert done.returncode != 0
    assert "the tool of the slots did not run, it needs Python 3.14" in done.stderr
    assert "must be an integer from 1 to 9" not in done.stderr
    assert "uv run" not in done.stdout


@pytest.mark.story("US-2450")
def test_under_another_python_the_plan_of_the_back_says_why_the_slots_did_not_run(
    tmp_path: Path,
) -> None:
    says_the_tool_did_not_run(plan_back(tmp_path, older_python(tmp_path)))


@pytest.mark.story("US-2450")
@pytest.mark.unexecuted("skipped when the workstation has no Python older than 3.14")
def test_under_the_oldest_python_the_plan_of_the_back_says_why_the_slots_did_not_run(
    tmp_path: Path,
) -> None:
    oldest = oldest_interpreter()
    if oldest is None:
        pytest.skip("no Python older than 3.14 on the workstation")
    directory = tmp_path / "oldest"
    directory.mkdir()
    (directory / "python3").symlink_to(oldest)
    says_the_tool_did_not_run(plan_back(tmp_path, directory))


def fake_python(tmp_path: Path, script: str) -> Path:
    """Return a directory whose ``python3`` is the shell script ``script``, whatever it is asked."""
    directory = tmp_path / "fake"
    directory.mkdir()
    python3 = directory / "python3"
    python3.write_text(f"#!/bin/sh\n{script}", encoding="utf-8")
    python3.chmod(0o755)
    return directory


@pytest.mark.story("US-2450")
def test_a_warning_of_the_tool_does_not_spoil_its_share(tmp_path: Path) -> None:
    """The share is read on the standard output alone: a warning on the error output is kept out."""
    warning = fake_python(tmp_path, "echo 'warning: x' >&2\necho 3\n")
    done = plan_back(tmp_path, warning)
    assert done.returncode == 0, done.stderr
    assert " -n 3 " in done.stdout
    assert "no share" not in done.stderr


@pytest.mark.story("US-2450")
def test_the_reason_of_the_tool_is_relayed_as_it_is_said(tmp_path: Path) -> None:
    """Make does not read what the tool said as make: neither ``$(…)`` nor ``#`` is interpreted."""
    reason = "$(error INJECTED) under $$HOME #1"
    failing = fake_python(tmp_path, f"echo '{reason}' >&2\nexit 2\n")
    done = plan_back(tmp_path, failing)
    assert done.returncode != 0
    assert f"no share of the processors from the tool of the slots: {reason}." in done.stderr
    assert "*** INJECTED" not in done.stderr


def test_a_slot_count_the_tool_refuses_is_named_by_the_plan(tmp_path: Path) -> None:
    """The tool ran and refused the setting: make relays its words, not that it did not run."""
    done = subprocess.run(
        ["make", "-n", "--no-print-directory", "test-back", "WATERFALL_SLOTS=x"],
        cwd=REPOSITORY,
        env=bare(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode != 0
    assert "WATERFALL_SLOTS must be an integer from 1 to 9, not 'x'" in done.stderr
    assert "did not run" not in done.stderr


@pytest.mark.story("US-2500")
def test_the_reason_of_the_tool_keeps_its_own_point_once(tmp_path: Path) -> None:
    """[US-2500] #3784: a reason that ends by a point does not get a second one from make."""
    failing = fake_python(tmp_path, "echo 'refused because.' >&2\nexit 2\n")
    done = plan_back(tmp_path, failing)
    assert done.returncode != 0
    assert "the tool of the slots: refused because." in done.stderr
    assert "because.." not in done.stderr


@pytest.mark.story("US-2500")
def test_what_the_tool_says_on_its_standard_output_instead_of_a_share_is_relayed(
    tmp_path: Path,
) -> None:
    """[US-2500] #3784: an output that is no share is not lost behind "it said nothing"."""
    odd = fake_python(tmp_path, "echo 'three'\n")
    done = plan_back(tmp_path, odd)
    assert done.returncode != 0
    assert "the tool of the slots: three" in done.stderr
    assert "it said nothing" not in done.stderr
