# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual cost of a project: the sums of its tracked lines, which the indicators read.

``actual_cost_by_subproject`` sums the tracked lines of a project by the subproject they are
imputed to, the lines imputed to the project alone under ``UNASSIGNED``: the indicators of the
remaining to commit read it (US-1600). ``actual_costs_until`` sums the tracked lines of a
scope whose document is dated on or before a day, as known at the reading: the indicators of the
project read it (EP-10), served by US-1610/L2, which applies the imports (EP-09, "Ce que le cadrage
laisse à EP-10"). An excluded line enters neither (WF-CRE-0030).

Declared by US-1580/L1 with their arguments and their results, which EP-10 reads; each raises
``NotImplementedError`` naming the story that fills it, until it does: ``actual_costs_until`` is
filled by US-1610/L2.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import func, select

from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date

    from sqlalchemy.orm import Session

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
    """Give the sum of the tracked lines of a project by subproject, or under ``UNASSIGNED``."""
    msg = "actual_cost_by_subproject is filled by US-1600"
    raise NotImplementedError(msg)


def actual_costs_until(
    session: Session, project_id: UUID, until: date, scope: CostScope
) -> Decimal:
    """Give the sum of the tracked lines of a scope of a project dated on or before ``until``.

    The scope is the whole project (``PROJECT``), the lines imputed to the project alone
    (``UNASSIGNED``) or those of a subproject (its identifier); a scope without a line sums to
    nought. An excluded line enters it not (WF-CRE-0030), a credit diminishes it (WF-CRE-0010).
    """
    criteria = [
        CostLine.project_id == project_id,
        CostLine.is_in_tracked_scope,
        CostLine.document_date <= until,
    ]
    if isinstance(scope, UUID):
        criteria.append(CostLine.subproject_id == scope)
    elif scope == UNASSIGNED:
        criteria.append(CostLine.subproject_id.is_(None))
    total = session.scalar(select(func.sum(CostLine.amount)).where(*criteria))
    return total if total is not None else Decimal(0)
