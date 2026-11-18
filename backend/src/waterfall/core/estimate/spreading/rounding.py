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
from typing import TYPE_CHECKING

from waterfall.core.estimate.pricing import CENT

if TYPE_CHECKING:
    from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Rounding:
    """How a magnitude is rounded: to the nearest quantum, a half in a mode of ``decimal``.

    ``mode`` is ``ROUND_HALF_EVEN`` or ``ROUND_HALF_UP``: it decides a half only.
    """

    quantum: Decimal
    mode: str

    def of(self, value: Decimal | Fraction) -> Decimal:
        """Round an exact value to the nearest quantum, a half in the mode.

        In integers, the value and the quantum as their ratios: the value is in quanta
        ``numerator / denominator``, its floor and the rest of it compared to a half exactly, as
        fractions would, without making any (#3902: the curves round tens of thousands of parts).
        """
        top, bottom = value.as_integer_ratio()
        quantum_top, quantum_bottom = self.quantum.as_integer_ratio()
        numerator, denominator = top * quantum_bottom, bottom * quantum_top
        floor, rest = divmod(numerator, denominator)
        if 2 * rest == denominator:
            # The only case the mode decides, in integers: a decimal context rounds a big floor.
            if self.mode == ROUND_HALF_UP:
                whole = floor + 1 if floor >= 0 else floor
            else:
                whole = floor if floor % 2 == 0 else floor + 1
        else:
            whole = floor + int(2 * rest > denominator)
        return Decimal(whole) * self.quantum


HOURS = Rounding(Decimal("0.01"), ROUND_HALF_EVEN)
"""The hours: to the hundredth, a half to the nearest even, as the plan of workload rounds them."""

MONEY = Rounding(CENT, ROUND_HALF_UP)
"""An amount (``Money``): to the cent, a half away from nought, as ``pricing`` rounds it."""
