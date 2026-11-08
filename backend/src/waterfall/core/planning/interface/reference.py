# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning answers to the reference: the idle tasks, and the recalculation.

Registered at the import of the interface in the registries of the resource settings
(``register_idle_task_guard``, ``register_recalculation``): a change of the hours of a calendar or
of the default is refused when it would leave a task of a current revision without an hour in its
week (``tasks_left_idle``, WF-PLA-0010), and a change of the units of duration or of a calendar
redates the structures of the current revisions in its transaction
(``reschedule_current_structures``, WF-PLA-0160), each locked ``FOR UPDATE`` in the order of
(``project_id``, ``id``) after the reference (EP-06, "Ce que le cadrage décide").

The guard judges the default calendar, which every task without a labour line is on — every task
of EP-06 —: a default left without an hour in the week names each project one of whose current
revisions holds such a task, by its label and its code, nothing else (WF-ADM-0110). The calendars
of the roles of the lines are EP-07's, which registers its own guard.

The recalculation reads the structures of the current revisions with their revisions ``FOR
SHARE`` — a marking or an abandonment waits for it, and a revision marked before it is left with
the dates it computed (WF-REF-0130) —, then replays the engine on each, in the order of
(``project_id``, ``id``), its ``scheduled_at`` moved on to the instant of the change. A write of the
planning never locks the reference, and locks its one structure: no lock is awaited both ways. It
keeps no entry of the history: no one wrote the tasks it redates.

Filled by US-1390/L2.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.interface.structures import reschedule
from waterfall.core.planning.tables import Node
from waterfall.core.planning.tree import TASK
from waterfall.core.projects.interface import projects_named
from waterfall.core.resource_settings.interface import IdleProject
from waterfall.core.revisions.interface import current_structures

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.resource_settings.interface import CalendarChange


def _on_the_default(session: Session, project_id: UUID, task_ids: list[UUID]) -> bool:
    """Tell whether one of these tasks is on the default calendar: its facets name no calendar."""
    hooks = list(facets().values())
    return any(
        not any(each.calendars(session, project_id, task_id) for each in hooks)
        for task_id in task_ids
    )


def tasks_left_idle(session: Session, change: CalendarChange) -> tuple[IdleProject, ...]:
    """Name the projects whose task of a current revision the change would leave without an hour.

    Only a default calendar without an hour in its week leaves one so, here: the projects are
    named by their label and their code, null without one, in the order of their label.
    """
    if not change.default or sum(change.weekly_hours.values()) > 0:
        return ()
    structures = {each.structure_id for each in current_structures(session, lock=False)}
    if not structures:
        return ()
    tasks: dict[UUID, list[UUID]] = {}
    for project_id, node_id in session.execute(
        select(Node.project_id, Node.id).where(Node.structure_id.in_(structures), Node.kind == TASK)
    ):
        tasks.setdefault(project_id, []).append(node_id)
    idle = [
        project_id
        for project_id, task_ids in tasks.items()
        if _on_the_default(session, project_id, task_ids)
    ]
    named = projects_named(session, idle)
    return tuple(
        IdleProject(label, code)
        for code, label in sorted(named.values(), key=lambda each: (each[1], each[0] or ""))
    )


def reschedule_current_structures(session: Session, at: datetime) -> None:
    """Redate the structures of the current revisions, after a change of the reference.

    Their revisions read ``FOR SHARE``, then each structure locked and replayed in the order of
    (``project_id``, ``id``), its dates' instant moved on to ``at``. Beyond fifteen years, the
    change is refused naming the task that finishes last (422 ``PROJECT_HORIZON_EXCEEDED``).
    """
    for each in current_structures(session, lock=True):
        reschedule(session, each.project_id, each.structure_id, at)
