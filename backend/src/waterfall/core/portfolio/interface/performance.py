# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The performance of the portfolio (``getPortfolioPerformance``; US-2710).

The quantities of the documents ``project`` of the projects In progress summed, then the formulas of
the indicators applied to the sums — an index of the portfolio is a ratio of sums, never an average
of indices (WF-PTF-0020) —, the variances, the three projections, the distribution by zone, and the
evolution by quarter, each past quarter read at its last day (WF-PTF-0070).

Only the projects In progress contribute, whatever the view is asked to retain besides: ``counted``
is that one state, ``scope.states`` naming the states asked (G-14). A project contributes the
document ``project`` of its revision retained: on the current day, the indicators of the day of
EP-10, read in the cache of the indicators under the fingerprint of the project; at a past date,
the document its last revision marked by then kept, which no line of a task or of a quote is read
for (WF-DAT-0040). A project that kept none — an offer, a marking before EP-10 — contributes
nothing, and is in no zone. The sums are those of amounts already rounded (``aggregate``); the
zones are classified at the reading, on the thresholds of the reference of the day (WF-REF-0170).

The evolution has one point per civil quarter the period touches, the oldest first, each read on
the last day of the quarter — on the date of calculation for the quarter that holds it, whose
indices are those of the top of the answer — as the projects were then In progress. A quarter with
no project In progress sums nothing: its indices are not computable, for lack of a denominator.

Declared by US-2670/L1, the socle of EP-11; filled by US-2710.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from waterfall.core.cost_settings.interface import plain_decimal, read_reference_settings
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.interface import (
    Computable,
    current_day_reading,
    day_indicators,
    kept_documents_of,
    zone_of,
)
from waterfall.core.portfolio.aggregation import (
    ProjectFigures,
    aggregate,
    quarters_touched,
    reading_day,
    zone_distribution,
)
from waterfall.core.portfolio.interface.scope import PeriodRule, resolve_scope

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, datetime

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import IndexThresholds
    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.aggregation import Aggregate
    from waterfall.core.portfolio.interface.scope import (
        PortfolioAsked,
        PortfolioReading,
        PortfolioScope,
        ResolvedScope,
    )
    from waterfall.core.projects.interface import ProjectState
    from waterfall.platform.cache import IndicatorsCache

# The one state the view counts: the others, asked or not, contribute to no sum.
COUNTED: frozenset[ProjectState] = frozenset({"in_progress"})
COST, SCHEDULE = "cost", "schedule"
# The longest period the view reads, in years: one document kept per civil quarter it touches, so
# that a longer one is refused (422 ``VALUE_OUT_OF_RANGE``; #4176, ``PortfolioFrom``).
PERIOD_YEARS = 5


def _money(amount: Decimal) -> str:
    """Write an amount as ``Money`` of the contract: to the cent."""
    return format(amount, "f")


def _computable(figure: Computable, *, in_cents: bool = False) -> dict[str, Any]:
    """Write a figure as ``Computable`` of the contract; an amount to the cent, a ratio plain."""
    value = figure.value
    shown = None if value is None else (_money(value) if in_cents else plain_decimal(value))
    return {"is_computable": value is not None, "value": shown, "reason": figure.reason}


def _index(figure: Computable, watch: Decimal, alert: Decimal) -> dict[str, Any]:
    """Write an index and its zone, classified on the thresholds read now."""
    return {"value": _computable(figure), "zone": zone_of(figure, watch, alert)}


def _scope(scope: PortfolioScope) -> dict[str, Any]:
    """Write the scope retained as ``PortfolioScope`` of the contract."""
    return {
        "states": list(scope.states),
        "as_of": scope.as_of.isoformat(),
        "from": None if scope.period_from is None else scope.period_from.isoformat(),
        "to": None if scope.period_to is None else scope.period_to.isoformat(),
        "org_node_id": None if scope.org_node_id is None else str(scope.org_node_id),
        "org_node_label": scope.org_node_label,
        "project_count": scope.project_count,
    }


@dataclass(frozen=True, slots=True)
class _Reading:
    """What a reading is made on: the session, the instant, the cache of the day."""

    session: Session
    at: datetime
    cache: IndicatorsCache | None

    def documents(self, resolved: ResolvedScope) -> list[Document]:
        """Give the document ``project`` of each project retained that has one, in no set order.

        On the current day the indicators of the day of the project, from the cache when one is
        given; at a past date those its retained revision kept, all read in one statement.
        """
        revisions = {
            project_id: each.revision_id
            for project_id, each in resolved.projects.items()
            if each.revision_id is not None
        }
        if resolved.on_current_day:
            reading = [current_day_reading(self.session, each, self.at) for each in revisions]
            return [
                day_indicators(self.session, each, (PROJECT,), self.cache)[PROJECT]
                for each in reading
            ]
        kept = kept_documents_of(self.session, set(revisions.values()), ("project",))
        return [kept[each]["project"] for each in revisions.values() if "project" in kept[each]]


def _figures(document: Document) -> ProjectFigures:
    """Give the rounded amounts a project gives to the sums."""
    return ProjectFigures(
        reference_budget=Decimal(document["reference_budget"]),
        earned_value=Decimal(document["earned_value"]),
        actual_cost=Decimal(document["actual_cost"]),
        planned_value=Decimal(document["planned_value"]),
        remaining=Decimal(document["remaining"]),
    )


def _index_of(document: Document, name: str) -> Computable:
    """Give the index a project kept or computed, as a figure that may not be computed."""
    held = document[name]["value"]
    if held["value"] is None:
        return Computable.not_computable(held["reason"])
    return Computable.of(Decimal(held["value"]))


def _distribution(
    documents: Sequence[Document], thresholds: IndexThresholds
) -> list[dict[str, Any]]:
    """Count the projects by zone of each index, the cost index first, each project once."""
    counted: list[dict[str, Any]] = []
    for index, name, watch, alert in (
        (COST, "cost_index", thresholds.cost_watch, thresholds.cost_alert),
        (SCHEDULE, "schedule_index", thresholds.schedule_watch, thresholds.schedule_alert),
    ):
        indices = [_index_of(each, name) for each in documents]
        counted.extend(
            {"index": index, "zone": each.zone, "project_count": each.project_count}
            for each in zone_distribution(indices, watch, alert)
        )
    return counted


def _projections(total: Aggregate) -> dict[str, Any]:
    """Write the projections of the sums: two sums, and the budget over the aggregated index."""
    held = total.projections
    observed = held.variance_at_observed_rate
    return {
        "at_budget": _money(held.at_budget),
        "project_manager": _money(held.project_manager),
        "at_observed_rate": _computable(held.at_observed_rate, in_cents=True),
        "variance_at_budget": _money(held.variance_at_budget),
        "variance_project_manager": _money(held.variance_project_manager),
        "variance_at_observed_rate": None if observed is None else _money(observed),
    }


def _evolution(
    reading: _Reading, asked: PortfolioAsked, scope: PortfolioScope, documents: Sequence[Document]
) -> list[dict[str, Any]]:
    """Give a point by civil quarter the period touches, each read on its last day.

    The quarter that holds the date of calculation — or any that has not ended by it — is read on
    that date, with the documents of the top of the answer; a past quarter is a date asked: the
    projects In progress that day, by the documents their last revision marked by then kept, the
    node dropped, which changes no figure.
    """
    bounds = cast("tuple[date, date]", (scope.period_from, scope.period_to))
    points: list[dict[str, Any]] = []
    for quarter in quarters_touched(*bounds):
        day = reading_day(quarter, scope.as_of)
        held = documents
        if day != scope.as_of:
            past = replace(asked, as_of=day, org_node_id=None)
            resolved = resolve_scope(
                reading.session, past, reading.at, counted=COUNTED, period=None
            )
            held = reading.documents(resolved)
        total = aggregate(_figures(each) for each in held)
        points.append(
            {
                "quarter": quarter.label,
                "cost_index": _computable(total.cost_index),
                "schedule_index": _computable(total.schedule_index),
            }
        )
    return points


def read_portfolio_performance(
    session: Session, asked: PortfolioAsked, reading: PortfolioReading
) -> Document:
    """Give the performance of the scope read by ``reading``; the day is read in its cache.

    Refuses a period or a node as every view of the portfolio does (422, ``resolve_scope``).
    """
    resolved = resolve_scope(
        session, asked, reading.at, counted=COUNTED, period=PeriodRule(PERIOD_YEARS)
    )
    scope = resolved.scope
    source = _Reading(session, reading.at, reading.cache)
    thresholds = read_reference_settings(session).index_thresholds
    documents = source.documents(resolved)
    total = aggregate(_figures(each) for each in documents)
    return {
        "scope": _scope(scope),
        "reference_budget": _money(total.reference_budget),
        "cost_index": _index(total.cost_index, thresholds.cost_watch, thresholds.cost_alert),
        "schedule_index": _index(
            total.schedule_index, thresholds.schedule_watch, thresholds.schedule_alert
        ),
        "cost_variance": _money(total.cost_variance),
        "schedule_variance": _money(total.schedule_variance),
        "projections": _projections(total),
        "zone_distribution": _distribution(documents, thresholds),
        "quarterly": _evolution(source, asked, scope, documents),
    }
