# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The one rounding of an indicator (WF-DAT-0100).

Every grandeur is computed exact, then rounded once, at the end: the amounts to the cent, half
away from zero as ``Money`` of the contract says (#2618), the ratios and the indices to four
decimals, half to even.
"""

from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

NOUGHT = Decimal(0)
CENT = Decimal("0.01")
RATIO_STEP = Decimal("0.0001")


def round_amount(amount: Decimal) -> Decimal:
    """Round an amount to the cent, half away from zero."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def round_ratio(ratio: Decimal) -> Decimal:
    """Round a ratio or an index to four decimals, half to even."""
    return ratio.quantize(RATIO_STEP, rounding=ROUND_HALF_EVEN)
