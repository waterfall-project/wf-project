# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning adds to the reference: the guard of the idle tasks, and the recalculation.

Two registries of this module, which imports no other module of the core (EP-06, "Les points
d'extension"), filled by the planning at the import of its interface:

- ``register_idle_task_guard``: a change of the hours of a calendar, or its designation as the
  default, is refused when a task of a current revision would be left without any hour in its week
  (``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010), the projects concerned named by their label and
  their code, without anything else, since the author may not read them (``params.projects``,
  WF-ADM-0110). EP-06 judges the default calendar (``tasks_left_idle``), EP-07 the roles;
- ``register_recalculation``: the constants of the units of duration, the hours of a calendar and
  the designation of the default redate, in their transaction, the structures of the current
  revisions (``reschedule_current_structures``), their dates' instant moved on to that of the
  change. The reference is locked first — the object written and the advisory lock of its rule —,
  the structures after it, by the recalculation, in the order of (``project_id``, ``id``).

Declared by US-1380/L1; US-1390/L2 fills what the planning registers, and gives the recalculation
the instant of the change.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class CalendarChange:
    """A calendar about to change: its hours of each day after the change, default or not after."""

    calendar_id: UUID
    weekly_hours: Mapping[str, Decimal]
    default: bool


@dataclass(frozen=True, slots=True)
class IdleProject:
    """A project a change would leave with a task without an hour: its label and its code."""

    label: str
    code: str | None


# What names the projects a change of a calendar would leave with an idle task, in order.
_GUARDS: Registry[Callable[[Session, CalendarChange], tuple[IdleProject, ...]]] = Registry(
    "resource_settings.idle_task_guard"
)
# What redates the structures of the current revisions once the reference changed, in order.
_RECALCULATIONS: Registry[Callable[[Session, datetime], None]] = Registry(
    "resource_settings.recalculation"
)


def register_idle_task_guard(
    guard: Callable[[Session, CalendarChange], tuple[IdleProject, ...]],
) -> Callable[[], None]:
    """Add what names the projects a calendar change would leave idle; give its withdrawal."""
    return _GUARDS.register(guard)


def register_recalculation(
    recalculate: Callable[[Session, datetime], None],
) -> Callable[[], None]:
    """Add what redates the current structures after the reference changed; give its withdrawal.

    It is given the transaction of the change and its instant.
    """
    return _RECALCULATIONS.register(recalculate)


def projects_left_idle(session: Session, change: CalendarChange) -> tuple[IdleProject, ...]:
    """Name the projects the change would leave with a task without an hour, by every guard."""
    return tuple(project for guard in _GUARDS.entries() for project in guard(session, change))


def recalculate(session: Session, at: datetime) -> None:
    """Redate the structures of the current revisions at ``at``, by every recalculation registered.

    To be called once the reference is written, in its transaction and under its locks.
    """
    for recalculation in _RECALCULATIONS.entries():
        recalculation(session, at)
