# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the trial of the chart runs commands by, and how it fails (US-2800).

``wftools.charttrial`` and the modules it hands work to — the authority of the trial, the cluster of
k3s — run a command through a function they are given, so that a test gives its own: ``Run`` for a
command whose outcome is a status, ``Read`` for one whose standard output is wanted. A command that
must succeed is named by what it was for, not by its words, which say nothing of the cause.
"""

from collections.abc import Callable

Run = Callable[[list[str]], int]
Read = Callable[[list[str]], tuple[int, str]]
Ask = Callable[[list[str], str], tuple[int, str]]


class TrialError(Exception):
    """What the cluster or the chart does not do as it must."""


def must(run: Run, command: list[str], what: str) -> None:
    """Run a command that must succeed; fail naming what it was for — its words say not."""
    if code := run(command):
        message = f"{what} failed ({code})"
        raise TrialError(message)


def output(read: Read, command: list[str], what: str) -> str:
    """Run a command that must succeed and return what it wrote; fail naming what it was for."""
    code, written = read(command)
    if code != 0:
        message = f"{what} failed ({code})"
        raise TrialError(message)
    return written
