# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The turns of the heavy runs, and the workstation a measure takes alone (US-1090, US-2210).

``slots.py`` takes them here; this module, as that one, depends on the standard library alone,
for the ``back`` job of the chain runs ``slots.py`` as a script, this module beside it.

Each turn is a lock file of ``$XDG_RUNTIME_DIR`` (``/tmp`` by default): ``waterfall-heavy.lock``
first — the lock of a repository whose Makefile predates the tool takes the first turn —, then
``waterfall-heavy.2.lock`` to ``waterfall-heavy.<N>.lock``. A heavy run takes the first free one
by a ``flock`` that does not wait, and tries again every second.

An exclusive run (US-2210), for a measure, takes the gate ``waterfall-heavy.exclusive.lock`` of the
same directory, then every lock file, ``waterfall-heavy.lock`` to ``waterfall-heavy.9.lock`` — the
nine, whatever its N, so that a deliverer whose N is larger is held back too —, always in that
order: two exclusive runs take the gate one after the other and never each a half of the turns. It
waits for the heavy runs in progress, saying so once. A heavy run takes a shared lock of the gate,
without waiting, around its attempt at a turn: while an exclusive run holds or waits for the
turns, the heavy runs started meanwhile wait, saying so once. A tool that predates the gate does
not see it, and is waited for like any heavy run in progress — but it does not wait for the gate
in turn, and may take a turn back before the exclusive run gets it: a measure holds the
workstation against the other deliverers once their branches have this tool.

The command of an exclusive run is given ``WATERFALL_SLOTS_HELD=exclusive``: a heavy or exclusive
run it starts in turn — a ``make`` behind ``$(heavy)`` — takes no turn, as the turns are its
parent's and waiting for them would never end, and says so. The mark is believed only while an
exclusive run holds the gate: one that outlived its measure, in a server the measure left, is
dropped and the run takes its turn as any other.
"""

import fcntl
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

LOCK_NAME = "waterfall-heavy"
GATE_NAME = f"{LOCK_NAME}.exclusive.lock"
"""The lock an exclusive run holds the whole time, and a heavy run shares while it takes a turn."""
MAX_SLOTS = 9
RETRY_SECONDS = 1.0
GATE_PATIENCE = 1.0
"""How long an exclusive run waits for the gate before it says so: a heavy run shares it briefly."""
GATE_POLL = 0.05
HELD_VARIABLE = "WATERFALL_SLOTS_HELD"
HELD_EXCLUSIVE = "exclusive"
"""The mark an exclusive run gives its command: the workstation is held above it."""


def runtime_directory(environment: Mapping[str, str]) -> Path:
    """Return ``$XDG_RUNTIME_DIR``, or ``/tmp`` where it is not set (WSL, a runner)."""
    return Path(environment.get("XDG_RUNTIME_DIR") or Path(os.sep, "tmp"))


def lock_paths(environment: Mapping[str, str], slots: int) -> list[Path]:
    """Return the lock files of the N turns, the one of before this tool first."""
    directory = runtime_directory(environment)
    names = [f"{LOCK_NAME}.lock"] + [f"{LOCK_NAME}.{index}.lock" for index in range(2, slots + 1)]
    return [directory / name for name in names]


def gate_path(environment: Mapping[str, str]) -> Path:
    """Return the gate of the exclusive runs, beside the lock files of the turns."""
    return runtime_directory(environment) / GATE_NAME


def open_lock(path: Path) -> int:
    """Open a lock file, created if it is not; the descriptor is not inherited by the command."""
    return os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)


def take_slot(paths: Sequence[Path]) -> int | None:
    """Return the descriptor of the first free lock file, locked; None when all are taken."""
    for path in paths:
        descriptor = open_lock(path)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(descriptor)
            continue
        return descriptor
    return None


def take_slot_past_gate(paths: Sequence[Path], gate: Path) -> int | str:
    """Return the descriptor of a free turn, locked, or why there is none to take now.

    The shared lock of the gate is held only around the attempt: an exclusive run that asks for the
    gate gets it as soon as the attempt ends, and the heavy runs started after it wait.
    """
    shared = open_lock(gate)
    try:
        try:
            fcntl.flock(shared, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return "An exclusive run holds the workstation; waiting for it to end."
        descriptor = take_slot(paths)
        if descriptor is None:
            return f"All {len(paths)} heavy slot(s) are taken; waiting for one to free."
        return descriptor
    finally:
        os.close(shared)


def wait_for_slot(paths: Sequence[Path], gate: Path) -> int:
    """Take a turn, saying once each reason to wait, then trying again every second."""
    said: set[str] = set()
    while isinstance(taken := take_slot_past_gate(paths, gate), str):
        if taken not in said:
            print(taken, file=sys.stderr, flush=True)
            said.add(taken)
        time.sleep(RETRY_SECONDS)
    return taken


def lock_waiting(path: Path, reason: str, *, said: bool, patience: float = 0.0) -> tuple[int, bool]:
    """Take the lock, waiting; return it and whether the reason is said.

    The reason is said once, and only past ``patience`` seconds of trying without waiting.
    """
    descriptor = open_lock(path)
    deadline = time.monotonic() + patience
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if time.monotonic() < deadline:
                    time.sleep(GATE_POLL)
                    continue
                if not said:
                    print(reason, file=sys.stderr, flush=True)
                    said = True
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            return descriptor, said
    except BaseException:
        os.close(descriptor)
        raise


def take_workstation(environment: Mapping[str, str]) -> list[int]:
    """Take the gate, then every turn of the heavy runs in their order; return the descriptors.

    The fixed order keeps two exclusive runs from each holding a part: the gate makes them one
    after the other. Whatever is taken is freed if the wait is interrupted.
    """
    descriptors: list[int] = []
    other = "Another exclusive run holds the workstation; waiting."
    heavy = "Heavy runs are in progress; waiting for them to end, the next ones held back."
    try:
        gate = lock_waiting(gate_path(environment), other, said=False, patience=GATE_PATIENCE)
        descriptors.append(gate[0])
        said = False
        for path in lock_paths(environment, MAX_SLOTS):
            descriptor, said = lock_waiting(path, heavy, said=said)
            descriptors.append(descriptor)
    except BaseException:
        for descriptor in descriptors:
            os.close(descriptor)
        raise
    return descriptors


def held_above(environment: Mapping[str, str]) -> bool:
    """Tell whether an exclusive run above this one holds the workstation: its mark, its gate held.

    A shared lock of the gate is refused only while an exclusive run holds it.
    """
    if environment.get(HELD_VARIABLE) != HELD_EXCLUSIVE:
        return False
    descriptor = open_lock(gate_path(environment))
    try:
        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(descriptor)
    return False
