# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exclusive mode of the slots: a measure takes the workstation for itself alone (US-2210).

The tool is run as the Makefile runs it, ``python3 slots.py run --exclusive -- <command>``, with
``XDG_RUNTIME_DIR`` on a temporary directory: no test touches the locks of the workstation.
"""

import fcntl
import os
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest
from test_slots import HANDSHAKE, SLOTS, plan, wait_for

from wftools import slots

if TYPE_CHECKING:
    from pathlib import Path


def start(
    directory: Path, mode: str, command: list[str], slot_count: str = "2"
) -> subprocess.Popen[str]:
    """Start the tool in a mode on a command, its locks in the directory."""
    environment = {**os.environ, "XDG_RUNTIME_DIR": str(directory), "WATERFALL_SLOTS": slot_count}
    return subprocess.Popen(
        [sys.executable, str(SLOTS), "run", mode, "--", *command],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def handshake(directory: Path, name: str) -> list[str]:
    """Return the command that writes its start, waits for the file "go", then writes its end."""
    return [sys.executable, "-c", HANDSHAKE, str(directory), name]


def moment(directory: Path, name: str) -> int:
    return int((directory / name).read_text())


def every_lock(directory: Path) -> list[Path]:
    """Return the gate of the exclusive runs, then the nine lock files of the heavy runs."""
    environment = {"XDG_RUNTIME_DIR": str(directory)}
    return [slots.gate_path(environment), *slots.lock_paths(environment, slots.MAX_SLOTS)]


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
            time.sleep(2.5)
            assert run.poll() is None
            assert not marker.exists(), "the measure does not start before the heavy run ends"
        except BaseException:
            finish(run)
            raise
    _, error = run.communicate(timeout=60)
    assert run.returncode == 0
    assert marker.exists()
    assert error.count("in progress") == 1


def test_a_heavy_run_started_during_an_exclusive_run_waits_for_its_end(tmp_path: Path) -> None:
    """US-2210: a measure holds back the heavy runs started while it lasts, and they say so once."""
    runs = [start(tmp_path, "--exclusive", handshake(tmp_path, "x"))]
    try:
        wait_for(tmp_path / "sx")
        runs.append(start(tmp_path, "--heavy", handshake(tmp_path, "h")))
        time.sleep(2.5)
        assert not (tmp_path / "sh").exists(), "no slot of the two is free while the measure lasts"
        (tmp_path / "go").write_text("go")
        _, error = runs[1].communicate(timeout=60)
        runs[0].communicate(timeout=60)
    finally:
        (tmp_path / "go").write_text("go")
        finish(*runs)
    assert [run.returncode for run in runs] == [0, 0]
    assert moment(tmp_path, "sh") >= moment(tmp_path, "ex")
    assert error.count("exclusive run holds the workstation") == 1


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


def test_two_exclusive_runs_do_not_hold_each_other_and_pass_one_after_the_other(
    tmp_path: Path,
) -> None:
    """US-2210: two measures waiting on the same heavy run both pass, one after the other."""
    with (tmp_path / "waterfall-heavy.3.lock").open("w") as in_progress:
        fcntl.flock(in_progress, fcntl.LOCK_EX)
        runs = [start(tmp_path, "--exclusive", handshake(tmp_path, name), "3") for name in "ab"]
        time.sleep(1)
    try:
        deadline = time.monotonic() + 30
        while not list(tmp_path.glob("s?")):
            assert time.monotonic() < deadline, "no measure started once the heavy run ended"
            time.sleep(0.02)
        time.sleep(0.5)
        assert len(list(tmp_path.glob("s?"))) == 1, "the second waits while the first lasts"
        (tmp_path / "go").write_text("go")
        for run in runs:
            run.communicate(timeout=60)
    finally:
        (tmp_path / "go").write_text("go")
        finish(*runs)
    assert [run.returncode for run in runs] == [0, 0]
    first, second = sorted("ab", key=lambda name: moment(tmp_path, f"s{name}"))
    assert moment(tmp_path, f"s{second}") >= moment(tmp_path, f"e{first}")


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
            deadline = time.monotonic() + 30
            while not held(slots.gate_path({"XDG_RUNTIME_DIR": str(tmp_path)})):
                assert time.monotonic() < deadline, "the measure never took the gate"
                time.sleep(0.02)
            run.send_signal(number)
            _, error = run.communicate(timeout=60)
        finally:
            finish(run)
    assert run.returncode == code
    assert "Traceback" not in error
    assert not any(held(path) for path in every_lock(tmp_path))


def test_an_exclusive_run_interrupted_while_its_command_runs_frees_every_slot(
    tmp_path: Path,
) -> None:
    """US-2210: a measure stopped while its command runs relays the signal and frees every slot."""
    ready = tmp_path / "ready"
    script = f"import time\nopen({str(ready)!r}, 'w')\ntime.sleep(60)\n"
    run = start(tmp_path, "--exclusive", [sys.executable, "-c", script])
    try:
        wait_for(ready)
        run.send_signal(signal.SIGTERM)
        run.communicate(timeout=60)
    finally:
        finish(run)
    assert run.returncode == 128 + signal.SIGTERM
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
            slots.take_workstation({"XDG_RUNTIME_DIR": str(tmp_path)})
        monkeypatch.setattr(fcntl, "flock", real)
    assert not any(held(path) for path in every_lock(tmp_path))


def test_an_exclusive_run_is_given_the_whole_workstation(tmp_path: Path) -> None:
    """US-2210: the command of a measure runs on every processor, whatever N."""
    show = [sys.executable, "-c", "import os; print(os.environ['WATERFALL_PROCESSORS'])"]
    run = start(tmp_path, "--exclusive", show, "4")
    output, _ = run.communicate(timeout=60)
    assert int(output) == slots.processor_share(1)


def test_heavy_and_exclusive_together_are_refused(tmp_path: Path) -> None:
    """US-2210: a run is heavy or exclusive, never both; the command does not run."""
    marker = tmp_path / "ran"
    both = ["run", "--heavy", "--exclusive"]
    command = [sys.executable, str(SLOTS), *both, "--", "touch", str(marker)]
    done = subprocess.run(
        command,
        env={**os.environ, "XDG_RUNTIME_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2
    assert "not allowed with" in done.stderr
    assert not marker.exists()


def test_the_makefile_gives_the_exclusive_mode_to_a_target(tmp_path: Path) -> None:
    """US-2210: the variable exclusive of the Makefile runs a command in the exclusive mode."""
    probe = "probe-exclusive: ; $(exclusive) true"
    planned = plan(tmp_path, "--eval", probe, "probe-exclusive", "TESTS=tests/test_guard.py")
    assert "slots.py run --exclusive -- env true" in planned.stdout
