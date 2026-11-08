# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars of the roles of the lines, which a change of a calendar must not leave idle.

The calendar applicable to a task is the intersection of the calendars of the roles of its labour
lines (WF-PLA-0010): a change of the hours of a calendar a role of a line names is refused when it
would leave such a task without any hour in its week (``TASK_WITHOUT_WORKING_HOURS``), the projects
concerned named (``register_idle_task_guard`` of the resource settings, EP-06).

Declared by US-1490/L1 and registered without effect: no line names a role before US-1490/L3, so
that no task is left idle by the roles. US-1500 fills it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.resource_settings.interface import CalendarChange, IdleProject


def idle_tasks_for_role_calendar(
    session: Session, change: CalendarChange
) -> tuple[IdleProject, ...]:
    """Name the projects a change of a calendar of a role would leave with an idle task: none."""
    del session, change
    return ()
