# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workers `make e2e-service` hands to Playwright, as the Makefile reads them (#3029, #3011).

`make -n` expands what it runs without running it: a prerequisite of the target, added by
`--eval`, prints the value of E2E_WORKERS the target would export, and the commands printed before
an error show what a refusal came too late to stop. The environment gives
neither WATERFALL_PROCESSORS nor E2E_WORKERS, the case of a developer who just types
`make e2e-service`.
"""

import os
import subprocess
import sys
from typing import TYPE_CHECKING

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
    assert workers(done) == str(max(1, min(40, int(share) * 3 // 4)))


def test_a_share_that_is_no_integer_is_refused_before_any_command(tmp_path: Path) -> None:
    """#3011: no installation, no build precedes the refusal of WATERFALL_PROCESSORS=abc."""
    done = play(tmp_path, "WATERFALL_PROCESSORS=abc")
    assert done.returncode != 0
    assert "WATERFALL_PROCESSORS must be a positive integer, got 'abc'" in done.stderr
    assert done.stdout == ""


def test_an_empty_workers_on_the_command_line_does_not_count(tmp_path: Path) -> None:
    """#3011: E2E_WORKERS= falls back to the default, and a number given wins."""
    assert workers(play(tmp_path, "WATERFALL_PROCESSORS=8", "E2E_WORKERS=")) == "6"
    assert workers(play(tmp_path, "WATERFALL_PROCESSORS=8", "E2E_WORKERS=5")) == "5"
