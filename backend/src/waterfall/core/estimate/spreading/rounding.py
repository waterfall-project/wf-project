# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rounding of a load or an amount spread, once, from its exact value (US-2040/L2).

Each magnitude keeps its rounding: the hours to the hundredth, a half to the nearest even
(``HOURS``); an amount to the cent, a half away from nought (``MONEY``), as ``pricing`` rounds it
(#2773). A value is rounded from the exact fraction a spreading gives, never from a decimal that
would have rounded it first (WF-DAT-0100): the parts of a line by month (``parting``) and the
planned value of a line at a day (``planned``) round the same cumulated the same way.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from fractions import Fraction

from waterfall.core.estimate.pricing import CENT

HALF = Fraction(1, 2)


@dataclass(frozen=True, slots=True)
class Rounding:
    """How a magnitude is rounded: to the nearest quantum, a half in a mode of ``decimal``.

    ``mode`` is ``ROUND_HALF_EVEN`` or ``ROUND_HALF_UP``: it decides a half only.
    """

    quantum: Decimal
    mode: str

    def of(self, value: Decimal | Fraction) -> Decimal:
        """Round an exact value to the nearest quantum, a half in the mode."""
        steps = Fraction(value) / Fraction(self.quantum)
        floor = steps.numerator // steps.denominator
        rest = steps - floor
        if rest == HALF:
            # The only case the mode decides: ``floor + 0.5`` is exact as a decimal.
            whole = int((Decimal(floor) + Decimal("0.5")).quantize(Decimal(1), rounding=self.mode))
        else:
            whole = floor + int(rest > HALF)
        return Decimal(whole) * self.quantum


HOURS = Rounding(Decimal("0.01"), ROUND_HALF_EVEN)
"""The hours: to the hundredth, a half to the nearest even, as the plan of workload rounds them."""

MONEY = Rounding(CENT, ROUND_HALF_UP)
"""An amount (``Money``): to the cent, a half away from nought, as ``pricing`` rounds it."""
