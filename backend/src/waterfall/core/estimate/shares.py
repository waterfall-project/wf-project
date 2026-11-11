# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The share of an amount in a total, and of the amounts of a distribution (WF-DEV-0060).

Pure. A share is an exact decimal given to four decimal places, rounded to nearest, a half going
away from zero; a share that is not nought is never given as nought, but to its first significant
digit, rounded the same way. The shares of a distribution of the total sum exactly to one: the
remainder of their roundings, floor included, is carried by the largest — the first on a tie —,
which may then carry more than four decimal places. The share of a part that carries only some of
the lines receives none. The rounding holds for the value returned alone (docs/api/README.md, "A
share…").
"""

from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

NOUGHT = Decimal(0)
ONE = Decimal(1)
PLACES = Decimal("0.0001")
# The precision a quotient is computed at, before its rounding.
PRECISION = 60


def share_of(amount: Decimal, total: Decimal) -> Decimal:
    """Give the share of an amount in a total, which is not nought, rounded as the contract says."""
    with localcontext() as context:
        context.prec = PRECISION
        exact = amount / total
        rounded = exact.quantize(PLACES, rounding=ROUND_HALF_UP)
        if rounded == 0 and exact != 0:
            return exact.quantize(ONE.scaleb(exact.adjusted()), rounding=ROUND_HALF_UP)
        return rounded


def distribution(amounts: Sequence[Decimal]) -> list[Decimal]:
    """Give the shares of the amounts of a distribution, which sum exactly to one.

    The total of the amounts is not nought; the remainder of the roundings is carried by the
    largest amount, the first on a tie.
    """
    total = sum(amounts, NOUGHT)
    shares = [share_of(amount, total) for amount in amounts]
    largest = max(range(len(amounts)), key=lambda index: (amounts[index], -index))
    shares[largest] += ONE - sum(shares, NOUGHT)
    return shares


def shown(share: Decimal) -> str:
    """Give a share as the contract writes a decimal: without trailing zeros, ``1`` for one."""
    return format(share.normalize(), "f")
