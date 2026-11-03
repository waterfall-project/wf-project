# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Admit N heavy runs at a time on the workstation, each on its share of the processors (US-1090).

The Makefile runs every heavy run — the whole tests of a side, their coverage, the production
build of the front, the end-to-end paths — behind ``python3 tools/src/wftools/slots.py run
--heavy -- <command>``. It depends on the standard library alone and imports no other module of
``wftools``: the ``back`` job of the chain has not the environment of the tools.

``WATERFALL_SLOTS`` (1 by default, an integer from 1 to 9) says how many heavy runs pass at once,
whatever the repository or the worktree. Each slot is a lock file of ``$XDG_RUNTIME_DIR`` (``/tmp``
by default): ``waterfall-heavy.lock`` first — the lock of a repository whose Makefile predates
this tool takes the first slot —, then ``waterfall-heavy.2.lock`` to ``waterfall-heavy.<N>.lock``.
The tool takes the first free one by a ``flock`` that does not wait, holds it in its own process
for the whole run, and starts the command as a child that does not inherit the descriptor: a
server left behind by the command does not keep the slot. It relays the signals it receives and
returns the code of the command.

It sets ``WATERFALL_PROCESSORS``, the processors divided by N and at least 1, for the workers of
the command; ``processors`` prints the same number, for a Makefile that runs no heavy run. The
sub-commands are the shape the next stories of EP-19 extend.
"""

import argparse
import fcntl
import os
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

LOCK_NAME = "waterfall-heavy"
MAX_SLOTS = 9
RETRY_SECONDS = 1.0
RELAYED = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)


class SlotsError(Exception):
    """A setting the tool refuses, said to the user."""


def slot_count(environment: Mapping[str, str]) -> int:
    """N, from ``WATERFALL_SLOTS``: an integer from 1 to 9, 1 when absent."""
    raw = environment.get("WATERFALL_SLOTS")
    if raw is None:
        return 1
    if raw.isascii() and raw.isdigit() and 1 <= int(raw) <= MAX_SLOTS:
        return int(raw)
    message = f"WATERFALL_SLOTS must be an integer from 1 to {MAX_SLOTS}, not {raw!r}."
    raise SlotsError(message)


def processor_share(slots: int) -> int:
    """Return the N-th part of the processors this process may use, at least 1."""
    available = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    return max(1, (available or 1) // slots)


def lock_paths(environment: Mapping[str, str], slots: int) -> list[Path]:
    """Return the lock files of the N slots, the one of before this tool first."""
    directory = Path(environment.get("XDG_RUNTIME_DIR") or Path(os.sep, "tmp"))
    names = [f"{LOCK_NAME}.lock"] + [f"{LOCK_NAME}.{index}.lock" for index in range(2, slots + 1)]
    return [directory / name for name in names]


def take_slot(paths: Sequence[Path]) -> int | None:
    """Return the descriptor of the first free lock file, locked; None when all are taken."""
    for path in paths:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            continue
        return descriptor
    return None


def wait_for_slot(paths: Sequence[Path]) -> int:
    """Take a slot, saying once that all are taken, then trying again every second."""
    said = False
    while (descriptor := take_slot(paths)) is None:
        if not said:
            print(
                f"All {len(paths)} heavy slot(s) are taken; waiting for one to free.",
                file=sys.stderr,
                flush=True,
            )
            said = True
        time.sleep(RETRY_SECONDS)
    return descriptor


def run_command(command: Sequence[str], environment: Mapping[str, str]) -> int:
    """Run the command as a child, relaying the signals; return its code (128 + n if killed).

    The handlers are set before the child exists, so a signal that comes first is kept and relayed
    once it does: the tool never dies leaving a child without a slot. SIGINT from a terminal
    reaches the child by itself (same process group), so it is not relayed a second time; one sent
    to the tool alone, or kept from before the child existed, is.
    """
    children: list[subprocess.Popen[bytes]] = []
    early: list[int] = []

    def relay(received: int, _frame: object) -> None:
        if children:
            if received != signal.SIGINT:
                children[0].send_signal(received)
        else:
            early.append(received)

    previous = {number: signal.signal(number, relay) for number in RELAYED}
    try:
        try:
            child = subprocess.Popen(command, env=dict(environment), close_fds=True)
        except OSError as error:
            print(f"slots: cannot run {command[0]!r}: {error.strerror}", file=sys.stderr)
            return 127 if isinstance(error, FileNotFoundError) else 126
        children.append(child)
        for received in early:
            child.send_signal(received)
        code = child.wait()
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
    return 128 - code if code < 0 else code


def run_heavy(command: Sequence[str], environment: Mapping[str, str]) -> int:
    """Run the command in a free slot, on its share of the processors; return its code."""
    slots = slot_count(environment)
    descriptor = wait_for_slot(lock_paths(environment, slots))
    try:
        child_environment = {**environment, "WATERFALL_PROCESSORS": str(processor_share(slots))}
        return run_command(command, child_environment)
    finally:
        os.close(descriptor)


def parser() -> argparse.ArgumentParser:
    """Return the parser of the sub-commands."""
    main = argparse.ArgumentParser(prog="slots.py", description=(__doc__ or "").splitlines()[0])
    commands = main.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="run a command once a slot is free")
    run.add_argument("--heavy", action="store_true", required=True, help="a heavy run")
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- <command…>")
    commands.add_parser("processors", help="print the share of the processors of one heavy run")
    return main


def main(
    arguments: Sequence[str] | None = None, environment: Mapping[str, str] | None = None
) -> int:
    """Run a sub-command; return the exit code."""
    environment = os.environ if environment is None else environment
    options = parser().parse_args(arguments)
    try:
        if options.action == "processors":
            print(processor_share(slot_count(environment)))
            return 0
        command = options.command[1:] if options.command[:1] == ["--"] else options.command
        if not command:
            print("slots: run --heavy needs a command after --", file=sys.stderr)
            return 2
        return run_heavy(command, environment)
    except SlotsError as error:
        print(f"slots: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
