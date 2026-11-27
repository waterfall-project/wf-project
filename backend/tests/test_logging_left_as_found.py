# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A test that runs an entry point leaves the logging of the process as it found it (#5155).

No requirement of the specification speaks of how the tests share a process: these tests cite none.
"""

import subprocess
import sys
from pathlib import Path

BACK = Path(__file__).parent.parent


def test_a_test_that_logs_after_one_that_ran_an_entry_point_reads_its_own_output() -> None:
    """The couple that failed in a chain run: ``main(["test"])``, then a read of the output."""
    restoration = "test_a_test_of_a_restoration_that_cannot_run_returns_failure_and_says_why"
    refusal = "test_the_refusal_of_a_row_not_written_names_it_in_the_log_for_each_of_the_two_rows"
    selected = [
        f"tests/test_restore_main.py::{restoration}",
        f"tests/test_actual_cost_mapping.py::{refusal}",
    ]
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-n0",
            "-p",
            "no:randomly",
            "-p",
            "no:cacheprovider",
            *selected,
        ],
        cwd=BACK,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stdout
