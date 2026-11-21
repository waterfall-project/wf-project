# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The S-curve of the portfolio (``getPortfolioCostCurve``; US-2740).

The curves of the projects In progress or Completed — the documents ``cost_curve`` and
``cost_curve_payment_delays`` of the indicators (EP-10), those ``getCostCurve`` gives on the current
day, those their last marking kept at a past date — and, for an offer, ``portfolio_offer_curves``
weighted by its probability of winning, summed month by month over the twelve months before that of
the date of calculation and the ``horizon_months`` months from it, whatever the period, which only
chooses the projects Completed (``resolve_scope``, G-05). Nothing is calculated again (WF-PTF-0100):
a point of the S-curve is the sum, over the projects, of the point of theirs at that date, each
rounded once.

A curve of a project is cumulative and stepped at its points: its value at a date is that of its
last point on or before it (``value_at``), nought before its first and its final value after its
last — a series without points, a project that kept no curves, adds nothing. The reference budget is
read at the end of each month of the window; the actual cost at the end of each month before the
date of calculation and at that date; the projection of the project manager at that date and at the
end of each month after it. With the payment delays the series are those of the cash-out of each
project, and ``cash_out_by_month`` sums the details of theirs by month, a month of the window none
holds being nought; without them it is null.

Declared by US-2670/L1, the socle of EP-11; filled by US-2740.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.interface import IndicatorKind, IndicatorsReading, cost_curve
from waterfall.core.portfolio.aggregation import (
    ZERO_AMOUNT,
    last_day_of,
    month_label,
    months_window,
    sum_by_key,
    sum_by_month,
    value_at,
    weighted_amount,
)
from waterfall.core.portfolio.contributing import OFFER_CURVES
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.interface.scope import PeriodRule, resolve_scope
from waterfall.core.portfolio.shaping import money, scope_document
from waterfall.core.portfolio.states import COMPLETED, IN_PROGRESS, PRICING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.interface import Month
    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import (
        PortfolioAsked,
        PortfolioReading,
        ResolvedScope,
    )
    from waterfall.core.projects.interface import ProjectState

COUNTED: frozenset[ProjectState] = frozenset({IN_PROGRESS, PRICING, COMPLETED})
# The months before that of the date of calculation the curve always starts from (G-04).
MONTHS_BEFORE = 12


@dataclass(frozen=True, slots=True)
class _Curve:
    """The curves of a project: its document ``CurveSeries`` and its weight in the sums."""

    document: Document
    weight: Decimal


def _curves(
    session: Session, resolved: ResolvedScope, reading: PortfolioReading, kind: IndicatorKind
) -> list[_Curve]:
    """Give the curves of the projects retained that have some, by the kind of curve asked.

    A project In progress or Completed gives its own: on the current day what ``getCostCurve``
    gives, from the cache of ``reading`` when it has one, at a past date what the last revision
    marked by then kept. An offer gives the curves of its estimate, those of ``kind``, weighted by
    its probability of winning. A project with no revision to contribute by, a weight unknown, or
    a revision that kept no curves — marked before it was In progress, before EP-11 for an offer —
    gives none.
    """
    weights = {
        project_id: each.weight
        for project_id, each in resolved.projects.items()
        if each.revision_id is not None and each.weight is not None
    }
    retained = {key: each for key, each in resolved.projects.items() if key in weights}
    offers = {key: each for key, each in retained.items() if each.state == PRICING}
    own = [key for key in retained if key not in offers]
    if resolved.on_current_day:
        held = documents_of(session, replace(resolved, projects=offers), reading, (OFFER_CURVES,))
        asked = IndicatorsReading(PROJECT, reading.at)
        delayed = kind == "cost_curve_payment_delays"
        found = {
            key: cost_curve(session, key, asked, payment_delays=delayed, cache=reading.cache)
            for key in own
        }
    else:
        held = documents_of(
            session, replace(resolved, projects=retained), reading, (kind, OFFER_CURVES)
        )
        found = {key: held[key][kind] for key in own if kind in held[key]}
    curves = [_Curve(found[key], weights[key]) for key in own if key in found]
    curves.extend(
        _Curve(held[key][OFFER_CURVES][kind], weights[key])
        for key in offers
        if OFFER_CURVES in held.get(key, {})
    )
    return curves


def _series(document: Document, name: str) -> list[tuple[date, Decimal]]:
    """Give the points of a series of a document by date, in the order the document holds them."""
    for each in document["series"]:
        if each["name"] == name:
            return [(date.fromisoformat(p["date"]), Decimal(p["amount"])) for p in each["points"]]
    return []


def _summed(
    curves: Sequence[_Curve], name: str, days: Sequence[date]
) -> list[dict[str, str | None]]:
    """Give the points of the sum of a series at the days asked: each project's, rounded once."""
    parts: list[dict[date, Decimal]] = []
    for each in curves:
        points = _series(each.document, name)
        parts.append({day: weighted_amount(value_at(points, day), each.weight) for day in days})
    sums = sum_by_key(parts)
    return [{"date": day.isoformat(), "amount": money(sums.get(day, ZERO_AMOUNT))} for day in days]


def _cash_out_of(curve: _Curve, window: Sequence[Month], field: str) -> Mapping[Month, Decimal]:
    """Give the weighted cash-out of a project, ``past`` or ``forecast``, by month of the window."""
    rows: list[Mapping[str, str]] = curve.document["cash_out_by_month"] or []
    detail = {each["month"]: each for each in rows}
    return {
        month: weighted_amount(Decimal(detail[month_label(month)][field]), curve.weight)
        for month in window
        if month_label(month) in detail
    }


def _cash_out(curves: Sequence[_Curve], window: Sequence[Month]) -> list[dict[str, str | None]]:
    """Give the cash-out of each month of the window: the past and the forecast, summed."""
    paid = sum_by_month([_cash_out_of(each, window, "past") for each in curves], window)
    to_pay = sum_by_month([_cash_out_of(each, window, "forecast") for each in curves], window)
    return [
        {"month": month_label(month), "past": money(past), "forecast": money(forecast)}
        for month, past, forecast in zip(window, paid, to_pay, strict=True)
    ]


def read_portfolio_cost_curve(
    session: Session,
    asked: PortfolioAsked,
    reading: PortfolioReading,
    *,
    horizon_months: int,
    payment_delays: bool,
) -> Document:
    """Give the S-curve of the scope read by ``reading``, over its horizon."""
    resolved = resolve_scope(session, asked, reading.at, counted=COUNTED, period=PeriodRule())
    day = resolved.scope.as_of
    window = months_window(day, before=MONTHS_BEFORE, horizon=horizon_months)
    ends = [last_day_of(month) for month in window]
    kind: IndicatorKind = "cost_curve_payment_delays" if payment_delays else "cost_curve"
    curves = _curves(session, resolved, reading, kind)
    return {
        "scope": scope_document(resolved.scope),
        "payment_delays": payment_delays,
        "series": [
            {"name": "reference_budget", "points": _summed(curves, "reference_budget", ends)},
            {
                "name": "actual_cost",
                "points": _summed(
                    curves, "actual_cost", [*(end for end in ends if end < day), day]
                ),
            },
            {
                "name": "project_manager_projection",
                "points": _summed(
                    curves, "project_manager_projection", [day, *(end for end in ends if end > day)]
                ),
            },
        ],
        "cash_out_by_month": _cash_out(curves, window) if payment_delays else None,
    }
