# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/calendars.py`` ask for: the calendars and the units.

``test_access_evaluation.py`` gathers them; US-0860 declares each operation it serves.
"""

# The permissions each operation asks for, in the order they are evaluated. The active calendars
# are read by any session; the deactivated calendars and every write ask for the
# permission to change the resource settings.
ASKED: dict[str, tuple[str, ...]] = {
    "listCalendars": (),
    "createCalendar": ("resource_settings.write",),
    "updateCalendar": ("resource_settings.write",),
    "setDefaultCalendar": ("resource_settings.write",),
    "setCalendarActivation": ("resource_settings.write",),
}
# The permission a list asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {"listCalendars": "resource_settings.write"}
