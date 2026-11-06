# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars and the units of duration (FBS-3.2).

``listCalendars``, ``createCalendar``, ``updateCalendar``, ``setDefaultCalendar``,
``setCalendarActivation``, ``getDurationUnits`` and ``setDurationUnits``.

Registered by the application, empty until US-0860 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
