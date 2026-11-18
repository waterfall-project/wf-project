# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts of a line by month, rounded so that they sum to its total (US-2040/L2).

Pure. A line is spread over the months of its task by ``spreading``; its part of a month is the
difference of two roundings of its cumulated load or amount, at the end of that month and at the
end of the month before, the cumulated of the last month being the whole line. A part is thus never
negative for a line that is not, and the parts sum to the total of the line, rounded: every total —
of a month, a task, a role, a category, a nature — is a sum of parts already rounded, which holds to
the hundredth the equalities of the Vérif of WF-DEV-0090 and WF-DEV-0100 (EP-10, recadrage of
2026-11-15; ``docs/api/DECISIONS.md``, US-2040/L1). Each magnitude keeps its rounding: the hours to
the hundredth, a half to the nearest even (``HOURS``); an amount to the cent, a half away from
nought (``MONEY``). The cumulated is exact, rounded once (``spreading``): that of an amount at the
end of a month is the planned value of the line then (``planned_value``, #3566). A month the
rounding leaves at nought is not one the line loads (#3096).

The plan of workload, its detail by task (US-2040), the projection of spending (US-2050) and the
curves of EP-10 (US-1690/L4, #3564) share it, each summing the parts at its own level. A caller that
spreads many lines of the same tasks weighs each task once (``weighing``, #3802): the weights of the
months do not depend on the amount, and the parts are the same.
"""

from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from itertools import accumulate
from typing import TYPE_CHECKING

from waterfall.core.estimate.spreading import Month, exact_of, month_weights
from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from datetime import date

    from waterfall.core.estimate.spreading import MonthWeights, Placement, Rounding

NOUGHT = Decimal(0)
ONE_DAY = timedelta(days=1)

# What gives the weights of the months of a task, from the date of calculation if any.
type Weighing = Callable[[Placement, date | None], MonthWeights]


def _weighed(placement: Placement, as_of: date | None) -> MonthWeights:
    return month_weights(placement, as_of=as_of)


def weighing() -> Weighing:
    """Give a weighing that weighs each task once, for one computation, its weights kept.

    The weights are those ``month_weights`` gives: a pure value of the task and the date, kept as
    long as the weighing is, never longer.
    """
    held: dict[tuple[Placement, date | None], MonthWeights] = {}

    def weigh(placement: Placement, as_of: date | None) -> MonthWeights:
        key = (placement, as_of)
        found = held.get(key)
        if found is None:
            found = held[key] = month_weights(placement, as_of=as_of)
        return found

    return weigh


def rounded_parts(
    placement: Placement,
    total: Decimal,
    rounding: Rounding,
    *,
    as_of: date | None = None,
    weigh: Weighing = _weighed,
) -> dict[Month, Decimal]:
    """Give the parts of a line in the months it loads, in their order, rounded to sum to its total.

    ``as_of`` is the date of calculation of a remaining: the line is then spread over the part of
    its task after it, or falls whole in its month once the task is over (``spread_by_month``).
    ``weigh`` gives the weights of the months of the task, one weighing kept by the caller
    (``weighing``) or each time.
    """
    shares = exact_of(total, weigh(placement, as_of))
    return parts_of_cumulated(zip(shares, accumulate(shares.values()), strict=True), rounding)


def remaining_parts(
    placement: Placement,
    total: Decimal,
    rounding: Rounding,
    *,
    as_of: date,
    weigh: Weighing = _weighed,
) -> dict[Month, Decimal]:
    """Give the parts of a remaining to commit, the part of its task after the end of ``as_of``.

    The date of calculation belongs to the past, as the curves of cost and the projection of
    spending read it (WF-IND-0100, WF-RAE-0040): the share starts at the first hour of the next
    day, and a task that ends by then falls whole on the month of ``as_of``, not on that of the
    next day (#3615).
    """
    if placement.finish <= WorkInstant(as_of + ONE_DAY):
        return parts_of_cumulated([(Month(as_of.year, as_of.month), Fraction(total))], rounding)
    return rounded_parts(placement, total, rounding, as_of=as_of + ONE_DAY, weigh=weigh)


def parts_of_cumulated(
    cumulated: Iterable[tuple[Month, Fraction]], rounding: Rounding
) -> dict[Month, Decimal]:
    """Give the parts of a line from its exact cumulated at the end of each month, in their order.

    The part of a month is the rounded cumulated at its end less that at the end of the month
    before; the cumulated of the last month is the whole line. A spreading that is not that of
    ``rounded_parts`` — the curve of the cash-out of EP-10, each month read at its end less the
    payment delay of the line (US-1690/L4) — gives its cumulated here, and is rounded alike.
    """
    found: dict[Month, Decimal] = {}
    before = NOUGHT
    for month, exact in cumulated:
        done = rounding.of(exact)
        if part := done - before:
            found[month] = part
        before = done
    return found


def summed_parts(parts: Iterable[Mapping[Month, Decimal]]) -> dict[Month, Decimal]:
    """Add up some parts month by month, in the order of the months; a month at nought left out."""
    sums: dict[Month, Decimal] = {}
    for months in parts:
        for month, part in months.items():
            sums[month] = sums.get(month, NOUGHT) + part
    return {month: sums[month] for month in sorted(sums) if sums[month]}
