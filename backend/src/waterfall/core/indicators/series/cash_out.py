# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cash-out by month (WF-IND-0100-A).

The past is what the documents say, by month of their date, the actual cost not being shifted; the
forecast is what is left to commit, spread over the part of the tasks after the date of calculation
and shifted by the payment delay of each line, in the parts of each line rounded to the cent
(``shares``). The month of the date of calculation carries both; a month without either is zero.
The forecast adds up to the rest to commit.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.indicators.series.cumulation import ZERO
from waterfall.core.indicators.series.months import months_between

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal

    from waterfall.core.estimate.interface import Month


@dataclass(frozen=True, slots=True)
class CashOutMonth:
    """A month of cash-out: what has been paid out, and what will be."""

    month: Month
    past: Decimal
    forecast: Decimal


def cash_out_by_month(
    past: Mapping[Month, Decimal], forecast: Mapping[Month, Decimal]
) -> list[CashOutMonth]:
    """Return the cash-out from the first to the last month, a month without amount at zero.

    The amounts are cents already: the documents are, and so are the parts of the lines.
    """
    months = [*past, *forecast]
    if not months:
        return []
    return [
        CashOutMonth(month, past.get(month, ZERO), forecast.get(month, ZERO))
        for month in months_between(min(months), max(months))
    ]
