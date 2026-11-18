# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cache of the indicators serves what it kept and never blocks a read (WF-DAT-0130-A).

Against the Redis of the tests, as the guide asks: an entry served, an entry past its validity,
and a Redis that answers nowhere.
"""

import socket
import time
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import redis
from redis.exceptions import ResponseError
from structlog.testing import capture_logs

from waterfall.platform.cache import PREFIX, UNAVAILABLE, IndicatorsCache, forget_reports
from waterfall.platform.queue import DEPOSIT_TIMEOUT, WORKER_TIMEOUT, TaskQueue
from waterfall.platform.settings import load_settings

if TYPE_CHECKING:
    from collections.abc import Iterator

CLOSED_PORT = "redis://127.0.0.1:1/0"


@pytest.fixture(autouse=True)
def fresh_reports() -> None:
    """Forget the causes the process has logged: each test sees the first of them."""
    forget_reports()


@pytest.fixture
def key() -> str:
    return f"{uuid4()}:{uuid4().hex}"


@pytest.fixture
def indicators(queue: TaskQueue, key: str) -> Iterator[IndicatorsCache]:
    opened = IndicatorsCache.of(queue, 600)
    yield opened
    queue.client.delete(PREFIX + key)
    opened.close()


@pytest.fixture
def unreachable() -> Iterator[IndicatorsCache]:
    # The queue waits long: the delay of the cache is the cache's own.
    closed = TaskQueue.connect(CLOSED_PORT, timeout=WORKER_TIMEOUT)
    unavailable = IndicatorsCache.of(closed, 600)
    yield unavailable
    unavailable.close()
    closed.close()


@pytest.fixture
def silent() -> Iterator[IndicatorsCache]:
    """Give a cache on a Redis that accepts the connection and never answers."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    mute = TaskQueue.connect(f"redis://127.0.0.1:{port}/0", timeout=WORKER_TIMEOUT)
    unanswering = IndicatorsCache.of(mute, 600)
    yield unanswering
    unanswering.close()
    mute.close()
    listener.close()


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
def test_an_entry_written_for_two_seconds_expires_after_it(queue: TaskQueue, key: str) -> None:
    brief = IndicatorsCache.of(queue, 2)
    try:
        brief.write(key, "{}")
        assert brief.read(key) == "{}"
        time.sleep(2.2)
        assert brief.read(key) is None
    finally:
        queue.client.delete(PREFIX + key)
        brief.close()


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
def test_a_lookup_tells_an_entry_absent_from_a_redis_that_answers_nowhere(
    unreachable: IndicatorsCache, indicators: IndicatorsCache, key: str
) -> None:
    assert unreachable.lookup(key) is UNAVAILABLE
    assert indicators.lookup(key) is None


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_redis_that_answers_nowhere_answers_within_the_delay_of_a_request(
    unreachable: IndicatorsCache, key: str
) -> None:
    started = time.monotonic()
    unreachable.read(key)
    unreachable.write(key, "{}")
    assert time.monotonic() - started < 5 * DEPOSIT_TIMEOUT


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_redis_that_accepts_and_never_answers_is_left_after_the_delay_of_a_deposit(
    silent: IndicatorsCache, key: str
) -> None:
    started = time.monotonic()
    with capture_logs() as records:
        assert silent.read(key) is None
        silent.write(key, "{}")
    assert time.monotonic() - started < 5 * DEPOSIT_TIMEOUT
    unavailable = [r for r in records if r["event"] == "indicators.cache_unavailable"]
    assert [r["cause"] for r in unavailable] == ["TimeoutError"]


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_cache_sets_its_own_delay_whatever_the_queue_waits(queue: TaskQueue) -> None:
    opened = IndicatorsCache.of(queue, 600)
    try:
        kwargs = opened.client.connection_pool.connection_kwargs
        assert kwargs["socket_timeout"] == DEPOSIT_TIMEOUT
        assert kwargs["socket_connect_timeout"] == DEPOSIT_TIMEOUT
        assert queue.client.connection_pool.connection_kwargs["socket_timeout"] == WORKER_TIMEOUT
    finally:
        opened.close()


@pytest.mark.requirement("WF-DAT-0130-A")
def test_two_distinct_response_errors_are_one_record_with_the_first_message(
    indicators: IndicatorsCache, key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(message: str) -> object:
        def raiser(*_: object, **__: object) -> None:
            raise ResponseError(message)

        return raiser

    with capture_logs() as records:
        monkeypatch.setattr(indicators.client, "get", refuse("WRONGTYPE bad kind"))
        monkeypatch.setattr(indicators.client, "set", refuse("OOM no memory"))
        assert indicators.read(key) is None
        indicators.write(key, "{}")
    unavailable = [r for r in records if r["event"] == "indicators.cache_unavailable"]
    assert len(unavailable) == 1
    assert unavailable[0]["cause"] == "ResponseError"
    assert unavailable[0]["message"] == "WRONGTYPE bad kind"


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_cause_is_logged_once_across_the_instances_of_the_cache(
    unreachable: IndicatorsCache, key: str
) -> None:
    other = IndicatorsCache(unreachable.client, 600)
    with capture_logs() as records:
        unreachable.read(key)
        other.read(key)
    assert len([r for r in records if r["event"] == "indicators.cache_unavailable"]) == 1


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_client_that_gives_bytes_is_served_all_the_same(
    indicators: IndicatorsCache, redis_url: str, key: str
) -> None:
    indicators.write(key, '{"é": 1}')
    raw = redis.from_url(redis_url)
    try:
        served = IndicatorsCache(raw, 600)
        with capture_logs() as records:
            assert served.read(key) == '{"é": 1}'
        assert records == []
    finally:
        raw.close()


@pytest.mark.requirement("WF-DAT-0130-A")
def test_an_entry_that_is_not_utf8_is_read_as_none_and_logged_once(
    queue: TaskQueue, redis_url: str, key: str
) -> None:
    raw = redis.from_url(redis_url)
    try:
        raw.set(PREFIX + key, b"\xff")
        served = IndicatorsCache(raw, 600)
        with capture_logs() as records:
            assert served.read(key) is None
            assert served.read(key) is None
        unavailable = [r for r in records if r["event"] == "indicators.cache_unavailable"]
        assert [r["cause"] for r in unavailable] == ["UnicodeDecodeError"]
    finally:
        queue.client.delete(PREFIX + key)
        raw.close()


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


# --- Several entries at once: the entries of the scopes of a project (US-2420, #3628) ----------


@pytest.mark.requirement("WF-DAT-0130-A")
def test_entries_written_to_a_redis_that_never_answers_wait_for_it_once(
    silent: IndicatorsCache, key: str
) -> None:
    started = time.monotonic()
    silent.write_many({f"{key}:{rank}": "{}" for rank in range(5)})
    assert time.monotonic() - started < 2 * DEPOSIT_TIMEOUT


@pytest.mark.requirement("WF-DAT-0130-A")
def test_entries_written_together_are_read_together_in_their_order(
    indicators: IndicatorsCache, queue: TaskQueue, key: str
) -> None:
    keys = [f"{key}:project", f"{key}:unassigned", f"{key}:absent"]
    try:
        indicators.write_many({keys[1]: '{"v": 2}', keys[0]: '{"v": 1}'})
        assert indicators.lookup_many(keys) == ['{"v": 1}', '{"v": 2}', None]
        for each in keys[:2]:
            assert 0 < queue.client.ttl(PREFIX + each) <= 600
    finally:
        queue.client.delete(*(PREFIX + each for each in keys))


@pytest.mark.requirement("WF-DAT-0130-A")
def test_no_key_asked_reads_nothing_and_nothing_to_write_writes_nothing(
    unreachable: IndicatorsCache,
) -> None:
    with capture_logs() as records:
        assert unreachable.lookup_many([]) == []
        unreachable.write_many({})
    assert records == []


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_redis_that_answers_nowhere_reads_several_as_unavailable_and_ignores_their_write(
    unreachable: IndicatorsCache, key: str
) -> None:
    with capture_logs() as records:
        assert unreachable.lookup_many([key, f"{key}:other"]) is UNAVAILABLE
        unreachable.write_many({key: "{}", f"{key}:other": "{}"})
    unavailable = [r for r in records if r["event"] == "indicators.cache_unavailable"]
    assert [r["cause"] for r in unavailable] == ["ConnectionError"]


@pytest.mark.requirement("WF-DAT-0130-A")
def test_several_entries_read_as_bytes_are_decoded_and_one_not_utf8_is_none(
    queue: TaskQueue, redis_url: str, key: str
) -> None:
    raw = redis.from_url(redis_url)
    try:
        raw.set(PREFIX + key, '{"é": 1}'.encode())
        raw.set(PREFIX + key + ":bad", b"\xff")
        served = IndicatorsCache(raw, 600)
        with capture_logs() as records:
            assert served.lookup_many([key, f"{key}:bad"]) == ['{"é": 1}', None]
        assert [r["cause"] for r in records] == ["UnicodeDecodeError"]
    finally:
        queue.client.delete(PREFIX + key, PREFIX + key + ":bad")
        raw.close()
