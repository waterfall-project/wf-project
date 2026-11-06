# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The questions of the minimal reference this module answers.

Whether the default calendar counts hours in its week (WF-CYC-0120); whether an active role of
resources exists is answered by ``resource_roles``. The route of the minimal reference composes
them with those of the cost settings.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, or_, select

from waterfall.core.resource_settings.tables import DAYS, Calendar

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def default_calendar_has_hours(session: Session) -> bool:
    """Tell whether the default calendar, active, works one day of the week at least.

    ``default_calendar_with_hours``: a week without any hour leaves a task no day to be worked.
    """
    worked = or_(*(getattr(Calendar, day) > 0 for day in DAYS))
    held = select(exists().where(Calendar.is_default, Calendar.is_active, worked))
    return bool(session.scalar(held))
