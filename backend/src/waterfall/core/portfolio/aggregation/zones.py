# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The zones of the portfolio: the distribution of the projects, the zone of a month of load.

Pure. A zone is classified at the reading, on the thresholds of the day (WF-REF-0170): the
distribution counts each project once per index, a project whose index is not computable in no
zone of it (WF-PTF-0070); a month of load is in alert beyond the capacity, in watch under the
threshold of under-load, nominal otherwise (WF-PTF-0060).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from waterfall.core.indicators.interface import Computable, zone_of
from waterfall.core.portfolio.aggregation.ratios import ratio_of

if TYPE_CHECKING:
    from collections.abc import Iterable

type Zone = Literal["nominal", "watch", "alert"]

NOMINAL: Zone = "nominal"
WATCH: Zone = "watch"
ALERT: Zone = "alert"
ZONES: tuple[Zone, ...] = (NOMINAL, WATCH, ALERT)
NO_CAPACITY = "no_capacity"
NOUGHT = Decimal(0)


@dataclass(frozen=True, slots=True)
class ZoneCount:
    """The number of projects in a zone."""

    zone: Zone
    project_count: int


def zone_distribution(
    indices: Iterable[Computable], watch: Decimal, alert: Decimal
) -> tuple[ZoneCount, ...]:
    """Count the projects by zone of one index, the three zones always given, in their order.

    An index not computable is in no zone: the counts sum to the projects whose index is computed.
    """
    zones = [zone_of(each, watch, alert) for each in indices]
    return tuple(ZoneCount(zone, zones.count(zone)) for zone in ZONES)


def load_ratio(hours: Decimal, capacity: Decimal) -> Computable:
    """Give the load over the capacity, to four decimals, ``no_capacity`` without capacity."""
    return ratio_of(hours, capacity, NO_CAPACITY)


def load_zone(hours: Decimal, capacity: Decimal, under_load_threshold: Decimal) -> Zone:
    """Give the zone of a month of a role: its load against its capacity and the threshold.

    Alert when the load exceeds the capacity, watch when the ratio of the load to the capacity is
    below the threshold — a role without load included — and nominal otherwise. A role without
    capacity that month is in alert if it has load, in watch if it has none. The comparison is on
    the exact hours, not on the ratio rounded to four decimals.
    """
    if capacity <= NOUGHT:
        return ALERT if hours > NOUGHT else WATCH
    if hours > capacity:
        return ALERT
    if hours < capacity * under_load_threshold:
        return WATCH
    return NOMINAL
