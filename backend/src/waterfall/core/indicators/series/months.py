# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The month-ends the curves are drawn on (WF-IND-0100-A, WF-IND-0110-A).

A curve has one point per month-end, so a month is named by its civil month and a point by the
last day of it. Pure: dates in, dates out.
"""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import Month

if TYPE_CHECKING:
    from collections.abc import Iterable

MONTHS_PER_YEAR = 12


def month_of(day: date) -> Month:
    """Return the civil month of a day."""
    return Month(day.year, day.month)


def end_of(month: Month) -> date:
    """Return the last day of a month, where the point of the month sits."""
    return date(month.year, month.month, monthrange(month.year, month.month)[1])


def month_end(day: date) -> date:
    """Return the last day of the month of a day."""
    return end_of(month_of(day))


def _index(month: Month) -> int:
    return month.year * MONTHS_PER_YEAR + month.month - 1


def _from_index(index: int) -> Month:
    year, number = divmod(index, MONTHS_PER_YEAR)
    return Month(year, number + 1)


def month_before(month: Month) -> Month:
    """Return the month that precedes a month."""
    return _from_index(_index(month) - 1)


def months_between(first: Month, last: Month) -> list[Month]:
    """Return the months from the first to the last, both included."""
    return [_from_index(index) for index in range(_index(first), _index(last) + 1)]


def month_ends(first: date, last: date) -> list[date]:
    """Return the month-ends of the months from that of ``first`` to that of ``last``."""
    return [end_of(month) for month in months_between(month_of(first), month_of(last))]


def events_by_month(
    events: Iterable[tuple[date, Decimal]], *, until: date | None = None
) -> dict[Month, Decimal]:
    """Add up, by month of their date, dated amounts; those after ``until`` are left out."""
    total: dict[Month, Decimal] = {}
    for day, amount in events:
        if until is not None and day > until:
            continue
        month = month_of(day)
        total[month] = total.get(month, Decimal(0)) + amount
    return total
