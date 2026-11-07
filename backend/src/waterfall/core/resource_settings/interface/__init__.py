# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the resource settings (FBS-3.2) offer to the API, the other modules and the witness.

One file per object, each filled by the story that serves it and re-exported here: the names
of a file are imported in a statement of their own, below the comment that names the file, so
that two stories filling two files write two places of this one. Another module imports them
from here, never from the file.
"""

# ``calendars`` (US-0860): the calendars, one of them the default.
from waterfall.core.resource_settings.interface.calendars import (
    DAYS as DAYS,
)
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
from waterfall.core.resource_settings.interface.duration_units import (
    DEFAULT_UNITS as DEFAULT_UNITS,
)
from waterfall.core.resource_settings.interface.duration_units import (
    DurationUnitsView as DurationUnitsView,
)
from waterfall.core.resource_settings.interface.duration_units import (
    Units as Units,
)
from waterfall.core.resource_settings.interface.duration_units import (
    get_duration_units as get_duration_units,
)
from waterfall.core.resource_settings.interface.duration_units import (
    install_duration_units as install_duration_units,
)
from waterfall.core.resource_settings.interface.duration_units import (
    set_duration_units as set_duration_units,
)

# ``extensions`` (US-1380/L1, filled by the planning in US-1390/L2): the guard of the idle tasks
# and the recalculation that the planning registers.
from waterfall.core.resource_settings.interface.extensions import (
    CalendarChange as CalendarChange,
)
from waterfall.core.resource_settings.interface.extensions import (
    IdleProject as IdleProject,
)
from waterfall.core.resource_settings.interface.extensions import (
    projects_left_idle as projects_left_idle,
)
from waterfall.core.resource_settings.interface.extensions import (
    recalculate as recalculate,
)
from waterfall.core.resource_settings.interface.extensions import (
    register_idle_task_guard as register_idle_task_guard,
)
from waterfall.core.resource_settings.interface.extensions import (
    register_recalculation as register_recalculation,
)

# ``org_nodes`` (US-0840): the tree of the organisation.
from waterfall.core.resource_settings.interface.org_nodes import (
    ACTIVE_ONLY as ACTIVE_ONLY,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeActivation as NodeActivation,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeCommand as NodeCommand,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeFilters as NodeFilters,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeView as NodeView,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    NodeWrite as NodeWrite,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    create_node as create_node,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    label_of as label_of,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    list_nodes as list_nodes,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    node_is_active as node_is_active,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    node_labels as node_labels,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    read_node as read_node,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    set_activation as set_activation,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    update_node as update_node,
)
from waterfall.core.resource_settings.interface.org_nodes import (
    within_node as within_node,
)

# ``readiness`` (US-0810/L2): the questions of the minimal reference this module answers, and the
# lock that guards them (#2154).
from waterfall.core.resource_settings.interface.readiness import (
    default_calendar_has_hours as default_calendar_has_hours,
)
from waterfall.core.resource_settings.interface.readiness import (
    lock_reference as lock_reference,
)
from waterfall.core.resource_settings.interface.readiness import (
    share_reference as share_reference,
)

# ``resource_roles`` (US-0850): the roles of resources and their capacity.
from waterfall.core.resource_settings.interface.resource_roles import (
    Capacity as Capacity,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    CategoryAdmission as CategoryAdmission,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    LabelOf as LabelOf,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleChange as RoleChange,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleColumn as RoleColumn,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleCommand as RoleCommand,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleDraft as RoleDraft,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleFilters as RoleFilters,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleOfCategory as RoleOfCategory,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RolePage as RolePage,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleSort as RoleSort,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleView as RoleView,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    RoleWindow as RoleWindow,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    active_role_exists as active_role_exists,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    category_has_roles as category_has_roles,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    create_role as create_role,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    list_roles as list_roles,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    read_role as read_role,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    read_roles as read_roles,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    role_calendar_change_is_admissible as role_calendar_change_is_admissible,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    role_calendars as role_calendars,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    roles_of_categories as roles_of_categories,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    roles_present as roles_present,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    set_role_activation as set_role_activation,
)
from waterfall.core.resource_settings.interface.resource_roles import (
    update_role as update_role,
)
