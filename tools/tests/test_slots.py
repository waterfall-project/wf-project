# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The admission of the heavy runs: N at a time, on a share of the processors (US-1090).

The tool is run as the Makefile runs it, ``python3 slots.py run --heavy -- <command>``, with
``XDG_RUNTIME_DIR`` on a temporary directory: no test touches the locks of the workstation.
"""

import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from wftools import REPOSITORY, slots

SLOTS = REPOSITORY / "tools" / "src" / "wftools" / "slots.py"
PAUSE = (
    "import sys, time; open(sys.argv[1], 'w').write(str(time.time())); time.sleep(1.5); "
    "open(sys.argv[2], 'w').write(str(time.time()))"
)


def start(
    directory: Path, command: list[str], slot_count: str | None = "1"
) -> subprocess.Popen[str]:
    """Start the tool on a command, its locks in the directory."""
    environment = {**os.environ, "XDG_RUNTIME_DIR": str(directory)}
    environment.pop("WATERFALL_SLOTS", None)
    if slot_count is not None:
        environment["WATERFALL_SLOTS"] = slot_count
    return subprocess.Popen(
        [sys.executable, str(SLOTS), "run", "--heavy", "--", *command],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for(path: Path) -> None:
    deadline = time.monotonic() + 10
    while not path.exists():
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.02)


def test_two_of_three_heavy_runs_pass_together_at_two_slots(tmp_path: Path) -> None:
    """US-1090: with N = 2, three heavy runs: two pass together, the third waits for one to end."""
    runs = [
        start(
            tmp_path,
            [sys.executable, "-c", PAUSE, str(tmp_path / f"s{i}"), str(tmp_path / f"e{i}")],
            "2",
        )
        for i in range(3)
    ]
    for run in runs:
        run.communicate(timeout=30)
        assert run.returncode == 0
    starts = sorted(float((tmp_path / f"s{i}").read_text()) for i in range(3))
    ends = sorted(float((tmp_path / f"e{i}").read_text()) for i in range(3))
    assert starts[1] < ends[0], "two runs pass together"
    assert starts[2] >= ends[0], "the third waits for one of them to end"


def test_the_first_slot_is_the_lock_of_before(tmp_path: Path) -> None:
    """US-1090: at N = 1 the slot is waterfall-heavy.lock: a run waits while it is held."""
    with (tmp_path / "waterfall-heavy.lock").open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        run = start(tmp_path, [sys.executable, "-c", "print('ran')"], None)
        time.sleep(0.5)
        assert run.poll() is None
        run.terminate()
        _, error = run.communicate(timeout=10)
        assert "taken" in error
    assert not (tmp_path / "waterfall-heavy.2.lock").exists()


def test_the_wait_is_said_once(tmp_path: Path) -> None:
    """US-1090: all slots taken, the tool says so once, then tries again."""
    with (tmp_path / "waterfall-heavy.lock").open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        run = start(tmp_path, [sys.executable, "-c", "print('ran')"])
        time.sleep(2.5)
        run.terminate()
        _, error = run.communicate(timeout=10)
    assert error.count("taken") == 1


@pytest.mark.parametrize("value", ["0", "10", "two", "", "-1", "1.5", "٣"])
def test_slots_other_than_one_to_nine_are_refused(tmp_path: Path, value: str) -> None:
    """US-1090: a WATERFALL_SLOTS that is not an integer from 1 to 9 is refused, and said."""
    marker = tmp_path / "ran"
    run = start(tmp_path, [sys.executable, "-c", f"open({str(marker)!r}, 'w')"], value)
    _, error = run.communicate(timeout=10)
    assert run.returncode == 2
    assert "WATERFALL_SLOTS" in error
    assert not marker.exists()


@pytest.mark.parametrize("value", [None, "1", "9"])
def test_slots_one_to_nine_and_absent_are_accepted(value: str | None) -> None:
    """US-1090: absent, WATERFALL_SLOTS is 1; 1 to 9 are accepted."""
    expected = 1 if value is None else int(value)
    assert slots.slot_count({} if value is None else {"WATERFALL_SLOTS": value}) == expected


def test_the_locks_are_numbered_from_the_first_of_before(tmp_path: Path) -> None:
    """US-1090: waterfall-heavy.lock, then waterfall-heavy.2.lock to waterfall-heavy.<N>.lock."""
    names = [path.name for path in slots.lock_paths({"XDG_RUNTIME_DIR": str(tmp_path)}, 3)]
    assert names == ["waterfall-heavy.lock", "waterfall-heavy.2.lock", "waterfall-heavy.3.lock"]
    assert slots.lock_paths({}, 1) == [Path(os.sep, "tmp", "waterfall-heavy.lock")]


def test_a_process_left_behind_does_not_keep_the_slot(tmp_path: Path) -> None:
    """US-1090: a server the command left behind does not hold the slot after the command ends."""
    run = start(tmp_path, ["sh", "-c", "sleep 30 >/dev/null 2>&1 & echo $!"])
    output, _ = run.communicate(timeout=10)
    orphan = int(output.strip())
    try:
        with (tmp_path / "waterfall-heavy.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.kill(orphan, signal.SIGKILL)


def test_the_signals_reach_the_command_and_its_code_is_returned(tmp_path: Path) -> None:
    """US-1090: a signal the tool receives is relayed; the code of the command is returned."""
    ready = tmp_path / "ready"
    script = (
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, lambda *_: sys.exit(7))\n"
        f"open({str(ready)!r}, 'w')\n"
        "time.sleep(30)\n"
    )
    run = start(tmp_path, [sys.executable, "-c", script])
    wait_for(ready)
    run.send_signal(signal.SIGTERM)
    run.communicate(timeout=10)
    assert run.returncode == 7


def test_a_command_killed_by_a_signal_returns_128_plus_it(tmp_path: Path) -> None:
    run = start(tmp_path, ["sh", "-c", "kill -KILL $$"])
    run.communicate(timeout=10)
    assert run.returncode == 128 + signal.SIGKILL


def test_a_missing_command_returns_127(tmp_path: Path) -> None:
    run = start(tmp_path, ["no-such-command-for-slots"])
    _, error = run.communicate(timeout=10)
    assert run.returncode == 127
    assert "no-such-command-for-slots" in error


def test_the_command_gets_its_share_of_the_processors(tmp_path: Path) -> None:
    """US-1090: the command runs with WATERFALL_PROCESSORS, the processors divided by N."""
    run = start(
        tmp_path,
        [sys.executable, "-c", "import os; print(os.environ['WATERFALL_PROCESSORS'])"],
        "2",
    )
    output, _ = run.communicate(timeout=10)
    assert int(output) == max(1, len(os.sched_getaffinity(0)) // 2)


def test_the_share_of_the_processors_is_at_least_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """US-1090: the share is the processors divided by N, at least 1."""

    def four(_pid: int) -> set[int]:
        return {0, 1, 2, 3}

    monkeypatch.setattr(os, "sched_getaffinity", four)
    assert [slots.processor_share(count) for count in (1, 2, 4, 9)] == [4, 2, 1, 1]


def test_the_share_is_printed_for_a_run_that_does_not_wait() -> None:
    environment = {**os.environ, "WATERFALL_SLOTS": "2"}
    printed = subprocess.run(
        [sys.executable, str(SLOTS), "processors"],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert int(printed.stdout) == slots.processor_share(2)


def test_make_waits_for_a_slot_unless_a_single_file_is_selected(tmp_path: Path) -> None:
    """US-1090: test-tools is a heavy run, and a run of one file (TESTS) does not wait (#1892)."""

    def plan(*arguments: str) -> str:
        # Not the variables of the make that runs this test, TESTS among them.
        outer = ("MAKEFLAGS", "MAKELEVEL", "MFLAGS", "TESTS", "WATERFALL_PROCESSORS")
        environment = {k: v for k, v in os.environ.items() if k not in outer}
        return subprocess.run(
            ["make", "--dry-run", "test-tools", *arguments],
            cwd=REPOSITORY,
            env={**environment, "XDG_RUNTIME_DIR": str(tmp_path)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    assert "slots.py run --heavy --" in plan()
    one_file = plan("TESTS=tests/test_guard.py")
    assert "slots.py run" not in one_file
    assert one_file.rstrip().endswith("tests/test_guard.py")
