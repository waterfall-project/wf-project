# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The months of a horizon and the quarters of a period, civil (WF-PTF-0060, WF-PTF-0070).

Pure. The months of a view run from the month of the date of calculation, or from some months
before it, without a gap; the evolution of the indices has one point per civil quarter that the
period touches, each read on its last day and, for the quarter that holds the date of calculation,
on that date (WF-PTF-0010).
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import Month

if TYPE_CHECKING:
    from collections.abc import Sequence

MONTHS_PER_YEAR = 12
MONTHS_PER_QUARTER = 3


def month_of(day: date) -> Month:
    """Give the civil month of a day."""
    return Month(day.year, day.month)


def month_label(month: Month) -> str:
    """Name a month as the contract does: ``2026-03``."""
    return f"{month.year:04d}-{month.month:02d}"


def _index_of(month: Month) -> int:
    return month.year * MONTHS_PER_YEAR + month.month - 1


def _month_at(index: int) -> Month:
    year, rest = divmod(index, MONTHS_PER_YEAR)
    return Month(year, rest + 1)


def months_window(as_of: date, *, before: int = 0, horizon: int) -> Sequence[Month]:
    """Give ``before + horizon`` months, from ``before`` months before that of the date.

    The month of the date is the first of its ``horizon`` months: the aggregated workload runs
    ``horizon`` months from it (``before`` nought), the S-curve ``before`` twelve before it and
    ``horizon`` from it (WF-PTF-0100): June 2026, twelve and six, runs
    from June 2025 to November 2026.
    """
    first = _index_of(month_of(as_of)) - before
    return [_month_at(index) for index in range(first, first + before + horizon)]


@dataclass(frozen=True, slots=True, order=True)
class Quarter:
    """A civil quarter, ``1`` to ``4``."""

    year: int
    number: int

    @property
    def label(self) -> str:
        """Name the quarter as the contract does: ``2026-Q1``."""
        return f"{self.year:04d}-Q{self.number}"

    @property
    def last_day(self) -> date:
        """Give the last day of the quarter."""
        month = self.number * MONTHS_PER_QUARTER
        return date(self.year, month, monthrange(self.year, month)[1])


def quarter_of(day: date) -> Quarter:
    """Give the civil quarter of a day."""
    return Quarter(day.year, (day.month - 1) // MONTHS_PER_QUARTER + 1)


def quarters_touched(period_from: date, period_to: date) -> list[Quarter]:
    """Give the civil quarters a period touches, bounds included, the oldest first.

    The contract names the quarters the period touches and bounds them by nothing else: a period
    that runs past the date of calculation gives quarters that are not over, each read on that date
    (``reading_day``), which the view repeats as the contract has it.
    """
    quarters: list[Quarter] = []
    quarter = quarter_of(period_from)
    last = quarter_of(period_to)
    while quarter <= last:
        quarters.append(quarter)
        quarter = Quarter(quarter.year + quarter.number // 4, quarter.number % 4 + 1)
    return quarters


def reading_day(quarter: Quarter, as_of: date) -> date:
    """Give the day a quarter is read on: its last day, the date of calculation if it holds it.

    A quarter that ends after the date is read on the date, never in the future: the last day of
    the quarter that holds the date of calculation has not been marked yet.
    """
    return min(quarter.last_day, as_of)
