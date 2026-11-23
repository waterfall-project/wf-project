# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of a cumulative curve at a day (WF-PTF-0100, US-2740).

Pure. A curve of a project (EP-10) is cumulative and drawn at its points, one by end of month: it
has no value of its own between two of them.
"""

from typing import TYPE_CHECKING

from waterfall.core.portfolio.aggregation.sums import ZERO_AMOUNT

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
    from decimal import Decimal


def value_at(points: Sequence[tuple[date, Decimal]], day: date) -> Decimal:
    """Give a cumulative curve at a day: its last point on or before that day.

    The points are in the order the curve holds them, by date. Before its first point a curve is
    nought; after its last it keeps its final value (a project over stays at its cumulative); of
    two points at one date the later in the order stands (a step of the reference budget); a curve
    without points is nought at every day.
    """
    value = ZERO_AMOUNT
    for when, amount in points:
        if when <= day:
            value = amount
    return value
