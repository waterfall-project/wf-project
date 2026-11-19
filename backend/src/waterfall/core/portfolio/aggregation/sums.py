# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The sums of the portfolio: of amounts already rounded, by key, by month (WF-PTF-0020).

Pure. A portfolio figure is the sum of the figures of the projects, each rounded once as EP-10
rounds it; the sum is not rounded again, so that each point of an aggregated curve equals the sum
of the points of the projects (WF-PTF-0100).
"""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from waterfall.core.estimate.interface import Month

NOUGHT = Decimal(0)
# The zero of a sum of amounts, written as they are: two decimals.
ZERO_AMOUNT = Decimal("0.00")


def total_of(amounts: Iterable[Decimal]) -> Decimal:
    """Give the sum of amounts, the zero of an empty sum written ``0.00``."""
    return sum(amounts, ZERO_AMOUNT)


def sum_by_key[K](parts: Iterable[Mapping[K, Decimal]]) -> dict[K, Decimal]:
    """Give the sum, key by key, of the amounts of several projects, in the order keys appear."""
    sums: dict[K, Decimal] = {}
    for each in parts:
        for key, amount in each.items():
            sums[key] = sums.get(key, ZERO_AMOUNT) + amount
    return sums


def count_by_key[K](keys: Iterable[K]) -> dict[K, int]:
    """Count the items by key, in the order keys appear: the risks of a cell of the matrix."""
    counts: dict[K, int] = {}
    for key in keys:
        counts[key] = counts.get(key, 0) + 1
    return counts


def sum_by_month(
    series: Iterable[Mapping[Month, Decimal]], months: Sequence[Month]
) -> list[Decimal]:
    """Give the sum of the series for each month asked, a month none holds being ``0.00``.

    A month the series hold and that is not asked — before the window, after the horizon — is
    left out: the window is the view's, not the projects'.
    """
    asked = set(months)
    sums = dict.fromkeys(months, ZERO_AMOUNT)
    for each in series:
        for month, amount in each.items():
            if month in asked:
                sums[month] += amount
    return [sums[month] for month in months]
