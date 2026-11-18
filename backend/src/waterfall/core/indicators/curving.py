# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of a scope of a project at a day, from one read (EP-10, "Les courbes").

The tasks, the lines of the revision computed R and of the reference Ref, the remaining to commit
of R are read once for all the scopes (``read_curve_sources``), the tracked lines of cost of each
scope after (``curves_of_scope``); the series are then drawn from them without the database
(``cost_curve_document``, ``earned_value_curves_document``), at the pace of the month, each line by
its parts rounded to the cent, as the estimate rounds them (WF-IND-0100, WF-IND-0110; US-1690/L4):

- ``reference_budget`` and ``planned_value``, the budgeted amounts of the lines of Ref of the scope
  spread over their tasks as Ref dates them, cumulated by month-end;
- ``earned_value``, those of the lines whose task is completed in R, by month of completion up to
  the day, a task of an occurred risk apart;
- ``actual_cost``, the tracked lines by month of their document up to the day;
- ``project_manager_projection``, from the actual cost at the day, the remaining to commit of each
  line of R spread over the part of its task after the day.

With the payment delays, the budget and the projection are those of the cash-out, each line shifted
by its own delay, the actual cost not; ``cash_out_by_month`` details it. A scope without a line in
Ref or in R and without cost has nothing to draw: its series have no point.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.costs.interface import actual_cost_dates
from waterfall.core.estimate.interface import remaining_of_lines
from waterfall.core.indicators.computing import Basis, completions, in_scope, read_lines
from waterfall.core.indicators.series import (
    CashOutMonth,
    Point,
    Spreader,
    SpreadLine,
    cash_out_by_month,
    cumulative,
    cumulative_from,
    cumulative_until,
    events_by_month,
    month_of,
    spread_lines,
)
from waterfall.core.indicators.shaping import context_document, money

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.estimate.interface import IndicatorLine, Month
    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.shaping import Context

type Dated = Sequence[tuple[date, Decimal]]


@dataclass(frozen=True, slots=True)
class CurveReading:
    """What the curves of a scope are drawn from, at a day.

    ``reference`` are the lines of Ref of the scope, ``lines`` those of R with the remaining to
    commit of each, ``earned`` the budgeted amounts of the lines of Ref earned, by day of
    completion, ``costs`` the tracked lines of the scope by day of document, up to the day;
    ``spreader`` that of the computation, which spreads each line once for all its curves.
    """

    day: date
    reference: tuple[IndicatorLine, ...]
    lines: tuple[tuple[IndicatorLine, Decimal], ...]
    earned: Dated
    costs: Dated
    spreader: Spreader = field(default_factory=Spreader, compare=False)

    @property
    def is_drawn(self) -> bool:
        """Tell whether the scope has anything to draw: a line in Ref or in R, or a cost."""
        return bool(self.reference or self.lines or self.costs)


@dataclass(frozen=True, slots=True)
class CurveSources:
    """What the curves of every scope of a basis are drawn from, read once.

    The lines of Ref and of R, the remaining to commit of each line of R, the day of completion
    of the tasks completed in R: what does not depend on the scope; the spreader every scope
    shares, each line spread once for all of them (#3902).
    """

    reference: tuple[IndicatorLine, ...]
    lines: tuple[IndicatorLine, ...]
    remaining: Mapping[UUID, Decimal]
    completed: Mapping[UUID, date]
    spreader: Spreader = field(default_factory=Spreader, compare=False)


def read_curve_sources(session: Session, basis: Basis) -> CurveSources:
    """Read, once for all the scopes, the lines, the remaining and the completions of a basis."""
    tasks, lines, reference = read_lines(session, basis)
    remaining = remaining_of_lines(tasks, lines).by_line
    return CurveSources(tuple(reference), tuple(lines), remaining, completions(tasks))


def curves_of_scope(
    session: Session, project_id: UUID, sources: CurveSources, day: date, scope: CostScope
) -> CurveReading:
    """Give what the curves of a scope are drawn from at a day: the sources, narrowed to it.

    Only the tracked lines of cost of the scope, in the project, are read here.
    """
    budgeted = tuple(line for line in sources.reference if in_scope(scope, line.subproject_id))
    earned = [
        (done, line.budgeted_amount)
        for line in budgeted
        if line.task_origin_risk_id is None
        and (done := sources.completed.get(line.task_lineage_id)) is not None
    ]
    return CurveReading(
        day,
        budgeted,
        tuple(
            (line, sources.remaining.get(line.node_id, Decimal(0)))
            for line in sources.lines
            if in_scope(scope, line.subproject_id)
        ),
        earned,
        actual_cost_dates(session, project_id, day, scope),
        sources.spreader,
    )


def read_curves(session: Session, basis: Basis, day: date, scope: CostScope) -> CurveReading:
    """Read what the curves of a scope are drawn from, at a day, on the revisions of a basis."""
    sources = read_curve_sources(session, basis)
    return curves_of_scope(session, basis.project_id, sources, day, scope)


def _budget(reading: CurveReading, *, delayed: bool) -> tuple[dict[Month, Decimal], list[Point]]:
    """Return the parts of the reference budget by month, and its cumulative series.

    The series runs on to the month of the end of the last task, shifted by its delay: it reaches
    the budget there and does not move after (WF-IND-0100, WF-IND-0110).
    """
    spreads = [
        SpreadLine(line.budgeted_amount, line.placement, line.payment_delay_days)
        for line in reading.reference
    ]
    shares = spread_lines(spreads, delayed=delayed, spreader=reading.spreader)
    ends = [
        line.placement.finish.day + _delay(line.payment_delay_days, delayed=delayed)
        for line in reading.reference
    ]
    return shares, cumulative(shares, through=max(ends, default=None))


def _delay(days: int, *, delayed: bool) -> timedelta:
    return timedelta(days=days if delayed else 0)


def _costs(reading: CurveReading, shares: Mapping[Month, Decimal]) -> list[Point]:
    """Return the actual cost up to the day, drawn from the origin of the budget when it has one.

    A scope that has lines and no document is drawn at zero (WF-IND-0100); one with nothing to
    draw has no point.
    """
    if not reading.is_drawn:
        return []
    origin = min(shares) if shares else month_of(reading.day)
    return cumulative_until(reading.costs, reading.day, from_month=origin)


def _total(events: Iterable[tuple[date, Decimal]]) -> Decimal:
    return sum((amount for _, amount in events), Decimal(0))


def _series(name: str, points: Iterable[Point]) -> dict[str, object]:
    return {
        "name": name,
        "points": [
            {"date": point.day.isoformat(), "amount": money(point.amount)} for point in points
        ],
    }


def _cash_out_document(months: Iterable[CashOutMonth]) -> list[dict[str, str]]:
    return [
        {
            "month": f"{each.month.year:04d}-{each.month.month:02d}",
            "past": money(each.past),
            "forecast": money(each.forecast),
        }
        for each in months
    ]


def cost_curve_document(
    reading: CurveReading, context: Context, *, payment_delays: bool
) -> Document:
    """Write the cumulative costs of a scope as the contract writes them (``CurveSeries``).

    The reference budget, the actual cost up to the day, then the projection of the project
    manager, which starts there and ends at the actual cost plus the remaining to commit; with the
    payment delays, the cash-out by month besides (WF-IND-0100). No step: the amendments are
    those of the risks and revisions of EP-08.
    """
    day = reading.day
    shares, budget = _budget(reading, delayed=payment_delays)
    to_come = spread_lines(
        (
            SpreadLine(left, line.placement, line.payment_delay_days)
            for line, left in reading.lines
            if left != 0
        ),
        as_of=day,
        delayed=payment_delays,
        spreader=reading.spreader,
    )
    projection = cumulative_from(to_come, day, _total(reading.costs)) if reading.is_drawn else []
    cash_out = None
    if payment_delays:
        past = events_by_month(reading.costs, until=day)
        cash_out = _cash_out_document(cash_out_by_month(past, to_come))
    return {
        "context": context_document(context),
        "payment_delays": payment_delays,
        "series": [
            _series("reference_budget", budget),
            _series("actual_cost", _costs(reading, shares)),
            _series("project_manager_projection", projection),
        ],
        "steps": [],
        "cash_out_by_month": cash_out,
    }


def earned_value_curves_document(reading: CurveReading, context: Context) -> Document:
    """Write the curves of the earned value of a scope as the contract writes them.

    The planned value, to the end of the reference; the earned value, by month of completion; the
    actual cost, by month of document, both up to the day (WF-IND-0110).
    """
    shares, planned = _budget(reading, delayed=False)
    origin = min(shares) if shares else month_of(reading.day)
    earned = (
        cumulative_until(reading.earned, reading.day, from_month=origin) if reading.is_drawn else []
    )
    return {
        "context": context_document(context),
        "payment_delays": False,
        "series": [
            _series("planned_value", planned),
            _series("earned_value", earned),
            _series("actual_cost", _costs(reading, shares)),
        ],
        "steps": [],
        "cash_out_by_month": None,
    }
