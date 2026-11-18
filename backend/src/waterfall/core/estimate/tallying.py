# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the lines a task bears count, read grouped by task, private to the module (US-2280/L1).

A reading of the tasks alone — the planning, ``listNodes`` with ``kinds=task`` — reads none of the
lines: it asks, by task, what they count (``FacetHooks.tally``; EP-26, "L'agrégat d'abord"). One
statement, grouped by task, over the nodes of the structure the planning names: their figures
summed as ``totals_of`` reads each — the budgeted amount as ``budgeted_of`` reads it —, their
number, whether one is not a risk's, the categories of the own lines that keep a remaining to
commit, which hold the task open unless a provision (``open_tasks``, WF-PLA-0040), the roles of
the lines, whose calendars the task's follows (``line_calendars``, WF-PLA-0010), and the budgeted
amounts of the lines not of a provision, which the physical progress of a summary weighs
(``Tally.earnable``, WF-IND-0060; US-1680): the categories of the provision kind are read first,
and the statement leaves their lines out of that sum; and which lines are of a provision
(``line_provisions``). A node whose facet is missing — written
around the service — counts in the number and adds nought.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import and_, distinct, func, select

from waterfall.core.cost_settings.interface import categories_of_kind
from waterfall.core.estimate.remaining.reviewing import PROVISION
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import Amounts, Tally
from waterfall.core.resource_settings.interface import role_calendars

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Subquery
    from sqlalchemy.orm import Session

NOUGHT = Decimal("0.00")


def line_provisions(session: Session, project_id: UUID, nodes: Subquery) -> frozenset[UUID]:
    """Give those of the lines named that are of a category of provision, whatever their amount.

    ``nodes`` as ``line_tallies`` is given them; one statement, the categories of the provision
    kind read first.
    """
    provisions = categories_of_kind(session, PROVISION)
    if not provisions:
        return frozenset()
    return frozenset(
        session.scalars(
            select(EstimateLine.node_id)
            .join(nodes, nodes.c.node_id == EstimateLine.node_id)
            .where(
                EstimateLine.project_id == project_id,
                EstimateLine.cost_category_id.in_(list(provisions)),
            )
        )
    )


def line_tallies(session: Session, project_id: UUID, nodes: Subquery) -> dict[UUID, Tally]:
    """Give, by task, what the lines it bears count, from the nodes named, in one statement.

    ``nodes`` the lines of a structure, as the planning names them: ``node_id``, the ``task_id``
    bearing each, whether it is ``from_risk``.
    """
    own = nodes.c.from_risk.is_(False)
    provisions = categories_of_kind(session, PROVISION)
    budgeted = func.coalesce(EstimateLine.budgeted_amount, EstimateLine.reestimated_amount)
    rows = session.execute(
        select(
            nodes.c.task_id,
            func.count(),
            func.bool_or(own),
            func.sum(EstimateLine.hours),
            func.coalesce(func.sum(EstimateLine.base_amount), NOUGHT),
            func.coalesce(func.sum(budgeted), NOUGHT),
            func.coalesce(func.sum(EstimateLine.reestimated_amount), NOUGHT),
            func.array_agg(distinct(EstimateLine.cost_category_id)).filter(
                own, EstimateLine.reestimated_amount != 0
            ),
            func.array_agg(distinct(EstimateLine.resource_role_id)).filter(
                EstimateLine.resource_role_id.is_not(None)
            ),
            func.coalesce(
                func.sum(budgeted).filter(EstimateLine.cost_category_id.not_in(list(provisions))),
                NOUGHT,
            ),
        )
        .select_from(
            nodes.outerjoin(
                EstimateLine,
                and_(
                    EstimateLine.project_id == project_id,
                    EstimateLine.node_id == nodes.c.node_id,
                ),
            )
        )
        .where(nodes.c.task_id.is_not(None))
        .group_by(nodes.c.task_id)
    ).all()
    calendars = role_calendars(
        session, {role for row in rows for role in row[8] or () if role is not None}
    )
    found: dict[UUID, Tally] = {}
    for task_id, count, owned, hours, base, summed, reestimated, held, roles, earnable in rows:
        found[task_id] = Tally(
            Amounts(Decimal(0) if hours is None else hours, base, summed, reestimated),
            count,
            bool(owned),
            any(each not in provisions for each in held or ()),
            frozenset(
                calendars[role] for role in roles or () if role is not None and role in calendars
            ),
            earnable,
        )
    return found
