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

The plan of workload, its detail by task (US-2040) and the projection of spending (US-2050) share
it, each summing the parts at its own level.
"""

from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.estimate.spreading import exact_by_month

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date

    from waterfall.core.estimate.spreading import Month, Placement, Rounding

NOUGHT = Decimal(0)


def rounded_parts(
    placement: Placement, total: Decimal, rounding: Rounding, *, as_of: date | None = None
) -> dict[Month, Decimal]:
    """Give the parts of a line in the months it loads, in their order, rounded to sum to its total.

    ``as_of`` is the date of calculation of a remaining: the line is then spread over the part of
    its task after it, or falls whole in its month once the task is over (``spread_by_month``).
    """
    found: dict[Month, Decimal] = {}
    cumulated, before = Fraction(0), NOUGHT
    for month, share in exact_by_month(placement, total, as_of=as_of).items():
        # Exact, the cumulated of the last month is the whole line.
        cumulated += share
        done = rounding.of(cumulated)
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
