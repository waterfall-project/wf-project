# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of the estimate of an offer, drawn from its lines (EP-11, US-2680/L1b).

An offer has no actual cost and no reference but its own estimate: its curves are those of a
project (``cost_curve_document``, EP-10) on the lines of its estimate, without the database:

- ``reference_budget``, the budgeted amounts of its lines without the provision lines, cumulated
  by month-end;
- ``actual_cost``, none;
- ``project_manager_projection``, the remaining to commit of each line, provision lines included
  (the one rule of EP-08), spread from the day of the computation, on a base of nought;
- ``cash_out_by_month``, with the payment delays only.

The portfolio sums an offer as a project (US-2740).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from waterfall.core.indicators.curving import CurveReading, cost_curve_document

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import date
    from uuid import UUID

    from waterfall.core.estimate.interface import IndicatorLine
    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.shaping import Context

NOUGHT = Decimal(0)


def offer_curves_document(
    reference: Sequence[IndicatorLine],
    lines: Sequence[IndicatorLine],
    remaining: Mapping[UUID, Decimal],
    day: date,
    context: Context,
) -> Document:
    """Write the two curves of an offer: ``cost_curve`` and ``cost_curve_payment_delays``.

    ``reference`` are the lines of the estimate without the provision lines, ``lines`` all of them
    with ``remaining``, the remaining to commit of each by node.
    """
    reading = CurveReading(
        day,
        tuple(reference),
        tuple((line, remaining.get(line.node_id, NOUGHT)) for line in lines),
        earned=(),
        costs=(),
    )
    return {
        kind: _without_actual_cost(cost_curve_document(reading, context, payment_delays=delayed))
        for kind, delayed in (("cost_curve", False), ("cost_curve_payment_delays", True))
    }


def _without_actual_cost(curve: Document) -> Document:
    """Give a curve whose actual cost is empty: an offer has paid nothing."""
    named: list[dict[str, Any]] = curve["series"]
    series: list[dict[str, Any]] = [
        {**each, "points": []} if each["name"] == "actual_cost" else each for each in named
    ]
    return {**curve, "series": series}
