# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests that run a process of the platform share: wait for it, start it, stop it."""

import os
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

# Long enough for a process to start, and short enough for a test to fail in reasonable time.
PATIENCE = 30.0


def wait_for(condition: Callable[[], bool]) -> None:
    """Wait until a condition holds, or fail."""
    deadline = time.monotonic() + PATIENCE
    while not condition():
        assert time.monotonic() < deadline, "the condition never held"
        time.sleep(0.05)


@contextmanager
def started(arguments: list[str], environment: dict[str, str]) -> Generator[subprocess.Popen[str]]:
    """Run a process, in a group of its own, and stop the whole group when the block ends."""
    process = subprocess.Popen(
        arguments,
        env={"PATH": os.environ["PATH"], **environment},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        _, errors = process.communicate(timeout=PATIENCE)
        # What the process said, shown with the failure of the test.
        sys.stderr.write(errors)
