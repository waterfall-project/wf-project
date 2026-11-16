# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of a revision as the indicators read them (EP-10, "Modules"; US-1660/L3).

Each task of the main structure of a revision, summaries and milestones included: its node, its
label, its lineage — what a task of the reference is found by in the revision computed, the
earned value counting a line of the reference when its task, by its lineage, is completed there
(WF-IND-0030) —, its parent, its state and its two dates, its start and finish as the revision
dates them, the hours of its applicable calendar, and the risk it comes from (EP-08). A marked
revision is read as its marking froze it; a revision without a main structure has no task.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.filters import NodeFilters
from waterfall.core.planning.interface.nodes import list_nodes
from waterfall.core.planning.writing import Place
from waterfall.core.revisions.interface import aimed_structure

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.scheduling.calendar import WorkInstant

TASK = "task"


@dataclass(frozen=True, slots=True)
class IndicatorTask:
    """A task of a revision: what places a line on it, and what tells whether it is earned.

    ``calendar_hours`` are the hours of its applicable calendar, Monday first; ``origin_risk_id``
    the risk whose occurrence created it, none before EP-08.
    """

    node_id: UUID
    lineage_id: UUID
    label: str
    parent_id: UUID | None
    is_summary: bool
    is_milestone: bool
    progress: str
    started_on: date | None
    completed_on: date | None
    start: WorkInstant
    finish: WorkInstant
    calendar_hours: tuple[Decimal, ...]
    origin_risk_id: UUID | None


def tasks_for_indicators(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[IndicatorTask, ...]:
    """Give the tasks of the main structure of a revision, depth first; none without one."""
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        return ()
    place = Place(project_id, revision_id, structure_id)
    read = list_nodes(session, place, NodeFilters(kinds=(TASK,)))
    return tuple(
        IndicatorTask(
            node_id=node.node_id,
            lineage_id=node.lineage_id,
            label=task.label,
            parent_id=node.parent_id,
            is_summary=task.is_summary,
            is_milestone=task.is_milestone,
            progress=task.progress,
            started_on=task.started_on,
            completed_on=task.completed_on,
            start=task.start,
            finish=task.finish,
            calendar_hours=task.calendar_hours,
            origin_risk_id=node.origin_risk_id,
        )
        for node in read.items
        if (task := node.task) is not None
    )
