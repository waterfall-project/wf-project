# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The admission of the heavy runs: N at a time, on a share of the processors (US-1090).

The tool is run as the Makefile runs it, ``python3 slots.py run --heavy -- <command>``, with
``XDG_RUNTIME_DIR`` on a temporary directory: no test touches the locks of the workstation.
"""

import contextlib
import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from wftools import REPOSITORY, slots

SLOTS = REPOSITORY / "tools" / "src" / "wftools" / "slots.py"
# Writes its start, waits for the file "go" (60 s at most, never to block), writes its end.
HANDSHAKE = (
    "import os, sys, time\n"
    "directory, name = sys.argv[1], sys.argv[2]\n"
    "open(f'{directory}/s{name}', 'w').write(str(time.time_ns()))\n"
    "deadline = time.monotonic() + 60\n"
    "while not os.path.exists(f'{directory}/go') and time.monotonic() < deadline:\n"
    "    time.sleep(0.01)\n"
    "open(f'{directory}/e{name}', 'w').write(str(time.time_ns()))\n"
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
        start_new_session=True,
    )


def wait_for(path: Path) -> None:
    deadline = time.monotonic() + 60
    while not path.exists():
        assert time.monotonic() < deadline, f"{path.name} never appeared"
        time.sleep(0.02)


def test_two_of_three_heavy_runs_pass_together_at_two_slots(tmp_path: Path) -> None:
    """US-1090: with N = 2, three heavy runs: two pass together, the third waits for one to end."""
    runs = [
        start(tmp_path, [sys.executable, "-c", HANDSHAKE, str(tmp_path), str(i)], "2")
        for i in range(3)
    ]
    try:
        # Two runs started and none ended: they pass together, each waiting for "go".
        deadline = time.monotonic() + 30
        while len(list(tmp_path.glob("s?"))) < 2:
            assert time.monotonic() < deadline, "two runs never started together"
            time.sleep(0.02)
        time.sleep(0.3)
        assert len(list(tmp_path.glob("s?"))) == 2, "the third waits while two hold the slots"
        assert not list(tmp_path.glob("e?"))
        (tmp_path / "go").write_text("go")
        for run in runs:
            run.communicate(timeout=60)
            assert run.returncode == 0
    finally:
        (tmp_path / "go").write_text("go")
        for run in runs:
            if run.poll() is None:
                run.kill()
    starts = sorted(int((tmp_path / f"s{i}").read_text()) for i in range(3))
    ends = sorted(int((tmp_path / f"e{i}").read_text()) for i in range(3))
    assert starts[2] >= ends[0], "the third started once one of them had ended"


def test_the_first_slot_is_the_lock_of_before(tmp_path: Path) -> None:
    """US-1090: at N = 1 the slot is waterfall-heavy.lock: a run waits while it is held."""
    with (tmp_path / "waterfall-heavy.lock").open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        run = start(tmp_path, [sys.executable, "-c", "print('ran')"], None)
        time.sleep(0.5)
        assert run.poll() is None
        run.terminate()
        _, error = run.communicate(timeout=60)
        assert "taken" in error
    assert not (tmp_path / "waterfall-heavy.2.lock").exists()


def test_the_wait_is_said_once(tmp_path: Path) -> None:
    """US-1090: all slots taken, the tool says so once, then tries again."""
    with (tmp_path / "waterfall-heavy.lock").open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        run = start(tmp_path, [sys.executable, "-c", "print('ran')"])
        time.sleep(2.5)
        run.terminate()
        _, error = run.communicate(timeout=60)
    assert error.count("taken") == 1


@pytest.mark.parametrize("value", ["0", "10", "two", "", "-1", "1.5", "٣"])
def test_slots_other_than_one_to_nine_are_refused(tmp_path: Path, value: str) -> None:
    """US-1090: a WATERFALL_SLOTS that is not an integer from 1 to 9 is refused, and said."""
    marker = tmp_path / "ran"
    run = start(tmp_path, [sys.executable, "-c", f"open({str(marker)!r}, 'w')"], value)
    _, error = run.communicate(timeout=60)
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
    output, _ = run.communicate(timeout=60)
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
    run.communicate(timeout=60)
    assert run.returncode == 7


def test_a_command_killed_by_a_signal_returns_128_plus_it(tmp_path: Path) -> None:
    """US-1090: a command killed by a signal returns 128 plus it."""
    run = start(tmp_path, ["sh", "-c", "kill -KILL $$"])
    run.communicate(timeout=60)
    assert run.returncode == 128 + signal.SIGKILL


def test_a_missing_command_returns_127(tmp_path: Path) -> None:
    """US-1090: a command that does not exist returns 127 and is named."""
    run = start(tmp_path, ["no-such-command-for-slots"])
    _, error = run.communicate(timeout=60)
    assert run.returncode == 127
    assert "no-such-command-for-slots" in error


def test_the_command_gets_its_share_of_the_processors(tmp_path: Path) -> None:
    """US-1090: the command runs with WATERFALL_PROCESSORS, the processors divided by N."""
    run = start(
        tmp_path,
        [sys.executable, "-c", "import os; print(os.environ['WATERFALL_PROCESSORS'])"],
        "2",
    )
    output, _ = run.communicate(timeout=60)
    assert int(output) == max(1, len(os.sched_getaffinity(0)) // 2)


def test_the_share_of_the_processors_is_at_least_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """US-1090: the share is the processors divided by N, at least 1."""

    def four(_pid: int) -> set[int]:
        return {0, 1, 2, 3}

    monkeypatch.setattr(os, "sched_getaffinity", four)
    assert [slots.processor_share(count) for count in (1, 2, 4, 9)] == [4, 2, 1, 1]


def test_the_share_is_printed_for_a_run_that_does_not_wait() -> None:
    """US-1090: processors prints the share, for a run that does not wait."""
    environment = {**os.environ, "WATERFALL_SLOTS": "2"}
    printed = subprocess.run(
        [sys.executable, str(SLOTS), "processors"],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert int(printed.stdout) == slots.processor_share(2)


def test_a_signal_before_the_child_exists_is_relayed_to_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """US-1090: a SIGTERM that comes before the child exists is kept, then relayed to it."""
    real = subprocess.Popen

    def popen_after_signal(command: list[str], **options: Any) -> subprocess.Popen[Any]:
        signal.raise_signal(signal.SIGTERM)
        return real(command, **options)

    monkeypatch.setattr(subprocess, "Popen", popen_after_signal)
    sleeping = [sys.executable, "-c", "import time; time.sleep(60)"]
    code = slots.run_command(sleeping, dict(os.environ))
    assert code == 128 + signal.SIGTERM


def test_a_sigint_sent_to_the_tool_alone_reaches_the_child(tmp_path: Path) -> None:
    """US-1090: the tool relays every signal, SIGINT included; the child frees the slot."""
    ready = tmp_path / "ready"
    script = f"import time\nopen({str(ready)!r}, 'w')\ntime.sleep(60)\n"
    run = start(tmp_path, [sys.executable, "-c", script])
    try:
        wait_for(ready)
        run.send_signal(signal.SIGINT)
        run.communicate(timeout=60)
    finally:
        # A relay that regressed would leave the tool and its child: the group of the tool, which
        # the session of the start made, is killed whole, so neither outlives the test.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(run.pid, signal.SIGKILL)
        run.communicate()
    # An unhandled KeyboardInterrupt ends the child by SIGINT itself: the tool returns 128 plus it.
    assert run.returncode == 128 + signal.SIGINT, "the child died of the SIGINT it was relayed"


HEAVY_TARGETS = {
    "test-tools": True,
    "test-back": True,
    "coverage-back": False,
    "test-front": True,
    "coverage-front": False,
    "build-front": False,
    "e2e": True,
    "e2e-measure": False,
}
SERVICES_TARGETS = {"test-back", "coverage-back", "test-front", "coverage-front"}
"""The targets that also start the test services (US-1110), whether they wait for a slot or not."""


def plan(
    tmp_path: Path, *arguments: str, extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Return the dry run of make, free of the variables of the make that runs this test.

    The ports and names of a slot are given, those of slot 0: the plan is the same in a worktree
    of a lot that holds no slot (US-1100).
    """
    outer = ("MAKEFLAGS", "MAKELEVEL", "MFLAGS", "TESTS", "WATERFALL_PROCESSORS", "WATERFALL_SLOTS")
    environment = {k: v for k, v in os.environ.items() if k not in outer}
    environment |= slots.variables(0) | (extra or {})
    return subprocess.run(
        ["make", "--dry-run", *arguments],
        cwd=REPOSITORY,
        env={**environment, "XDG_RUNTIME_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("target", list(HEAVY_TARGETS))
def test_make_waits_for_a_slot_unless_a_single_file_is_selected(
    tmp_path: Path, target: str
) -> None:
    """US-1090: a heavy run waits for a slot, and a run of one file (TESTS) does not (#1892)."""
    heavy = (
        "slots.py run --heavy --services"
        if target in SERVICES_TARGETS
        else "slots.py run --heavy --"
    )
    assert heavy in plan(tmp_path, target).stdout
    if HEAVY_TARGETS[target]:
        one_file = plan(tmp_path, target, "TESTS=tests/test_guard.py").stdout
        if target in SERVICES_TARGETS:
            assert "slots.py run --services" in one_file, "no wait, but the services of the tests"
            assert "--heavy" not in one_file
        else:
            assert "slots.py run" not in one_file
        assert one_file.rstrip().endswith("tests/test_guard.py")


def test_the_back_workers_follow_the_share(tmp_path: Path) -> None:
    """US-1090: at N = 2, the plan of test-back runs on the share, eight workers at most."""
    share = slots.processor_share(2)
    output = plan(tmp_path, "test-back", "WATERFALL_SLOTS=2").stdout
    assert f"-n {share} --maxprocesses 8" in output


def test_the_front_gets_the_share_of_a_run_of_one_file_too(tmp_path: Path) -> None:
    """US-1090: the front is given WATERFALL_PROCESSORS, whatever the run of the front."""
    share = slots.processor_share(2)
    for arguments in (["TESTS=x"], []):
        output = plan(tmp_path, "test-front", "WATERFALL_SLOTS=2", *arguments).stdout
        assert f"WATERFALL_PROCESSORS={share} pnpm test" in output


def test_make_names_an_invalid_slot_count_whatever_the_target(tmp_path: Path) -> None:
    """US-1090: with TESTS, an invalid WATERFALL_SLOTS stops make, saying so; other targets run."""
    refused = plan(tmp_path, "test-tools", "TESTS=x", "WATERFALL_SLOTS=x")
    assert refused.returncode != 0
    assert "WATERFALL_SLOTS" in refused.stderr
    assert plan(tmp_path, "lint-front", "WATERFALL_SLOTS=x").returncode == 0


def test_a_single_quote_in_the_slot_count_runs_nothing(tmp_path: Path) -> None:
    """US-1090: a quote in WATERFALL_SLOTS does not reach the shell; make names the setting."""
    witness = tmp_path / "witness"
    for value in (f"1'; touch {witness}; echo '", "it's"):
        refused = plan(tmp_path, "test-tools", "TESTS=x", f"WATERFALL_SLOTS={value}")
        assert refused.returncode != 0
        assert "WATERFALL_SLOTS must be an integer from 1 to 9" in refused.stderr
        assert "syntax error" not in refused.stderr
        assert not witness.exists()


def test_an_empty_slot_count_is_refused_as_the_tool_refuses_it(tmp_path: Path) -> None:
    """US-1090: a WATERFALL_SLOTS set to nothing has the verdict of the tool, whatever make."""
    run = start(tmp_path, [sys.executable, "-c", "pass"], "")
    run.communicate(timeout=60)
    assert run.returncode == 2
    refused = plan(tmp_path, "test-tools", "TESTS=x", "WATERFALL_SLOTS=")
    assert refused.returncode != 0
    assert "WATERFALL_SLOTS must be an integer from 1 to 9" in refused.stderr
    from_environment = plan(tmp_path, "test-tools", "TESTS=x", extra={"WATERFALL_SLOTS": ""})
    assert from_environment.returncode != 0
    assert "WATERFALL_SLOTS must be an integer from 1 to 9" in from_environment.stderr
