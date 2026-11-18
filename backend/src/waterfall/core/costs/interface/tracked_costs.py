# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual cost of a project: the sums of its tracked lines, which the indicators read.

``actual_cost_by_subproject`` sums the tracked lines of a project by the subproject they are
imputed to, the lines imputed to the project alone under ``UNASSIGNED``: the indicators of the
remaining to commit read it (US-1600). ``actual_costs_until`` sums the tracked lines of a
scope whose document is dated on or before a day, as known at the reading: the indicators of the
project read it (EP-10), served by US-1610/L2, which applies the imports (EP-09, "Ce que le cadrage
laisse à EP-10"); ``actual_cost_dates`` gives them by day of document, for the curves (US-1690/L2).
``actual_costs_until_by_subproject`` gives the sums of every scope at a day in one statement, by
subproject as ``actual_cost_by_subproject`` does, and ``scope_cost`` draws one scope from them: the
indicators of several scopes read the actual cost once (#3569, #3802). An excluded line enters none
(WF-CRE-0030).

Declared by US-1580/L1 with their arguments and their results, which EP-10 reads:
``actual_costs_until`` is filled by US-1610/L2, ``actual_cost_by_subproject`` by US-1600.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import func, select

from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import date

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import InstrumentedAttribute, Session

# The two scopes a sum names by a word, as the contract does (``CalculationContext.scope``,
# WF-IND-0020), never by ``None``: every line of the project, whatever its imputation; the lines
# imputed to the project alone — without a subproject part in their WBS element, or with a code no
# subproject bears (WF-CRE-0020).
PROJECT = "project"
UNASSIGNED = "unassigned"
# The lines a sum keeps: those of the whole project, of a subproject (its identifier), or of the
# project alone.
type CostScope = UUID | Literal["project", "unassigned"]
# What a sum by subproject is keyed by: a subproject, or the project alone.
type CostKey = UUID | Literal["unassigned"]


def actual_cost_by_subproject(session: Session, project_id: UUID) -> Mapping[CostKey, Decimal]:
    """Give the sum of the tracked lines of a project by subproject, or under ``UNASSIGNED``.

    A subproject or the project alone without a tracked line is absent; an excluded line enters
    nothing (WF-CRE-0030), a credit diminishes its sum (WF-CRE-0010).
    """
    rows = session.execute(
        select(CostLine.subproject_id, func.sum(CostLine.amount))
        .where(CostLine.project_id == project_id, CostLine.is_in_tracked_scope)
        .group_by(CostLine.subproject_id)
    )
    return {UNASSIGNED if key is None else key: total for key, total in rows}


def _tracked_until(
    project_id: UUID, until: date, scope: CostScope
) -> Sequence[ColumnElement[bool] | InstrumentedAttribute[bool]]:
    """Give the criteria of the tracked lines of a scope dated on or before a day."""
    criteria = [
        CostLine.project_id == project_id,
        CostLine.is_in_tracked_scope,
        CostLine.document_date <= until,
    ]
    if isinstance(scope, UUID):
        criteria.append(CostLine.subproject_id == scope)
    elif scope == UNASSIGNED:
        criteria.append(CostLine.subproject_id.is_(None))
    return criteria


def actual_costs_until(
    session: Session, project_id: UUID, until: date, scope: CostScope
) -> Decimal:
    """Give the sum of the tracked lines of a scope of a project dated on or before ``until``.

    The scope is the whole project (``PROJECT``), the lines imputed to the project alone
    (``UNASSIGNED``) or those of a subproject (its identifier); a scope without a line sums to
    nought. An excluded line enters it not (WF-CRE-0030), a credit diminishes it (WF-CRE-0010).
    """
    criteria = _tracked_until(project_id, until, scope)
    total = session.scalar(select(func.sum(CostLine.amount)).where(*criteria))
    return total if total is not None else Decimal(0)


def actual_costs_until_by_subproject(
    session: Session, project_id: UUID, until: date
) -> Mapping[CostKey, Decimal]:
    """Give the tracked lines of a project dated on or before ``until``, summed by subproject.

    In one statement, keyed as ``actual_cost_by_subproject`` is: a subproject, or the lines imputed
    to the project alone under ``UNASSIGNED``; one without a line so dated is absent. The sum of a
    scope is drawn from them by ``scope_cost``, equal to ``actual_costs_until`` of that scope.
    """
    rows = session.execute(
        select(CostLine.subproject_id, func.sum(CostLine.amount))
        .where(*_tracked_until(project_id, until, PROJECT))
        .group_by(CostLine.subproject_id)
    )
    return {UNASSIGNED if key is None else key: total for key, total in rows}


def scope_cost(by_subproject: Mapping[CostKey, Decimal], scope: CostScope) -> Decimal:
    """Give the sum of a scope from the sums by subproject: all of them for the whole project.

    A scope without a sum is nought, as ``actual_costs_until`` gives it.
    """
    if scope == PROJECT:
        return sum(by_subproject.values(), Decimal(0))
    return by_subproject.get(scope, Decimal(0))


def actual_cost_dates(
    session: Session, project_id: UUID, until: date, scope: CostScope
) -> list[tuple[date, Decimal]]:
    """Give the tracked lines of a scope dated on or before ``until``, summed by document date.

    Those ``actual_costs_until`` sums, by the day of their document, the earliest first: what a
    curve of the actual cost is drawn from (WF-IND-0100). A day without a line is absent.
    """
    criteria = _tracked_until(project_id, until, scope)
    rows = session.execute(
        select(CostLine.document_date, func.sum(CostLine.amount))
        .where(*criteria)
        .group_by(CostLine.document_date)
        .order_by(CostLine.document_date)
    )
    return [(day, total) for day, total in rows]
