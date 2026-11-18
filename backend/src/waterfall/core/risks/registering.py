# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The register of the risks of a project, private to the module (``listRisks``; US-2600/L1).

The risks a revision holds, each read as ``getRisk`` reads it (``reading.risk_view``), so that the
register and the detail never disagree on a column: kept by the filters on each column, sorted,
totalled — all the risks the filters retain, whatever the page (WF-IHM-0130, #1367) — then
paginated. The label is searched in the database, as every search of the contract is (``unaccent``,
README); every other column is judged on the value the risk is read at, which is computed (severity,
provision, zone, reestimated amount) and so is in no column of a table.

- the provisions are summed by state: the identified at their current provision, the occurred and
  the dismissed at the share they held in the reference (WF-RIS-0040, H-03), and the reserve beside
  them is that of the coverage of the revision read (WF-RIS-0050), which US-2610 answers;
- a risk with neither a cost at occurrence nor a reestimated amount, as one identified or dismissed
  is, is retained by no bound of these columns, and sorts like a null: after the others in the
  ascending order, before them in the descending one (#1761);
- the order unsorted is that of the declaration of the risks; a tie keeps it (WF-IHM-0060), the
  descending order too, which reverses the comparison and not the list.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.interface import risk_coverage
from waterfall.core.revisions.interface import (
    current_revision,
    last_marked_revision,
    read_revision_for,
)
from waterfall.core.risks.reading import NOUGHT, Found, risk_view
from waterfall.core.risks.tables import Risk, RiskEvaluation
from waterfall.core.risks.views import ProvisionTotals, RiskList
from waterfall.platform.database import contains

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import (
        Bounds,
        RiskColumn,
        RiskFilters,
        RiskPage,
        RiskSort,
        RiskState,
        RiskView,
    )

# What a sort compares: a text, a number, or a value that may be null, the null last.
type SortKey = str | int | Decimal | tuple[bool, Decimal] | tuple[bool, date]

# The states in the order the contract gives them, which the sort on the state follows.
STATE_ORDER: dict[RiskState, int] = {"identified": 0, "occurred": 1, "dismissed": 2}


def _within[T: (Decimal, date)](value: T | None, bounds: Bounds[T]) -> bool:
    """Tell whether a value is between the bounds given, each included; none is within no bound."""
    if bounds.least is None and bounds.most is None:
        return True
    if value is None:
        return False
    return (bounds.least is None or value >= bounds.least) and (
        bounds.most is None or value <= bounds.most
    )


def _kept(view: RiskView, filters: RiskFilters) -> bool:
    """Tell whether the filters retain a risk: every column asked for, all together."""
    return (
        (filters.states is None or view.state in filters.states)
        and (filters.zones is None or view.matrix_cell.zone in filters.zones)
        and _within(view.probability, filters.probability)
        and _within(view.severity, filters.severity)
        and _within(view.provision_amount, filters.provision_amount)
        and _within(view.occurrence_cost, filters.occurrence_cost)
        and _within(view.occurred_reestimated_amount, filters.occurred_reestimated_amount)
        and _within(view.last_review_on, filters.last_review_on)
    )


def _amount_or_null(value: Decimal | None) -> tuple[bool, Decimal]:
    """Give what a sort compares of an amount that may be null: the null after the others."""
    return (value is None, NOUGHT if value is None else value)


def _day_or_null(value: date | None) -> tuple[bool, date]:
    """Give what a sort compares of a day that may be null: the null after the others."""
    return (value is None, date.min if value is None else value)


def _keys() -> dict[RiskColumn, Callable[[RiskView], SortKey]]:
    """Give what a sort on each column compares in a risk."""
    return {
        "label": lambda view: view.label,
        "probability": lambda view: view.probability,
        "severity": lambda view: view.severity,
        "provision_amount": lambda view: view.provision_amount,
        "occurrence_cost": lambda view: _amount_or_null(view.occurrence_cost),
        "occurred_reestimated_amount": lambda view: _amount_or_null(
            view.occurred_reestimated_amount
        ),
        "state": lambda view: STATE_ORDER[view.state],
        "last_review_on": lambda view: _day_or_null(view.last_review_on),
    }


def _sorted(views: list[RiskView], sort: RiskSort) -> list[RiskView]:
    """Sort the risks by a column, the declaration kept between equals; none: as declared.

    ``sorted`` is stable, also reversed: equals keep the order of the declaration, as the order
    unsorted breaks a tie (WF-IHM-0060).
    """
    if sort.key is None:
        return views
    return sorted(views, key=_keys()[sort.key], reverse=sort.descending)


def _totals(
    views: list[RiskView], session: Session, project_id: UUID, revision_id: UUID
) -> ProvisionTotals:
    """Sum the provisions of the risks retained by state, and give the reserve beside them."""
    by_state = dict.fromkeys(STATE_ORDER, NOUGHT)
    for view in views:
        by_state[view.state] += view.provision_amount
    return ProvisionTotals(
        identified=by_state["identified"],
        occurred=by_state["occurred"],
        dismissed=by_state["dismissed"],
        total=sum(by_state.values(), NOUGHT),
        reserve=risk_coverage(session, project_id, revision_id).reserve,
    )


def _found(
    session: Session, project_id: UUID, revision_id: UUID, search: str | None
) -> list[Found]:
    """Read the risks a revision holds, in the order of their declaration, the label searched."""
    query = (
        select(Risk, RiskEvaluation)
        .join(
            RiskEvaluation,
            (RiskEvaluation.project_id == Risk.project_id) & (RiskEvaluation.risk_id == Risk.id),
        )
        .where(Risk.project_id == project_id, RiskEvaluation.revision_id == revision_id)
        .order_by(Risk.created_at, Risk.id)
        .execution_options(populate_existing=True)
    )
    if search is not None:
        query = query.where(contains(Risk.label, search))
    return [Found(risk, evaluation) for risk, evaluation in session.execute(query)]


def read_register(
    session: Session,
    project_id: UUID,
    query: tuple[RiskFilters, RiskSort, RiskPage],
    viewer: Viewer,
) -> RiskList:
    """Read a page of the register of a project in a revision, and the totals of those retained.

    The revision named, else the current, else the last marked (404 for one of another project); a
    project with none holds no risk, and its register is empty, its totals nought.
    """
    filters, sort, page = query
    if (
        filters.revision_id is None
        and current_revision(session, project_id) is None
        and last_marked_revision(session, project_id) is None
    ):
        empty = ProvisionTotals(NOUGHT, NOUGHT, NOUGHT, NOUGHT, NOUGHT)
        return RiskList([], 0, empty)
    revision_id = read_revision_for(session, project_id, filters.revision_id).revision_id
    views = [
        view
        for view in (
            risk_view(session, project_id, found, viewer)
            for found in _found(session, project_id, revision_id, filters.search)
        )
        if _kept(view, filters)
    ]
    ordered = _sorted(views, sort)
    totals = _totals(views, session, project_id, revision_id)
    return RiskList(ordered[page.offset : page.offset + page.limit], len(ordered), totals)
