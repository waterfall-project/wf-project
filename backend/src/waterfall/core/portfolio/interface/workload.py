# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of the portfolio (``getPortfolioWorkload``; US-2700).

The documents ``portfolio_workload`` of the projects In progress and, when the pricing is asked, of
the offers, weighted — one for a project In progress, the probability of winning for an offer —,
summed by role and by month over the horizon; the roles retained — all the active ones, or those of
the node and its descendants, on the current tree —, and their capacity calculated (EP-10), the
rate of load and the zone of each month, under-load flagged as much as overload (WF-PTF-0060).

Only the projects In progress and, if asked, In pricing contribute: another state a request names,
Completed included, has no effect, and the view retains no period (``resolve_scope``, #1714). The
hours a document keeps are already rounded, and so is the weighted part of an offer, once, to the
hundredth: the plan sums hours as rounded, never rounds a sum again. A past date reads what the
revisions marked by then kept, with the capacity of the roles as it stands: the capacity is not a
document of a marking.

Declared by US-2670/L1, the socle of EP-11; filled by US-2700.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.cost_settings.interface import category_label_of
from waterfall.core.portfolio.aggregation import (
    load_ratio,
    load_zone,
    month_label,
    months_window,
    sum_by_key,
    total_of,
    weighted_hours,
)
from waterfall.core.portfolio.contributing import WORKLOAD
from waterfall.core.portfolio.documents import documents_of
from waterfall.core.portfolio.interface.scope import resolve_scope
from waterfall.core.portfolio.shaping import computable, hours, percent, scope_document
from waterfall.core.portfolio.states import IN_PROGRESS, PRICING
from waterfall.core.resource_settings.interface import (
    RoleFilters,
    RoleSort,
    RoleWindow,
    list_roles,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.documents import Documents
    from waterfall.core.portfolio.interface.scope import (
        PortfolioAsked,
        PortfolioReading,
        ResolvedScope,
    )
    from waterfall.core.projects.interface import ProjectState
    from waterfall.core.resource_settings.interface import RoleView

COUNTED: frozenset[ProjectState] = frozenset({IN_PROGRESS, PRICING})
# Every role there is: the window of the list of the roles, wider than any installation.
EVERY_ROLE = RoleWindow(limit=10**9, offset=0)
NOUGHT = Decimal("0.00")

type Loads = dict[tuple[UUID, str], Decimal]


def _loads(resolved: ResolvedScope, documents: Mapping[UUID, Documents]) -> Loads:
    """Sum the weighted hours of the projects by role and by month, each part rounded once.

    A project that kept no workload — a marking before EP-11 — or whose weight is unknown, an
    offer a marking before EP-07 kept no probability for, adds nothing (EP-11, "La contribution
    d'un projet").
    """
    parts: list[Loads] = []
    for project_id, held in documents.items():
        weight = resolved.projects[project_id].weight
        document = held.get(WORKLOAD)
        if document is None or weight is None:
            continue
        parts.append(
            {
                (UUID(role["resource_role_id"]), month["month"]): weighted_hours(
                    Decimal(month["hours"]), weight
                )
                for role in document["roles"]
                for month in role["months"]
            }
        )
    return sum_by_key(parts)


def _roles(session: Session, asked: PortfolioAsked) -> list[RoleView]:
    """Give the active roles, or those of the node and its descendants, on the tree as it stands."""
    filters = RoleFilters(org_node_id=asked.org_node_id, states=frozenset({True}))
    sort = RoleSort(category_label_of)
    return list_roles(session, filters, sort, EVERY_ROLE, may_change=False).roles


def read_portfolio_workload(
    session: Session,
    asked: PortfolioAsked,
    reading: PortfolioReading,
    *,
    horizon_months: int,
    under_load_threshold: Decimal,
) -> Document:
    """Give the workload of the scope read by ``reading``, over its horizon, at its threshold.

    The months are those of ``horizon_months`` from the month of the date of calculation, without a
    gap; each role retained has one for each, a role without load included, the roles by label then
    by identifier. The zone of a month is
    the load against the capacity of its role and the threshold (``load_zone``); the capacity of
    the scope is the sum of those of the roles retained, and each month's total the sum of their
    hours. Refuses an unknown node as every view of the portfolio does (422, ``resolve_scope``).
    """
    resolved = resolve_scope(session, asked, reading.at, counted=COUNTED, period=False)
    documents = documents_of(session, resolved, reading, (WORKLOAD,))
    loads = _loads(resolved, documents)
    roles = _roles(session, asked)
    window = months_window(resolved.scope.as_of, horizon=horizon_months)
    months = [month_label(each) for each in window]

    def hours_of(role: RoleView, month: str) -> Decimal:
        return loads.get((role.resource_role_id, month), NOUGHT)

    return {
        "scope": scope_document(resolved.scope),
        "under_load_threshold": percent(under_load_threshold),
        "capacity_monthly_hours": hours(total_of(role.capacity.monthly_hours for role in roles)),
        "months": months,
        "monthly_totals": [
            {"month": month, "hours": hours(total_of(hours_of(role, month) for role in roles))}
            for month in months
        ],
        "roles": [
            {
                "resource_role_id": str(role.resource_role_id),
                "label": role.label,
                "capacity_monthly_hours": hours(role.capacity.monthly_hours),
                "months": [
                    {
                        "month": month,
                        "hours": hours(hours_of(role, month)),
                        "load_ratio": computable(
                            load_ratio(hours_of(role, month), role.capacity.monthly_hours)
                        ),
                        "zone": load_zone(
                            hours_of(role, month), role.capacity.monthly_hours, under_load_threshold
                        ),
                    }
                    for month in months
                ],
            }
            for role in roles
        ],
    }
