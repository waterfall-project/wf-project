# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The measure of the entry of the cache of the indicators (US-2420, #3628; WF-QUA-0060).

``make measure-core ONLY=indicators`` measures, on PRJ-001 of the witness and in the Redis of the
platform, the size of the entry of the day and the reading of one scope of it, whole and alone,
cold and hot. The tool is the one of WF-QUA-0060: these tests hold its arithmetic, and its promise
to leave no entry in Redis.
"""

from typing import TYPE_CHECKING, Protocol, cast

import pytest

from measure.indicators import SUBPROJECTS, linear, measure_cache
from measure.target import MeasureError, cache_from_environment, locate
from waterfall.platform.cache import PREFIX, IndicatorsCache
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from collections.abc import Iterator

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue


class Keyed(Protocol):
    """What this test asks of the client of Redis of the cache, typed: its keys."""

    def scan_iter(self, *, match: str) -> Iterator[str]: ...


def keys_of(cache: IndicatorsCache) -> set[str]:
    return set(cast("Keyed", cache.client).scan_iter(match=f"{PREFIX}*"))


def test_a_figure_is_extrapolated_on_the_line_through_one_scope_and_the_whole_entry() -> None:
    # WF-QUA-0060: 0.2 s for one scope, 0.5 s for the four of the witness: 0.1 s a scope.
    assert linear(0.2, 0.5, 4, 1) == pytest.approx(0.2)
    assert linear(0.2, 0.5, 4, 4) == pytest.approx(0.5)
    assert linear(0.2, 0.5, 4, 12) == pytest.approx(1.3)


def test_the_cache_is_the_slots_redis_with_the_password_of_the_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_REDIS_PASSWORD", "secret")
    monkeypatch.setenv("WATERFALL_REDIS_PORT", "20411")

    cache = cache_from_environment()

    kwargs = cache.client.connection_pool.connection_kwargs
    assert (kwargs["port"], kwargs["password"]) == (20411, "secret")
    cache.close()


def test_the_cache_without_the_password_of_the_platform_says_what_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WATERFALL_REDIS_PASSWORD", raising=False)

    with pytest.raises(MeasureError, match="WATERFALL_REDIS_PASSWORD"):
        cache_from_environment()


def test_a_port_of_redis_that_is_no_number_is_refused_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_REDIS_PASSWORD", "secret")
    monkeypatch.setenv("WATERFALL_REDIS_PORT", "many")

    with pytest.raises(MeasureError, match="WATERFALL_REDIS_PORT"):
        cache_from_environment()


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[IndicatorsCache]:
    opened = IndicatorsCache.of(queue, 60)
    yield opened
    opened.close()


def test_the_entry_of_the_day_measured_gives_its_size_and_its_reading_and_leaves_no_entry(
    witness: Database, cache: IndicatorsCache
) -> None:
    # WF-QUA-0060: the figures are those the report of a version carries.
    target = locate(witness)
    before = keys_of(cache)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        measures = measure_cache(witness, target.place.project_id, cache, 1)

    assert keys_of(cache) == before
    assert [each.name for each in measures] == [
        "indicators cache, the whole entry, cold",
        "indicators cache, the whole entry, hot",
        "indicators cache, one scope alone, cold",
        "indicators cache, one scope alone, hot",
        "indicators cache",
    ]
    facts = measures[-1].facts
    assert int(facts["scopes"]) == int(facts["subprojects"]) + 2
    assert int(facts["entry_bytes"]) >= int(facts["cell_bytes"]) > 0
    for name in ("cold_whole_s", "cold_cell_s", "hot_whole_s", "hot_cell_s"):
        assert float(facts[name]) > 0
    assert [row["subprojects"] for row in measures[-1].rows] == list(SUBPROJECTS)
