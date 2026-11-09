# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars of the roles of the lines, which a change of a calendar must not leave idle.

The calendar applicable to a task is the intersection of the calendars of the roles of its labour
lines (WF-PLA-0010): a change of the hours of a calendar a role of a line names
(``updateCalendar``), or a role given another calendar (``updateResourceRole``), is refused when it
would leave a task of a current revision without any hour in its week — the calendars of the
roles of its labour lines, the change applied, meeting on no day, or the one role of its lines left
without an hour — (``TASK_WITHOUT_WORKING_HOURS``), the projects concerned named, and the roles
whose calendars leave a task of them idle (``register_idle_task_guard`` of the resource settings,
EP-06). A task without a labour line is on the default calendar, which the planning judges
(``tasks_left_idle``).

Read without a lock, as the guard of the planning reads the tasks: the change of the reference
holds its own.

Declared by US-1490/L1 and registered without effect; filled by US-1500/L2.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.costing import DAYS, calendar_hours
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import bearers_of, lines_of, node_revisions
from waterfall.core.projects.interface import projects_named
from waterfall.core.resource_settings.interface import IdleProject, role_calendars
from waterfall.core.revisions.interface import current_structures

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.resource_settings.interface import CalendarChange


def _roles_changed(session: Session, change: CalendarChange) -> frozenset[UUID]:
    """Give the roles the change gives new hours: the role named, or those on the calendar."""
    if change.resource_role_id is not None:
        return frozenset({change.resource_role_id})
    employed = session.scalars(
        select(EstimateLine.resource_role_id)
        .where(EstimateLine.resource_role_id.is_not(None))
        .distinct()
    )
    calendars = role_calendars(session, {role for role in employed if role is not None})
    return frozenset(role for role, calendar in calendars.items() if calendar == change.calendar_id)


def _lines_of_roles(
    session: Session, roles: Collection[UUID], current: Collection[UUID]
) -> dict[UUID, set[UUID]]:
    """Give, by project, the labour lines of the roles named that a current revision holds."""
    found: dict[UUID, set[UUID]] = {}
    rows = session.execute(
        select(EstimateLine.project_id, EstimateLine.node_id).where(
            EstimateLine.resource_role_id.in_(list(roles))
        )
    )
    for project_id, node_id in rows:
        found.setdefault(project_id, set()).add(node_id)
    for project_id, nodes in list(found.items()):
        revisions = node_revisions(session, project_id, nodes)
        kept = {node for node in nodes if revisions.get(node) in current}
        if kept:
            found[project_id] = kept
        else:
            del found[project_id]
    return found


def _idle_roles(
    session: Session, held: tuple[UUID, Collection[UUID]], change: CalendarChange
) -> set[UUID]:
    """Give the roles of the tasks of the lines named that the change leaves without a common hour.

    ``held`` is the project and the lines. Each task bearing one of the lines is judged on the
    roles of all its labour lines, the roles the change touches on the hours it gives them.
    """
    project_id, lines = held
    changed = _roles_changed(session, change)
    tasks = lines_of(session, project_id, set(bearers_of(session, project_id, lines).values()))
    roles = dict(
        session.execute(
            select(EstimateLine.node_id, EstimateLine.resource_role_id).where(
                EstimateLine.project_id == project_id,
                EstimateLine.node_id.in_([line for each in tasks.values() for line in each]),
                EstimateLine.resource_role_id.is_not(None),
            )
        ).all()
    )
    calendars = role_calendars(session, {role for role in roles.values() if role is not None})
    weeks = calendar_hours(session, set(calendars.values()))
    given = tuple(change.weekly_hours[day] for day in DAYS)
    idle: set[UUID] = set()
    for task_lines in tasks.values():
        named = {role for line in task_lines if (role := roles.get(line)) is not None}
        hours = [given if role in changed else weeks[calendars[role]] for role in named]
        if hours and not any(min(day) > 0 for day in zip(*hours, strict=True)):
            idle |= named
    return idle


def idle_tasks_for_role_calendar(
    session: Session, change: CalendarChange
) -> tuple[IdleProject, ...]:
    """Name the projects a change of a calendar of a role would leave with an idle task.

    Each by its label and its code, in the order of its label, with the roles of its idle tasks.
    """
    roles = _roles_changed(session, change)
    if not roles:
        return ()
    current = {each.revision_id for each in current_structures(session, lock=False)}
    idle: dict[UUID, set[UUID]] = {}
    for project_id, lines in _lines_of_roles(session, roles, current).items():
        found = _idle_roles(session, (project_id, lines), change)
        if found:
            idle[project_id] = found
    named = projects_named(session, idle)
    ordered = sorted(named.items(), key=lambda item: (item[1][1], item[1][0] or ""))
    return tuple(
        IdleProject(label, code, tuple(sorted(idle[project_id])))
        for project_id, (code, label) in ordered
    )
