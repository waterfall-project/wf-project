# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the resource settings (FBS-3.2) offer to the API, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names
of a file are imported in a statement of their own, below the comment that names the file, so
that two stories filling two files write two places of this one. Another module imports them
from here, never from the file.
"""

# ``readiness`` (US-0810/L2): the questions of the minimal reference this module answers.

# ``org_nodes`` (US-0840): the tree of the organisation.

# ``resource_roles`` (US-0850): the roles of resources and their capacity.

# ``calendars`` (US-0860): the calendars, one of them the default.
from waterfall.core.resource_settings.interface.calendars import (
    CalendarColumn as CalendarColumn,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarCommand as CalendarCommand,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarContent as CalendarContent,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarFilters as CalendarFilters,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarPage as CalendarPage,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarSort as CalendarSort,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarView as CalendarView,
)
from waterfall.core.resource_settings.interface.calendars import (
    CalendarWindow as CalendarWindow,
)
from waterfall.core.resource_settings.interface.calendars import (
    WeeklyHours as WeeklyHours,
)
from waterfall.core.resource_settings.interface.calendars import (
    calendar_change_is_admissible as calendar_change_is_admissible,
)
from waterfall.core.resource_settings.interface.calendars import (
    calendar_commands as calendar_commands,
)
from waterfall.core.resource_settings.interface.calendars import (
    calendars_present as calendars_present,
)
from waterfall.core.resource_settings.interface.calendars import (
    create_calendar as create_calendar,
)
from waterfall.core.resource_settings.interface.calendars import (
    list_calendars as list_calendars,
)
from waterfall.core.resource_settings.interface.calendars import (
    read_calendar as read_calendar,
)
from waterfall.core.resource_settings.interface.calendars import (
    set_calendar_activation as set_calendar_activation,
)
from waterfall.core.resource_settings.interface.calendars import (
    set_default_calendar as set_default_calendar,
)
from waterfall.core.resource_settings.interface.calendars import (
    update_calendar as update_calendar,
)

# ``duration_units`` (US-0860): the units of duration.
