# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The wait of a migration run for the lock of the others is read in its log (US-2850/L5, #5096)."""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from support import RefusalClock

from waterfall.migrations.runner import upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine

# The key of the lock of a migration run (``MIGRATION_LOCK`` of ``migrations/env.py``, which a
# test cannot import: it runs the migrations as it is loaded).
KEY = 7_240_330


@pytest.mark.story("US-2850")
def test_a_run_that_waits_for_the_lock_of_another_writes_a_warning_naming_the_lock_and_step(
    empty_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("WARNING")
    with ThreadPoolExecutor(1) as pool, empty_engine.connect() as holder:
        holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": KEY})
        holder.commit()
        migrating = pool.submit(upgrade, empty_engine, "0001")
        deadline = time.monotonic() + 30
        while not caplog.records and time.monotonic() < deadline:
            time.sleep(0.05)
        holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": KEY})
        holder.commit()
        migrating.result(timeout=60)
    assert caplog.records
    refusal = caplog.records[0]
    assert refusal.levelname == "WARNING"
    assert f"advisory lock {KEY}" in refusal.getMessage()
    assert "alembic_version" not in refusal.getMessage()
    assert "lock of the migration run" in refusal.getMessage()


@pytest.mark.story("US-2850")
@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_lock_refused_thirteen_times_over_a_clock_of_a_second_a_try_gives_two_warnings(
    empty_engine: Engine, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Give the first refusal, then the one past ten seconds with the count of those between.

    #5151. The clock is the test's, one second a try, so that the limit is proved whatever the
    speed of the machine: thirteen refusals cover thirteen seconds, which is more than the two
    seconds of the criterion (a lock held two seconds gives at most two lines) and crosses the
    ten-second limit once. Over the real time, the former code, a line per refusal, passed that
    criterion too: the period of a refusal was too long for the test to tell them apart.
    """
    clock = RefusalClock(monkeypatch, ("env.py",), stop_after=13)
    caplog.set_level("WARNING")
    with ThreadPoolExecutor(1) as pool, empty_engine.connect() as holder:
        holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": KEY})
        holder.commit()
        migrating = pool.submit(upgrade, empty_engine, "0001")
        assert clock.reached.wait(60)
        holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": KEY})
        holder.commit()
        clock.gate.set()
        migrating.result(timeout=60)
    refusals = [each for each in caplog.messages if "migration lock refused" in each]
    assert len(refusals) == 2
    assert "refused 1 time(s)" in refusals[0]
    assert "refused 10 time(s)" in refusals[1]
