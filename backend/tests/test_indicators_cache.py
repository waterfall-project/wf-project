# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cache of the indicators serves what it kept and never blocks a read (WF-DAT-0130-A).

Against the Redis of the tests, as the guide asks: an entry served, an entry past its validity,
and a Redis that answers nowhere.
"""

import time
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from waterfall.platform import cache
from waterfall.platform.cache import PREFIX, IndicatorsCache
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.settings import load_settings

if TYPE_CHECKING:
    from collections.abc import Iterator

CLOSED_PORT = "redis://127.0.0.1:1/0"


@pytest.fixture(autouse=True)
def fresh_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forget the causes the process has logged: each test sees the first of them."""
    monkeypatch.setattr(cache, "reported", set[str]())


@pytest.fixture
def key() -> str:
    return f"{uuid4()}:{uuid4().hex}"


@pytest.fixture
def indicators(queue: TaskQueue, key: str) -> Iterator[IndicatorsCache]:
    yield IndicatorsCache.of(queue, 600)
    queue.client.delete(PREFIX + key)


@pytest.fixture
def unreachable() -> Iterator[IndicatorsCache]:
    closed = TaskQueue.connect(CLOSED_PORT, timeout=DEPOSIT_TIMEOUT)
    yield IndicatorsCache.of(closed, 600)
    closed.close()


@pytest.mark.requirement("WF-DAT-0130-A")
def test_an_entry_written_is_served_under_the_prefix_of_the_cache(
    indicators: IndicatorsCache, key: str
) -> None:
    indicators.write(key, '{"cost_index": "1.05"}')
    assert indicators.read(key) == '{"cost_index": "1.05"}'
    assert indicators.client.get(PREFIX + key) == '{"cost_index": "1.05"}'


@pytest.mark.requirement("WF-DAT-0130-A")
def test_an_entry_never_written_is_read_as_none(indicators: IndicatorsCache, key: str) -> None:
    assert indicators.read(key) is None


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_validity_period_is_set_at_the_write(queue: TaskQueue, key: str) -> None:
    short = IndicatorsCache.of(queue, 90)
    short.write(key, "{}")
    try:
        assert 0 < short.client.ttl(PREFIX + key) <= 90
    finally:
        queue.client.delete(PREFIX + key)


@pytest.mark.requirement("WF-DAT-0130-A")
def test_an_entry_past_its_validity_is_no_longer_served(
    indicators: IndicatorsCache, key: str
) -> None:
    indicators.write(key, "{}")
    indicators.client.pexpire(PREFIX + key, 1)
    time.sleep(0.05)
    assert indicators.read(key) is None


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_write_renews_the_validity_of_the_entry(queue: TaskQueue, key: str) -> None:
    indicators = IndicatorsCache.of(queue, 600)
    indicators.write(key, '{"v": 1}')
    indicators.client.pexpire(PREFIX + key, 5)
    indicators.write(key, '{"v": 2}')
    try:
        assert indicators.client.ttl(PREFIX + key) > 5
        assert indicators.read(key) == '{"v": 2}'
    finally:
        queue.client.delete(PREFIX + key)


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_redis_that_answers_nowhere_reads_as_none_and_ignores_a_write(
    unreachable: IndicatorsCache, key: str
) -> None:
    unreachable.write(key, "{}")
    assert unreachable.read(key) is None


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_redis_that_answers_nowhere_answers_within_the_delay_of_a_request(
    unreachable: IndicatorsCache, key: str
) -> None:
    started = time.monotonic()
    unreachable.read(key)
    unreachable.write(key, "{}")
    assert time.monotonic() - started < 3 * DEPOSIT_TIMEOUT


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_unavailable_cache_is_logged_once_by_cause(
    unreachable: IndicatorsCache, key: str
) -> None:
    with capture_logs() as records:
        for _ in range(3):
            unreachable.read(key)
            unreachable.write(key, "{}")
    unavailable = [r for r in records if r["event"] == "indicators.cache_unavailable"]
    assert len(unavailable) == 1
    assert unavailable[0]["log_level"] == "warning"
    assert unavailable[0]["cause"] == "ConnectionError"


@pytest.mark.requirement("WF-DAT-0130-A")
def test_an_entry_served_is_not_logged(indicators: IndicatorsCache, key: str) -> None:
    with capture_logs() as records:
        indicators.write(key, "{}")
        indicators.read(key)
    assert records == []


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_validity_period_is_ten_minutes_unless_the_environment_says_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_DATABASE_URL", "postgresql://u:p@localhost/d")
    monkeypatch.setenv("WATERFALL_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.delenv("WATERFALL_INDICATORS_CACHE_TTL", raising=False)
    assert load_settings().indicators_cache_ttl == 600
    monkeypatch.setenv("WATERFALL_INDICATORS_CACHE_TTL", "30")
    assert load_settings().indicators_cache_ttl == 30
