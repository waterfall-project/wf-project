# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exclusive mode of the slots: a measure takes the workstation for itself alone (US-2210).

The tool is run as ``python3 slots.py run --exclusive -- <command>``, the arguments the Makefile
gives it through ``launch.py slots`` (US-2450), with ``WATERFALL_RUNTIME_DIR`` on a temporary
directory: no test touches the locks of the workstation. A test waits for what it can see — a file
the command writes, a line the tool says —, never a delay.
"""

import contextlib
import fcntl
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from test_slots import HANDSHAKE, SLOTS, plan, wait_for

from wftools import heavyturns, slots

PROBE = (
    "import fcntl, json, os, sys\n"
    "def held(path):\n"
    "    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)\n"
    "    try:\n"
    "        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)\n"
    "    except BlockingIOError:\n"
    "        return True\n"
    "    finally:\n"
    "        os.close(descriptor)\n"
    "    return False\n"
    "directory = sys.argv[1]\n"
    "print(json.dumps({\n"
    "    'held': os.environ.get('WATERFALL_SLOTS_HELD'),\n"
    "    'processors': int(os.environ['WATERFALL_PROCESSORS']),\n"
    "    'gate': held(f'{directory}/waterfall-heavy.exclusive.lock'),\n"
    "    'first': held(f'{directory}/waterfall-heavy.lock'),\n"
    "    'database': os.environ.get('WATERFALL_TEST_DATABASE_URL'),\n"
    "}))\n"
)
"""A command that prints what it is given, and whether the gate and the first turn are held."""


def start(
    directory: Path,
    mode: str,
    command: list[str],
    slot_count: str = "2",
    *,
    name: str = "run",
    **extra: str,
) -> subprocess.Popen[str]:
    """Start the tool in a mode on a command, its locks in the directory, its words in <name>.err.

    The mode is one option or several, split on spaces; the variables named are added.
    """
    environment = {
        **os.environ,
        "WATERFALL_RUNTIME_DIR": str(directory),
        "WATERFALL_SLOTS": slot_count,
    }
    environment.pop(heavyturns.HELD_VARIABLE, None)
    with (directory / f"{name}.err").open("w") as error:
        return subprocess.Popen(
            [sys.executable, str(SLOTS), "run", *mode.split(), "--", *command],
            env=environment | extra,
            stdout=subprocess.PIPE,
            stderr=error,
            text=True,
            start_new_session=True,
        )


def said(directory: Path, name: str) -> str:
    """Return what the tool started under the name has said so far."""
    return (directory / f"{name}.err").read_text()


def wait_until_said(directory: Path, name: str, words: str) -> None:
    """Wait until the tool started under the name says the words."""
    deadline = time.monotonic() + 60
    while words not in said(directory, name):
        assert time.monotonic() < deadline, f"{name} never said {words!r}"
        time.sleep(0.02)


def probe(directory: Path) -> list[str]:
    """Return the command that prints what it is given, the locks of the directory looked at."""
    return [sys.executable, "-c", PROBE, str(directory)]


def handshake(directory: Path, name: str) -> list[str]:
    """Return the command that writes its start, waits for the file "go", then writes its end."""
    return [sys.executable, "-c", HANDSHAKE, str(directory), name]


def moment(directory: Path, name: str) -> int:
    return int((directory / name).read_text())


def every_lock(directory: Path) -> list[Path]:
    """Return the gate of the exclusive runs, then the nine lock files of the heavy runs."""
    environment = {"WATERFALL_RUNTIME_DIR": str(directory)}
    paths = heavyturns.lock_paths(environment, heavyturns.MAX_SLOTS)
    return [heavyturns.gate_path(environment), *paths]


def held(path: Path) -> bool:
    """Whether another holds the lock file: an exclusive lock that does not wait is refused."""
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(descriptor)
    return False


def opened_by(pid: int) -> set[Path]:
    """Return the files the process has open, as its descriptors in ``/proc`` name them."""
    opened: set[Path] = set()
    try:
        for descriptor in Path("/proc", str(pid), "fd").iterdir():
            with contextlib.suppress(OSError):
                opened.add(descriptor.readlink())
    except OSError:
        pass  # gone already
    return opened


def finish(*runs: subprocess.Popen[str]) -> None:
    """Kill what a failed test leaves running, the group of each tool with its command."""
    for run in runs:
        if run.poll() is None:
            os.killpg(run.pid, signal.SIGKILL)
        run.communicate()


def test_an_exclusive_run_waits_for_the_heavy_runs_in_progress_saying_so_once(
    tmp_path: Path,
) -> None:
    """US-2210: a measure waits for the end of the heavy runs in progress, and says so once."""
    marker = tmp_path / "ran"
    with (tmp_path / "waterfall-heavy.2.lock").open("w") as in_progress:
        fcntl.flock(in_progress, fcntl.LOCK_EX)
        run = start(tmp_path, "--exclusive", [sys.executable, "-c", f"open({str(marker)!r}, 'w')"])
        try:
            wait_until_said(tmp_path, "run", "in progress")
            assert run.poll() is None
            assert not marker.exists(), "the measure does not start before the heavy run ends"
        except BaseException:
            finish(run)
            raise
    run.communicate(timeout=60)
    assert run.returncode == 0
    assert marker.exists()
    assert said(tmp_path, "run").count("in progress") == 1


def test_a_heavy_run_started_during_an_exclusive_run_waits_for_its_end(tmp_path: Path) -> None:
    """US-2210: a measure holds back the heavy runs started while it lasts, and they say so once."""
    runs = [start(tmp_path, "--exclusive", handshake(tmp_path, "x"), name="x")]
    try:
        wait_for(tmp_path / "sx")
        runs.append(start(tmp_path, "--heavy", handshake(tmp_path, "h"), name="h"))
        wait_until_said(tmp_path, "h", "exclusive run holds the workstation")
        assert not (tmp_path / "sh").exists(), "no slot of the two is free while the measure lasts"
        (tmp_path / "go").write_text("go")
        for run in runs:
            run.communicate(timeout=60)
    finally:
        (tmp_path / "go").write_text("go")
        finish(*runs)
    assert [run.returncode for run in runs] == [0, 0]
    assert moment(tmp_path, "sh") >= moment(tmp_path, "ex")
    assert said(tmp_path, "h").count("exclusive run holds the workstation") == 1


def test_an_exclusive_run_says_nothing_of_a_gate_a_heavy_run_shares_a_moment(
    tmp_path: Path,
) -> None:
    """US-2210: a heavy run shares the gate while it looks for a turn; the measure keeps silent."""
    gate = heavyturns.gate_path({"WATERFALL_RUNTIME_DIR": str(tmp_path)})
    with gate.open("w") as shared:
        fcntl.flock(shared, fcntl.LOCK_SH)
        run = start(tmp_path, "--exclusive", handshake(tmp_path, "x"))
        try:
            # The measure has the gate open: it is trying for it while the heavy run shares it.
            deadline = time.monotonic() + 60
            while gate.resolve() not in opened_by(run.pid):
                assert time.monotonic() < deadline, "the measure never opened the gate"
                time.sleep(0.02)
            assert not (tmp_path / "sx").exists()
        except BaseException:
            finish(run)
            raise
    try:
        (tmp_path / "go").write_text("go")
        run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 0
    assert not said(tmp_path, "run")


def test_an_exclusive_run_holds_every_slot_whatever_its_n_then_frees_them(tmp_path: Path) -> None:
    """US-2210: at N = 1 a measure holds the nine slots, so a deliverer whose N is larger waits."""
    run = start(tmp_path, "--exclusive", handshake(tmp_path, "x"), "1")
    try:
        wait_for(tmp_path / "sx")
        assert all(held(path) for path in every_lock(tmp_path))
        (tmp_path / "go").write_text("go")
        run.communicate(timeout=60)
    finally:
        (tmp_path / "go").write_text("go")
        finish(run)
    assert run.returncode == 0
    assert not any(held(path) for path in every_lock(tmp_path))


@pytest.mark.parametrize(("first_n", "second_n"), [("3", "3"), ("1", "9")])
def test_two_exclusive_runs_do_not_hold_each_other_and_pass_one_after_the_other(
    tmp_path: Path, first_n: str, second_n: str
) -> None:
    """US-2210: two measures, at one N or two, both wait on a heavy run, then pass in turn.

    One holds the gate and waits for the heavy run, the other waits for the gate: each says so.
    """
    with (tmp_path / "waterfall-heavy.3.lock").open("w") as in_progress:
        fcntl.flock(in_progress, fcntl.LOCK_EX)
        runs = [
            start(tmp_path, "--exclusive", handshake(tmp_path, name), count, name=name)
            for name, count in (("a", first_n), ("b", second_n))
        ]
        try:
            deadline = time.monotonic() + 60
            while not any("in progress" in said(tmp_path, name) for name in "ab"):
                assert time.monotonic() < deadline, "no measure waits for the heavy run"
                time.sleep(0.02)
            holder, other = ("a", "b") if "in progress" in said(tmp_path, "a") else ("b", "a")
            wait_until_said(tmp_path, other, "Another exclusive run holds the workstation")
            assert "in progress" not in said(tmp_path, other), "the other waits for the gate"
            assert not list(tmp_path.glob("s?")), "neither starts while the heavy run lasts"
        except BaseException:
            finish(*runs)
            raise
    try:
        (tmp_path / "go").write_text("go")
        for run in runs:
            run.communicate(timeout=60)
    finally:
        finish(*runs)
    assert [run.returncode for run in runs] == [0, 0]
    assert moment(tmp_path, f"s{other}") >= moment(tmp_path, f"e{holder}")


@pytest.mark.parametrize(
    ("number", "code"), [(signal.SIGINT, 128 + signal.SIGINT), (signal.SIGTERM, -signal.SIGTERM)]
)
def test_an_exclusive_run_interrupted_while_it_waits_frees_what_it_took(
    tmp_path: Path, number: int, code: int
) -> None:
    """US-2210: interrupted while it waits, a measure frees the gate and the slots it took."""
    with (tmp_path / "waterfall-heavy.3.lock").open("w") as in_progress:
        fcntl.flock(in_progress, fcntl.LOCK_EX)
        run = start(tmp_path, "--exclusive", [sys.executable, "-c", "pass"], "1")
        try:
            wait_until_said(tmp_path, "run", "in progress")
            run.send_signal(number)
            run.communicate(timeout=60)
        finally:
            finish(run)
    assert run.returncode == code
    assert "Traceback" not in said(tmp_path, "run")
    assert not any(held(path) for path in every_lock(tmp_path))


@pytest.mark.parametrize("number", [signal.SIGINT, signal.SIGTERM])
def test_an_exclusive_run_interrupted_while_its_command_runs_frees_every_slot(
    tmp_path: Path, number: int
) -> None:
    """US-2210: a measure stopped while its command runs relays the signal and frees every slot."""
    ready = tmp_path / "ready"
    script = f"import time\nopen({str(ready)!r}, 'w')\ntime.sleep(60)\n"
    run = start(tmp_path, "--exclusive", [sys.executable, "-c", script])
    try:
        wait_for(ready)
        run.send_signal(number)
        run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 128 + number
    assert not any(held(path) for path in every_lock(tmp_path))


def test_an_exception_while_the_workstation_is_taken_frees_what_was_taken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """US-2210: an exception in the wait for a slot closes the gate and the slots already taken."""
    real = fcntl.flock

    def interrupted(descriptor: int, operation: int) -> None:
        if operation == fcntl.LOCK_EX:
            raise KeyboardInterrupt
        real(descriptor, operation)

    with (tmp_path / "waterfall-heavy.2.lock").open("w") as in_progress:
        fcntl.flock(in_progress, fcntl.LOCK_EX)
        monkeypatch.setattr(fcntl, "flock", interrupted)
        with pytest.raises(KeyboardInterrupt):
            heavyturns.take_workstation({"WATERFALL_RUNTIME_DIR": str(tmp_path)})
        monkeypatch.setattr(fcntl, "flock", real)
    assert not any(held(path) for path in every_lock(tmp_path))


def test_an_exclusive_run_is_given_the_whole_workstation(tmp_path: Path) -> None:
    """US-2210: the command of a measure runs on every processor, whatever N."""
    run = start(tmp_path, "--exclusive", probe(tmp_path), "4")
    output, _ = run.communicate(timeout=60)
    assert json.loads(output)["processors"] == slots.processor_share(1)


@pytest.mark.parametrize("inner", ["--heavy", "--exclusive"])
def test_a_run_started_by_the_command_of_an_exclusive_run_takes_no_turn(
    tmp_path: Path, inner: str
) -> None:
    """US-2210: a make behind $(heavy) inside a measure does not wait for its parent's turns.

    It would wait forever: the turns are the measure's. It says so, and runs on the workstation.
    """
    nested = [sys.executable, str(SLOTS), "run", inner, "--", *probe(tmp_path)]
    run = start(tmp_path, "--exclusive", nested, "4")
    try:
        output, _ = run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 0
    given = json.loads(output)
    assert given["held"].startswith(f"{heavyturns.HELD_EXCLUSIVE}:")
    assert given["gate"]
    assert given["processors"] == slots.processor_share(1)
    assert "above this one holds the workstation; no turn to take" in said(tmp_path, "run")


def test_the_mark_of_an_exclusive_run_is_not_believed_once_the_gate_is_free(tmp_path: Path) -> None:
    """US-2210: a mark that outlived its measure is dropped: the run takes a turn, says nothing.

    Its command is not given the mark: the mark goes no further than the measure.
    """
    stale = {heavyturns.HELD_VARIABLE: heavyturns.HELD_EXCLUSIVE}
    run = start(tmp_path, "--heavy", probe(tmp_path), "2", **stale)
    try:
        output, _ = run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 0
    given = json.loads(output)
    assert given["held"] is None
    assert given["first"], "the run holds the first turn"
    assert not given["gate"]
    assert given["processors"] == slots.processor_share(2)
    assert "above this one" not in said(tmp_path, "run")


def test_an_exclusive_run_with_services_holds_the_workstation_and_has_them(tmp_path: Path) -> None:
    """US-2210: --exclusive goes with --services as --heavy does; a service given is not started."""
    given_url = "postgresql://postgres@127.0.0.1:1/given"
    extra = {"WATERFALL_TEST_DATABASE_URL": given_url}
    run = start(tmp_path, "--exclusive --services db", probe(tmp_path), **extra)
    try:
        output, _ = run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 0
    given = json.loads(output)
    assert given["database"] == given_url
    assert given["gate"]
    assert given["first"]
    assert given["held"].startswith(f"{heavyturns.HELD_EXCLUSIVE}:")


def test_heavy_and_exclusive_together_are_refused(tmp_path: Path) -> None:
    """US-2210: a run is heavy or exclusive, never both; the command does not run."""
    marker = tmp_path / "ran"
    both = ["run", "--heavy", "--exclusive"]
    command = [sys.executable, str(SLOTS), *both, "--", "touch", str(marker)]
    done = subprocess.run(
        command,
        env={**os.environ, "WATERFALL_RUNTIME_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2
    assert "not allowed with" in done.stderr
    assert not marker.exists()


def test_the_makefile_gives_the_exclusive_mode_to_a_target(tmp_path: Path) -> None:
    """US-2210: the variable exclusive of the Makefile runs a command in the exclusive mode."""
    rule = "probe-exclusive: ; $(exclusive) true"
    planned = plan(tmp_path, "--eval", rule, "probe-exclusive", "TESTS=tests/test_guard.py")
    assert "launch.py slots run --exclusive -- env true" in planned.stdout


def hold_gate(directory: Path, token: str) -> int:
    """Hold the gate as another exclusive run does, its token in the file; return the descriptor."""
    environment = {"WATERFALL_RUNTIME_DIR": str(directory)}
    descriptor = heavyturns.open_lock(heavyturns.gate_path(environment))
    fcntl.flock(descriptor, fcntl.LOCK_EX)
    os.pwrite(descriptor, token.encode(), 0)
    return descriptor


def test_a_mark_with_the_token_of_another_exclusive_run_takes_its_turn(tmp_path: Path) -> None:
    """US-2460 (#3343): a mark of a measure gone, the gate held by another, waits for its turn."""
    other = hold_gate(tmp_path, "200:2")
    stale = {heavyturns.HELD_VARIABLE: f"{heavyturns.HELD_EXCLUSIVE}:100:1"}
    run = start(tmp_path, "--heavy", probe(tmp_path), "2", **stale)
    try:
        wait_until_said(tmp_path, "run", "An exclusive run holds the workstation; waiting")
        assert "above this one" not in said(tmp_path, "run")
        assert run.poll() is None
        os.close(other)
        output, _ = run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 0
    assert json.loads(output)["first"], "the run took a turn"


def test_a_mark_with_the_token_of_the_gate_is_believed(tmp_path: Path) -> None:
    """US-2460 (#3343): the token the gate bears is the mark's: no turn to take."""
    holder = hold_gate(tmp_path, "100:1")
    environment = {
        "WATERFALL_RUNTIME_DIR": str(tmp_path),
        heavyturns.HELD_VARIABLE: f"{heavyturns.HELD_EXCLUSIVE}:100:1",
    }
    try:
        assert heavyturns.held_above(environment)
    finally:
        os.close(holder)
    assert not heavyturns.held_above(environment), "the gate is free: the mark is dropped"


def test_a_mark_without_a_token_is_believed_while_the_gate_is_held(tmp_path: Path) -> None:
    """US-2460 (#3343): the mark of a tool that predates the token is believed as before."""
    holder = hold_gate(tmp_path, "100:1")
    environment = {
        "WATERFALL_RUNTIME_DIR": str(tmp_path),
        heavyturns.HELD_VARIABLE: heavyturns.HELD_EXCLUSIVE,
    }
    try:
        assert heavyturns.held_above(environment)
    finally:
        os.close(holder)


def test_a_mark_with_an_empty_token_is_not_believed(tmp_path: Path) -> None:
    """US-2460 (#3343): `exclusive:` alone must not equal an empty gate file."""
    holder = heavyturns.open_lock(heavyturns.gate_path({"WATERFALL_RUNTIME_DIR": str(tmp_path)}))
    fcntl.flock(holder, fcntl.LOCK_EX)
    environment = {
        "WATERFALL_RUNTIME_DIR": str(tmp_path),
        heavyturns.HELD_VARIABLE: f"{heavyturns.HELD_EXCLUSIVE}:",
    }
    try:
        assert not heavyturns.held_above(environment)
    finally:
        os.close(holder)


def test_a_gate_with_bytes_that_are_not_text_does_not_raise(tmp_path: Path) -> None:
    """US-2460 (#3343): invalid UTF-8 in the gate file is a token that differs, not an error."""
    holder = hold_gate(tmp_path, "100:1")
    os.ftruncate(holder, 0)
    os.pwrite(holder, b"\xff\xfe", 0)
    environment = {
        "WATERFALL_RUNTIME_DIR": str(tmp_path),
        heavyturns.HELD_VARIABLE: f"{heavyturns.HELD_EXCLUSIVE}:100:1",
    }
    try:
        assert not heavyturns.held_above(environment)
    finally:
        os.close(holder)


def test_the_token_is_in_the_gate_while_the_exclusive_run_waits_for_the_turns(
    tmp_path: Path,
) -> None:
    """US-2460 (#3343): a survivor of the measure before is not believed during the wait."""
    environment = {"WATERFALL_RUNTIME_DIR": str(tmp_path)}
    previous = hold_gate(tmp_path, "100:1")
    os.close(previous)
    survivor = {**environment, heavyturns.HELD_VARIABLE: f"{heavyturns.HELD_EXCLUSIVE}:100:1"}
    turn = heavyturns.open_lock(heavyturns.lock_paths(environment, 1)[0])
    fcntl.flock(turn, fcntl.LOCK_EX)

    def take_then_free() -> None:
        for descriptor in heavyturns.take_workstation(environment)[0]:
            os.close(descriptor)

    taking = threading.Thread(target=take_then_free, daemon=True)
    taking.start()
    try:
        deadline = time.monotonic() + 30
        gate = heavyturns.gate_path(environment)
        while gate.read_bytes() in {b"", b"100:1"} and time.monotonic() < deadline:
            time.sleep(0.05)
        assert gate.read_bytes() not in {b"", b"100:1"}, "the gate bears the token of the new run"
        assert taking.is_alive(), "the run still waits for the turn"
        assert not heavyturns.held_above(survivor)
    finally:
        os.close(turn)
        taking.join(timeout=30)
