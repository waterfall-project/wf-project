# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The wait of a migration run for the lock of the others is read in its log (US-2850/L5, #5096)."""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text

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
def test_a_lock_held_two_seconds_gives_at_most_two_warnings_of_the_run_that_waits(
    empty_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    # #5151: a WARNING at the first refusal, then one every ten seconds, not one per refusal.
    caplog.set_level("WARNING")
    with ThreadPoolExecutor(1) as pool, empty_engine.connect() as holder:
        holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": KEY})
        holder.commit()
        migrating = pool.submit(upgrade, empty_engine, "0001")
        time.sleep(2)
        holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": KEY})
        holder.commit()
        migrating.result(timeout=60)
    refusals = [each for each in caplog.messages if "migration lock refused" in each]
    assert 1 <= len(refusals) <= 2
