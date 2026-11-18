# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cumulative series at the step of the month (WF-IND-0100-A, WF-IND-0110-A).

Each point carries the cumulative total at the end of its month. The first, zero, sits at the end
of the month that precedes the first amount; the date of calculation is one more point on the
series that stops or starts there. The parts of the lines come rounded to the cent (``shares``)
and the documents are cents: a sum of cents is a cent, so ``cumulative`` needs no rounding of its
own to give a point its two decimals, as the contract serves them (WF-DAT-0100). The series of
documents and of the actual cost, whose amounts come from outside the estimate, are rounded to the
cent all the same.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import round_to_cent
from waterfall.core.indicators.series.months import (
    end_of,
    events_by_month,
    month_before,
    month_of,
    months_between,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date

    from waterfall.core.estimate.interface import Month

ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class Point:
    """A point of a series: a day, and the cumulative amount at that day."""

    day: date
    amount: Decimal


def to_cent(amount: Decimal) -> Decimal:
    """Round an amount to the cent, a half going away from zero: that of the estimate."""
    return round_to_cent(amount)


def cumulative(shares: Mapping[Month, Decimal], *, through: date | None = None) -> list[Point]:
    """Return the cumulative series by month-end, none without a part.

    It runs from the month before the first part, at zero, to the month of the last part, or of
    ``through`` when that is later: a series that stays flat to the end of a reference.
    """
    if not shares:
        return []
    first = min(shares)
    last = max(shares)
    if through is not None:
        last = max(last, month_of(through))
    running = Decimal(0)
    points = [Point(end_of(month_before(first)), ZERO)]
    for month in months_between(first, last):
        running += shares.get(month, Decimal(0))
        points.append(Point(end_of(month), running))
    return points


def cumulative_until(
    events: Iterable[tuple[date, Decimal]], as_of: date, *, from_month: Month | None = None
) -> list[Point]:
    """Return the cumulative series of dated amounts, which stops at the date of calculation.

    The month-ends before ``as_of`` are followed by ``as_of`` carrying every amount dated up to
    it, that day included; those of a later day, in its month or after, are left out here, once and
    for all. ``from_month`` makes a series without an amount start at zero, as a line without a
    document is drawn at zero (WF-IND-0100-A), at the month of ``as_of`` when it starts later.
    """
    kept = events_by_month(events, until=as_of)
    cut = month_of(as_of)
    starts = [*kept, *([min(from_month, cut)] if from_month is not None else [])]
    if not starts:
        return []
    first = min(starts)
    points = [Point(end_of(month_before(first)), ZERO)]
    running = Decimal(0)
    for month in months_between(first, cut):
        running += kept.get(month, Decimal(0))
        if end_of(month) < as_of:
            points.append(Point(end_of(month), to_cent(running)))
    points.append(Point(as_of, to_cent(running)))
    return points


def cumulative_from(shares: Mapping[Month, Decimal], as_of: date, base: Decimal) -> list[Point]:
    """Return the cumulative series that starts at the date of calculation, from its ``base``.

    The first point is ``as_of`` at the base — the actual cost there —; each month-end from the
    month of ``as_of`` adds its parts, a month-end that is ``as_of`` itself being that same point.
    Without a part to come, nothing follows: the series is that one point.
    """
    first = month_of(as_of)
    kept = {month: part for month, part in shares.items() if month >= first}
    points = [Point(as_of, to_cent(base))]
    if not kept:
        return points
    running = base
    for month in months_between(first, max(kept, default=first)):
        running += kept.get(month, Decimal(0))
        point = Point(end_of(month), to_cent(running))
        if point.day == as_of:
            points[0] = point
        else:
            points.append(point)
    return points
