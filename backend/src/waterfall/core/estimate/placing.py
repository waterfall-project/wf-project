# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of a revision on the tasks that bear them, private to the module (US-1520).

The workload and the planned value read the same thing: each line of the main structure of a
revision with the task that bears it, as the planning dates it, and the calendar its hours are
worked on — its role's for a labour line, its task's for another (EP-07, "Le calcul des montants").
A revision is read as it stands: a marked one keeps the dates its marking froze.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.estimate.costing import calendar_hours
from waterfall.core.estimate.reading import rows_of
from waterfall.core.estimate.spreading import Placement, WorkWeek
from waterfall.core.planning.interface import NodeFilters, Place, lines_of, list_nodes
from waterfall.core.resource_settings.interface import role_calendars
from waterfall.core.revisions.interface import aimed_structure

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.tables import EstimateLine
    from waterfall.core.planning.interface import TaskView

TASK = "task"
COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class Placed:
    """A line with its task: the dates and the progress of the task, the hours of its calendar."""

    line: EstimateLine
    task: TaskView

    @property
    def is_completed(self) -> bool:
        """Tell whether the task that bears the line is completed (``setTaskProgress``)."""
        return self.task.progress == COMPLETED


def placed_lines(session: Session, project_id: UUID, revision_id: UUID) -> list[Placed]:
    """Give the lines of the main structure of a revision, each with the task that bears it.

    In the order of the tree: the tasks depth first, the lines of a task in their order.
    """
    structure = aimed_structure(session, project_id, revision_id, None)
    if structure is None:
        return []
    place = Place(project_id, revision_id, structure)
    read = list_nodes(session, place, NodeFilters(kinds=(TASK,)))
    tasks = {item.node_id: item.task for item in read.items if item.task is not None}
    bearing = lines_of(session, project_id, list(tasks))
    nodes = [node for each in bearing.values() for node in each]
    rows = {row.node_id: row for row in rows_of(session, project_id, nodes)}
    return [
        Placed(rows[node], tasks[task_id])
        for task_id, held in bearing.items()
        for node in held
        if node in rows
    ]


def role_weeks(session: Session, role_ids: Collection[UUID]) -> dict[UUID, WorkWeek]:
    """Give the week of work of each role named: the calendar of the reference it names."""
    calendars = role_calendars(session, role_ids)
    weeks = calendar_hours(session, calendars.values())
    return {role_id: WorkWeek(weeks[calendar_id]) for role_id, calendar_id in calendars.items()}


def placement_of(placed: Placed, weeks: dict[UUID, WorkWeek]) -> Placement:
    """Give a line as a spreading sees it: its task's dates, on the calendar it is worked on."""
    role_id = placed.line.resource_role_id
    week = WorkWeek(placed.task.calendar_hours) if role_id is None else weeks[role_id]
    return Placement(week, placed.task.start, placed.task.finish)
