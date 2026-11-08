# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning answers to the reference: the idle tasks, and the recalculation.

Registered at the import of the interface in the registries of the resource settings
(``register_idle_task_guard``, ``register_recalculation``): a change of the hours of a calendar or
of the default is refused when it would leave a task of a current revision without an hour in its
week (``tasks_left_idle``, WF-PLA-0010), and a change of the units of duration or of a calendar
redates the structures of the current revisions in its transaction
(``reschedule_current_structures``), each locked ``FOR UPDATE`` in the order of
(``project_id``, ``id``) after the reference (EP-06, "Ce que le cadrage décide").

Declared by US-1380/L1, without effect until US-1390/L2 fills them: no task is scheduled before.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.resource_settings.interface import CalendarChange, IdleProject


def tasks_left_idle(session: Session, change: CalendarChange) -> tuple[IdleProject, ...]:
    """Name the projects whose task of a current revision the change would leave without an hour.

    None until US-1390/L2 judges the default calendar.
    """
    del session, change
    return ()


def reschedule_current_structures(session: Session) -> None:
    """Redate the structures of the current revisions, after a change of the reference.

    Nothing until US-1390/L2 fills it with the engine.
    """
    del session
