# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The directory of the locks of the workstation, one for every session (US-2460, PLC-13).

``slots.py`` and ``tracking.py`` take it from ``heavyturns.runtime_directory``. The fixture
``user_runtime`` moves ``/run/user`` under the test: no test touches the locks of the workstation.
"""

import fcntl
import os
from pathlib import Path

import pytest

from wftools import heavyturns, slots, tracking


@pytest.mark.story("US-2460")
def test_the_directory_of_the_locks_is_the_variable_then_the_one_of_the_user_then_tmp(
    user_runtime: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """US-2460: WATERFALL_RUNTIME_DIR, else /run/user/<uid>, else /tmp; XDG_RUNTIME_DIR unread."""
    elsewhere = {"XDG_RUNTIME_DIR": "/elsewhere"}
    assert heavyturns.runtime_directory({"WATERFALL_RUNTIME_DIR": "/run/x"} | elsewhere) == Path(
        "/run/x"
    )
    assert heavyturns.runtime_directory(elsewhere) == user_runtime
    assert heavyturns.runtime_directory({"WATERFALL_RUNTIME_DIR": ""}) == user_runtime
    # Under a systemd session, XDG_RUNTIME_DIR is /run/user/<uid>: the directory of before.
    assert heavyturns.runtime_directory({"XDG_RUNTIME_DIR": str(user_runtime)}) == user_runtime
    monkeypatch.setattr(heavyturns, "USER_RUNTIME_ROOT", user_runtime / "absent")
    assert heavyturns.runtime_directory(elsewhere) == Path(os.sep, "tmp")


@pytest.mark.story("US-2460")
def test_two_sessions_one_without_xdg_runtime_dir_share_the_slots_and_turns(
    user_runtime: Path, tmp_path: Path
) -> None:
    """US-2460, PLC-13: the register, the heavy turns and the test services are one for both.

    One session has XDG_RUNTIME_DIR elsewhere, the other none: before, the first locked under its
    variable and the second under /tmp, and each believed itself alone on the workstation.
    """
    with_variable = {"XDG_RUNTIME_DIR": str(tmp_path / "elsewhere")}
    without: dict[str, str] = {}
    assert slots.register(with_variable) == slots.register(without)
    assert slots.register(without).parent == user_runtime
    first, second = tmp_path / "first", tmp_path / "second"
    for worktree in (first, second):
        (worktree / ".git").mkdir(parents=True)

    def keep(_slot: int) -> None:
        """Remove nothing: no slot here was ever used."""

    assert slots.claim(slots.register(with_variable), first, 1, keep) == (1, True)
    with pytest.raises(slots.RegisterError, match="all 1 slot"):
        slots.claim(slots.register(without), second, 1, keep)
    held = heavyturns.take_slot(heavyturns.lock_paths(with_variable, 1))
    assert held is not None
    try:
        assert heavyturns.take_slot(heavyturns.lock_paths(without, 1)) is None
    finally:
        os.close(held)
    with slots.services_locked(with_variable, 1):
        descriptor = os.open(user_runtime / "waterfall-test-services.1.lock", os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)


@pytest.mark.story("US-2460")
def test_two_sessions_one_without_xdg_runtime_dir_share_the_lock_of_an_issue(
    user_runtime: Path, tmp_path: Path
) -> None:
    """US-2460, PLC-13: the lock of an issue is one for a session with XDG_RUNTIME_DIR and without.

    Before, the first locked under its variable and the second under /tmp: two deliverers could
    write the same table at once, and one change was lost.
    """
    with_variable = tracking.lock_path({"XDG_RUNTIME_DIR": str(tmp_path / "elsewhere")}, 7)
    without = tracking.lock_path({}, 7)
    assert with_variable == without == user_runtime / "waterfall-tracking-7.lock"
    with tracking.locked(with_variable):
        descriptor = os.open(without, os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)
