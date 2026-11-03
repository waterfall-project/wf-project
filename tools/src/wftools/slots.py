# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Admit N heavy runs at a time; give each worktree of a lot a slot of its own (US-1090, US-1100).

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
the command; ``processors`` prints the same number, for a Makefile that runs no heavy run.

The same N bounds the worktrees of the lots, each of which takes a slot of 1 to N (``claim``,
``make slot``) that gives it its ports, its projects of Compose and the tags of its images; the
main repository — and every runner of the chain, a main repository too — is at slot 0, on the
ports and under the names of before. The register of the workstation, whatever the repository, is
``$XDG_RUNTIME_DIR/waterfall-slots/``: a file ``<i>`` for each slot taken, which holds the path of
its worktree and the moment it was taken, written under an exclusive lock of the register. A slot
whose worktree no longer exists is free; whoever takes a slot first removes the projects of
Compose an earlier holder left in it, volumes included, as ``release`` does before it frees it,
the lock held until they are removed.
``which`` prints the slot of the current worktree, ``which --variables`` its ports and names for the
Makefile, and ``list`` the slots taken on the workstation.
"""

import argparse
import fcntl
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

LOCK_NAME = "waterfall-heavy"
MAX_SLOTS = 9
RETRY_SECONDS = 1.0
REMOVE_SECONDS = 300
"""How long ``docker compose down`` may take, the lock of the register held, before it fails."""
RELAYED = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)

REGISTER_NAME = "waterfall-slots"
REGISTER_LOCK = ".lock"
BLOCK_START = 20000
BLOCK_SIZE = 100
FRONTS = 40
"""The fronts of the end-to-end paths a slot has ports for, one for each worker."""
TEST_SERVICE_OFFSETS = {
    "WATERFALL_TEST_POSTGRES_PORT": 0,
    "WATERFALL_TEST_REDIS_PORT": 1,
    "WATERFALL_TEST_STORAGE_PORT": 2,
}
"""The services of the tests of a slot, in its block, at slot 0 too: they are new."""
SLOT_OFFSETS = {
    "WATERFALL_POSTGRES_PORT": 10,
    "WATERFALL_REDIS_PORT": 11,
    "WATERFALL_API_PORT": 12,
    "WATERFALL_KEYCLOAK_PORT": 13,
    "WATERFALL_MAILPIT_PORT": 14,
    "WATERFALL_PROXY_PORT": 15,
    "E2E_API_PORT": 20,
    "E2E_FRONT_PORT": 40,
}
"""The service platform, the fake back and the first front of the paths, in the block of a slot."""
PORTS_OF_BEFORE = {
    "WATERFALL_POSTGRES_PORT": 5432,
    "WATERFALL_REDIS_PORT": 6379,
    "WATERFALL_API_PORT": 8000,
    "WATERFALL_KEYCLOAK_PORT": 8443,
    "WATERFALL_MAILPIT_PORT": 8025,
    "WATERFALL_PROXY_PORT": 4210,
    "E2E_API_PORT": 4110,
    "E2E_FRONT_PORT": 3100,
}
"""The same at slot 0, the ports of the main repository before the slots."""
GIT_FATAL = 128
OUTSIDE_REPOSITORY = "not a git repository (or any"
"""The code and the words of git for a directory outside any repository (``LC_ALL=C``)."""
COMPOSE_SETTINGS = ("COMPOSE_FILE", "COMPOSE_PROJECT_NAME", "COMPOSE_PROFILES")
"""What would point ``docker compose -p <project> down`` at another file or project."""


class SlotsError(Exception):
    """A setting the tool refuses, said to the user."""


class RegisterError(SlotsError):
    """A slot the tool cannot give, find or free, said to the user."""


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


def runtime_directory(environment: Mapping[str, str]) -> Path:
    """Return ``$XDG_RUNTIME_DIR``, or ``/tmp`` where it is not set (WSL, a runner)."""
    return Path(environment.get("XDG_RUNTIME_DIR") or Path(os.sep, "tmp"))


def lock_paths(environment: Mapping[str, str], slots: int) -> list[Path]:
    """Return the lock files of the N slots, the one of before this tool first."""
    directory = runtime_directory(environment)
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
    once it does: the tool never dies leaving a child without a slot. Every signal is relayed,
    SIGINT included, before and after the child exists, so one sent to the tool alone reaches it.
    """
    children: list[subprocess.Popen[bytes]] = []
    early: list[int] = []

    def relay(received: int, _frame: object) -> None:
        if children:
            # On Ctrl-C the child gets SIGINT twice, by the group and by this relay: accepted,
            # as a child outside the foreground group would lose the terminal.
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


# --- The slots of the worktrees (US-1100) ---------------------------------------------------------


class Worktree(NamedTuple):
    """Where a command runs: the top of its checkout, and whether it is the main repository."""

    path: Path
    main: bool


class Holder(NamedTuple):
    """A slot taken: the path of the worktree that holds it, and the moment it was taken."""

    worktree: str
    taken: str

    def abandoned(self) -> bool:
        """Whether the worktree no longer exists: removed, or never written whole."""
        path = Path(self.worktree)
        return not (self.worktree and path.is_absolute() and (path / ".git").exists())


Remove = Callable[[int], None]
"""Removes the projects of Compose of a slot, volumes included; raises ``RegisterError``."""


def block(slot: int) -> int:
    """Return the first port of the block of a slot."""
    return BLOCK_START + BLOCK_SIZE * slot


def ports(slot: int) -> dict[str, int]:
    """Return the ports of a slot: its block, or at slot 0 those of before, but for the tests."""
    tests = {name: block(slot) + offset for name, offset in TEST_SERVICE_OFFSETS.items()}
    if slot == 0:
        return tests | PORTS_OF_BEFORE
    return tests | {name: block(slot) + offset for name, offset in SLOT_OFFSETS.items()}


def front_ports(slot: int) -> range:
    """Return the ports of the fronts of the paths of a slot, one for each worker."""
    first = ports(slot)["E2E_FRONT_PORT"]
    return range(first, first + FRONTS)


def names(slot: int) -> dict[str, str]:
    """Return the projects of Compose and the tags of the images of a slot; at 0, as before."""
    suffix = f"-s{slot}" if slot else ""
    return {
        "WATERFALL_SERVICE_PROJECT": f"waterfall-service{suffix}",
        "WATERFALL_TEST_PROJECT": f"waterfall-test{suffix}",
        "WATERFALL_KEYCLOAK_IMAGE": f"waterfall-keycloak{suffix}",
        "WATERFALL_FRONT_CHECK_IMAGE": f"waterfall-front:check{suffix}",
    }


def variables(slot: int) -> dict[str, str]:
    """Return what the Makefile gives the targets of a slot: its number, its ports, its names."""
    numbers = {name: str(port) for name, port in ports(slot).items()}
    return {"WATERFALL_SLOT": str(slot)} | numbers | names(slot)


def current_worktree(directory: Path | None = None) -> Worktree | None:
    """Return the worktree a command runs in; None outside a repository of git, or without git.

    Any other failure of git — a repository it refuses to read — is said, not taken for slot 0:
    a linked worktree would be given the ports and names of the main repository.
    """
    asked = ["--show-toplevel", "--git-dir", "--git-common-dir"]
    try:
        found = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", *asked],
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
    except FileNotFoundError:
        return None
    lines = found.stdout.splitlines()
    if found.returncode == GIT_FATAL and OUTSIDE_REPOSITORY in found.stderr:
        return None
    if found.returncode != 0 or len(lines) != len(asked):
        message = f"git cannot say which worktree this is: {found.stderr.strip() or found.stdout}"
        raise SlotsError(message)
    top, own, common = lines
    return Worktree(Path(top), Path(own).resolve() == Path(common).resolve())


def register(environment: Mapping[str, str]) -> Path:
    """Return the register of the slots of the workstation."""
    return runtime_directory(environment) / REGISTER_NAME


@contextmanager
def locked(directory: Path) -> Generator[None]:
    """Hold the exclusive lock of the register, created if it is not; say once when it waits."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(directory / REGISTER_LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(
                "The register of the slots is held, a slot being taken or released; waiting.",
                file=sys.stderr,
                flush=True,
            )
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def holders(directory: Path) -> dict[int, Holder]:
    """Return the slots taken in the register, by number."""
    taken: dict[int, Holder] = {}
    if not directory.is_dir():
        return taken
    for entry in directory.iterdir():
        if entry.name not in {str(slot) for slot in range(1, MAX_SLOTS + 1)}:
            continue
        try:
            lines = entry.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            continue
        except (OSError, UnicodeDecodeError):
            lines = []  # unreadable: no worktree, so abandoned, and taken again as such
        worktree, taken_at = ([*lines, "", ""])[:2]
        taken[int(entry.name)] = Holder(worktree, taken_at)
    return dict(sorted(taken.items()))


def slot_of(taken: Mapping[int, Holder], worktree: Path) -> int | None:
    """Return the slot the worktree holds, if any."""
    return next((slot for slot, holder in taken.items() if holder.worktree == str(worktree)), None)


def describe(taken: Mapping[int, Holder]) -> list[str]:
    """Return a line for each slot taken: its number, its worktree, when it was taken."""
    gone = " — its worktree no longer exists"
    return [
        f"slot {slot}: {holder.worktree} (taken {holder.taken}){gone if holder.abandoned() else ''}"
        for slot, holder in taken.items()
    ]


def claim(directory: Path, worktree: Path, count: int, remove: Remove) -> tuple[int, bool]:
    """Take a slot of 1 to N for the worktree, or find the one it holds; return it, and if new.

    The slot taken is the smallest free one, a slot whose worktree no longer exists being free.
    What a holder left in it is removed first, then the slot written, the lock held throughout: a
    slot is never said held — to this worktree, by another claim — before it is emptied, and a
    removal that fails takes nothing, so the next claim does it again.
    """
    with locked(directory):
        taken = holders(directory)
        held = slot_of(taken, worktree)
        if held is not None:
            return held, False
        free = [
            slot for slot in range(1, count + 1) if slot not in taken or taken[slot].abandoned()
        ]
        if not free:
            listed = "\n  ".join(describe(taken))
            message = f"all {count} slot(s) are taken (WATERFALL_SLOTS):\n  {listed}"
            raise RegisterError(message)
        slot = free[0]
        try:
            remove(slot)
        except RegisterError as error:
            message = (
                f"slot {slot} is not taken: what was left in it could not be removed: {error}. "
                "Run make slot again once Docker answers."
            )
            raise RegisterError(message) from error
        stamp = datetime.now(UTC).isoformat(timespec="seconds")
        written = directory / f".{slot}.new"
        written.write_text(f"{worktree}\n{stamp}\n", encoding="utf-8")
        written.replace(directory / str(slot))
    return slot, True


def release(directory: Path, worktree: Path, remove: Remove) -> int | None:
    """Remove what the slot of the worktree holds, then free it; return it, None if none was held.

    The slot is freed only once its projects are removed: if they cannot be, it stays taken. The
    lock is held throughout, as ``claim`` holds it: no claim of this worktree answers in between.
    """
    with locked(directory):
        slot = slot_of(holders(directory), worktree)
        if slot is None:
            return None
        remove(slot)
        (directory / str(slot)).unlink(missing_ok=True)
    return slot


def slot_here(environment: Mapping[str, str], worktree: Worktree | None) -> int:
    """Return the slot of the worktree: 0 for the main repository, or outside one."""
    if worktree is None or worktree.main:
        return 0
    slot = slot_of(holders(register(environment)), worktree.path)
    if slot is None:
        message = f"this worktree has no slot: run make slot ({worktree.path})"
        raise RegisterError(message)
    return slot


def compose_remover(environment: Mapping[str, str], directory: Path) -> Remove:
    """Return what removes the projects of a slot by ``docker compose -p <project> down``.

    By the name of the project alone, from the register, where no Compose file lies: what is
    removed is what Docker labels with the project, whatever worktree started it. Without Docker,
    nothing was started. A ``down`` that has not ended after ``REMOVE_SECONDS`` fails: the lock of
    the register is held while it runs.
    """
    clean = {name: value for name, value in environment.items() if name not in COMPOSE_SETTINGS}

    def remove(slot: int) -> None:
        for project in (
            names(slot)["WATERFALL_SERVICE_PROJECT"],
            names(slot)["WATERFALL_TEST_PROJECT"],
        ):
            command = ["docker", "compose", "-p", project, "down", "--volumes"]
            try:
                done = subprocess.run(
                    command,
                    cwd=directory,
                    env=clean,
                    stdout=sys.stderr,
                    check=False,
                    timeout=REMOVE_SECONDS,
                )
            except FileNotFoundError:
                return
            except subprocess.TimeoutExpired as expired:
                message = f"{' '.join(command)} did not end within {REMOVE_SECONDS} s"
                raise RegisterError(message) from expired
            if done.returncode:
                message = f"{' '.join(command)} failed with code {done.returncode}"
                raise RegisterError(message)

    return remove


def take(environment: Mapping[str, str]) -> int:
    """``claim``: take a slot for the current worktree, and say which."""
    worktree = current_worktree()
    if worktree is None or worktree.main:
        print("slot 0: the main repository is at slot 0; make slot is for a worktree of a lot")
        return 0
    count = slot_count(environment)
    directory = register(environment)
    slot, new = claim(directory, worktree.path, count, compose_remover(environment, directory))
    first = block(slot)
    held = "taken" if new else "already held"
    print(f"slot {slot} {held}: {worktree.path} (ports {first} to {first + BLOCK_SIZE - 1})")
    return 0


def give_back(environment: Mapping[str, str]) -> int:
    """``release``: remove what the slot of the current worktree holds, then free it."""
    worktree = current_worktree()
    if worktree is None or worktree.main:
        print("slot 0: the main repository keeps slot 0, which is never released")
        return 0
    directory = register(environment)
    slot = release(directory, worktree.path, compose_remover(environment, directory))
    if slot is None:
        print(f"this worktree holds no slot: {worktree.path}")
    else:
        print(f"slot {slot} released: {worktree.path}")
    return 0


def list_slots(environment: Mapping[str, str]) -> int:
    """``list``: print N, then each slot taken on the workstation and its worktree."""
    print(f"WATERFALL_SLOTS={slot_count(environment)}")
    taken = holders(register(environment))
    print("\n".join(describe(taken)) if taken else "no slot taken")
    return 0


def which(environment: Mapping[str, str], *, listed: bool) -> int:
    """``which``: print the slot of the current worktree, or its variables for the Makefile."""
    slot = slot_here(environment, current_worktree())
    if listed:
        print("\n".join(f"{name}={value}" for name, value in variables(slot).items()))
    else:
        print(slot)
    return 0


def parser() -> argparse.ArgumentParser:
    """Return the parser of the sub-commands."""
    main = argparse.ArgumentParser(prog="slots.py", description=(__doc__ or "").splitlines()[0])
    commands = main.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="run a command once a slot is free")
    run.add_argument("--heavy", action="store_true", required=True, help="a heavy run")
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- <command…>")
    commands.add_parser("processors", help="print the share of the processors of one heavy run")
    commands.add_parser("claim", help="take a slot for this worktree, or say the one it holds")
    commands.add_parser("release", help="remove what the slot of this worktree holds, free it")
    commands.add_parser("list", help="print N and the slots taken on the workstation")
    current = commands.add_parser("which", help="print the slot of this worktree, 0 for the main")
    current.add_argument(
        "--variables", action="store_true", help="print its ports and names, NAME=value"
    )
    return main


def run_action(options: argparse.Namespace, environment: Mapping[str, str]) -> int:
    """Run the sub-command the options name; return its code."""
    actions: dict[str, Callable[[Mapping[str, str]], int]] = {
        "claim": take,
        "release": give_back,
        "list": list_slots,
    }
    if options.action in actions:
        return actions[options.action](environment)
    if options.action == "which":
        return which(environment, listed=options.variables)
    if options.action == "processors":
        print(processor_share(slot_count(environment)))
        return 0
    command = options.command[1:] if options.command[:1] == ["--"] else options.command
    if not command:
        print("slots: run --heavy needs a command after --", file=sys.stderr)
        return 2
    return run_heavy(command, environment)


def main(
    arguments: Sequence[str] | None = None, environment: Mapping[str, str] | None = None
) -> int:
    """Run a sub-command; return the exit code: 1 for a slot refused, 2 for a setting."""
    environment = os.environ if environment is None else environment
    options = parser().parse_args(arguments)
    try:
        return run_action(options, environment)
    except RegisterError as error:
        print(f"slots: {error}", file=sys.stderr)
        return 1
    except SlotsError as error:
        print(f"slots: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"slots: the register or a command cannot be used: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
