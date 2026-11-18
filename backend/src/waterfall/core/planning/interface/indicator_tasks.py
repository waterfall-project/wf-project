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
from functools import partial
from typing import TYPE_CHECKING

from waterfall.core.planning.reading import tasks_tallied
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.views import derived_states, tallied_own_lines
from waterfall.core.planning.writing import Place
from waterfall.core.revisions.interface import aimed_structure

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


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
    """Give the tasks of the main structure of a revision, depth first; none without one.

    The tasks alone, with what their lines count (``tasks_tallied``): the state of a summary is
    derived as ``listNodes`` derives it, without the links, the tracking, the physical progress or
    the views a reading of the grid adds, which the indicators do not read (#3902).
    """
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        return ()
    tallied = tasks_tallied(session, Place(project_id, revision_id, structure_id))
    tree = tallied.tree
    states = derived_states(tree, partial(tallied_own_lines, tree, tallied.tallies))
    found: list[IndicatorTask] = []
    for node_id in tree.order:
        node, task, state = tree.nodes[node_id], tree.tasks[node_id], states[node_id]
        found.append(
            IndicatorTask(
                node_id=node_id,
                lineage_id=node.lineage_id,
                label=task.label,
                parent_id=node.parent_id,
                is_summary=tree.is_summary(node_id),
                is_milestone=tree.is_milestone(node_id),
                progress=state.progress,
                started_on=state.started_on,
                completed_on=state.completed_on,
                start=WorkInstant(task.start_date, task.start_hours),
                finish=WorkInstant(task.finish_date, task.finish_hours),
                calendar_hours=tallied.calendars[node_id].calendar.week,
                origin_risk_id=node.origin_risk_id,
            )
        )
    return tuple(found)
