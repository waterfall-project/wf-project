# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of a revision as the indicators read them, private to the module (US-1660/L3).

What ``interface.indicator_lines`` offers is read here, so that the estimate reads it without
importing its own interface (#3591): ``lines_for_indicators`` gives each line of the main structure
of a revision, the provisions left out, on the task that bears it; ``planned_value_at`` the planned
value of lines at the end of a day.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.estimate.imaging import kept_reference
from waterfall.core.estimate.placing import role_weeks
from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.remaining.reviewing import provisions_of
from waterfall.core.estimate.spreading import Placement, PlannedLine, planned_value
from waterfall.core.planning.interface import lines_of, tasks_for_indicators, weekly_calendar
from waterfall.core.revisions.interface import revision_marked_at

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Calendar, IndicatorTask


@dataclass(frozen=True, slots=True)
class IndicatorLine:
    """A line of a revision, not a provision, on the task that bears it.

    ``budgeted_amount`` is the amount the reference fixes, its re-estimated one without a
    reference; ``task_origin_risk_id`` the risk whose occurrence created its task, none before
    EP-08; ``placement`` its task as the revision dates it, on the calendar the line is worked on.
    """

    node_id: UUID
    task_id: UUID
    task_lineage_id: UUID
    task_origin_risk_id: UUID | None
    subproject_id: UUID | None
    budgeted_amount: Decimal
    reestimated_amount: Decimal
    payment_delay_days: int
    placement: Placement


@dataclass(frozen=True, slots=True)
class LinesStamp:
    """How many lines a revision holds, and the last instant one was written."""

    count: int
    updated_at: datetime | None


def lines_for_indicators(
    session: Session,
    project_id: UUID,
    revision_id: UUID,
    tasks: Sequence[IndicatorTask] | None = None,
) -> tuple[IndicatorLine, ...]:
    """Give the lines of the main structure of a revision, not provisions, in the order of the tree.

    ``tasks`` are those of the revision when the caller has read them already
    (``tasks_for_indicators``), so that a computation reads them once.
    """
    if tasks is None:
        tasks = tasks_for_indicators(session, project_id, revision_id)
    by_node = {task.node_id: task for task in tasks}
    bearing = lines_of(session, project_id, list(by_node))
    rows = {row.node_id: row for row in rows_of(session, project_id, _held(bearing))}
    provisions = provisions_of(session, list(rows.values()))
    roles = {row.resource_role_id for row in rows.values() if row.resource_role_id is not None}
    marked = revision_marked_at(session, revision_id) is not None
    kept = kept_reference(session, project_id, revision_id) if marked else None
    weeks = role_weeks(session, roles, kept)
    found: list[IndicatorLine] = []
    for task_id, held in bearing.items():
        task = by_node[task_id]
        # The calendar of the task, made once for its lines without a role (#3802).
        own: Calendar | None = None
        for node in held:
            row = rows.get(node)
            if row is None or node in provisions:
                continue
            role = row.resource_role_id
            if role is None:
                own = own or weekly_calendar(task.calendar_hours)
                week = own
            else:
                week = weeks[role]
            found.append(
                IndicatorLine(
                    node_id=node,
                    task_id=task_id,
                    task_lineage_id=task.lineage_id,
                    task_origin_risk_id=task.origin_risk_id,
                    subproject_id=row.subproject_id,
                    budgeted_amount=budgeted_of(row),
                    reestimated_amount=row.reestimated_amount,
                    payment_delay_days=row.payment_delay_days,
                    placement=Placement(week, task.start, task.finish),
                )
            )
    return tuple(found)


def _held(bearing: dict[UUID, tuple[UUID, ...]]) -> list[UUID]:
    return [node for held in bearing.values() for node in held]


def planned_value_at(lines: Iterable[IndicatorLine], at: date) -> Decimal:
    """Give the planned value of lines at the end of a day: their budgeted amounts spread.

    Each line is spread over its task in proportion to the hours worked, a line of a milestone
    counting whole at its date (WF-DEV-0080); each share is rounded to the cent, and their sum is
    the planned value, whatever the scope the lines are grouped by (WF-IND-0020-A).
    """
    planned = (PlannedLine(each.budgeted_amount, each.placement) for each in lines)
    return planned_value(planned, at)
