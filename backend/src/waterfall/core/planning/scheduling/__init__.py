# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine of the planning: dates, floats, critical path and links of a structure (US-1390).

Pure: a structure in, its schedule or a refusal out, without a database, a setting or a clock
(WF-PLA-0010, WF-PLA-0020, WF-PLA-0030, WF-PLA-0100, WF-PLA-0150, WF-PLA-0160). Every write of a
node of the planning calls it on the whole structure. The names are imported from here, never from
the file that defines them.
"""

# ``calendar``: the hours of work of a calendar, the instants of work, the applicable calendar.
from waterfall.core.planning.scheduling.calendar import (
    Calendar as Calendar,
)
from waterfall.core.planning.scheduling.calendar import (
    Moment as Moment,
)
from waterfall.core.planning.scheduling.calendar import (
    WorkInstant as WorkInstant,
)
from waterfall.core.planning.scheduling.calendar import (
    applicable_calendar as applicable_calendar,
)

# ``engine``: the calculation of a structure.
from waterfall.core.planning.scheduling.engine import (
    HORIZON_YEARS as HORIZON_YEARS,
)
from waterfall.core.planning.scheduling.engine import (
    horizon_of as horizon_of,
)
from waterfall.core.planning.scheduling.engine import (
    schedule as schedule,
)

# ``structure``: what the engine reads, what it renders, and its refusals.
from waterfall.core.planning.scheduling.structure import (
    Entry as Entry,
)
from waterfall.core.planning.scheduling.structure import (
    Link as Link,
)
from waterfall.core.planning.scheduling.structure import (
    LinkConflict as LinkConflict,
)
from waterfall.core.planning.scheduling.structure import (
    LinkCycleError as LinkCycleError,
)
from waterfall.core.planning.scheduling.structure import (
    LinkForbiddenError as LinkForbiddenError,
)
from waterfall.core.planning.scheduling.structure import (
    LinkType as LinkType,
)
from waterfall.core.planning.scheduling.structure import (
    Move as Move,
)
from waterfall.core.planning.scheduling.structure import (
    Origin as Origin,
)
from waterfall.core.planning.scheduling.structure import (
    Schedule as Schedule,
)
from waterfall.core.planning.scheduling.structure import (
    ScheduledTask as ScheduledTask,
)
from waterfall.core.planning.scheduling.structure import (
    SchedulingMode as SchedulingMode,
)
from waterfall.core.planning.scheduling.structure import (
    SchedulingRefusalError as SchedulingRefusalError,
)
from waterfall.core.planning.scheduling.structure import (
    Structure as Structure,
)
from waterfall.core.planning.scheduling.structure import (
    Task as Task,
)
from waterfall.core.planning.scheduling.structure import (
    TaskWithoutWorkingHoursError as TaskWithoutWorkingHoursError,
)

# ``units``: the units of a duration and of a lag, and their conversion into hours.
from waterfall.core.planning.scheduling.units import (
    Duration as Duration,
)
from waterfall.core.planning.scheduling.units import (
    DurationUnit as DurationUnit,
)
from waterfall.core.planning.scheduling.units import (
    Lag as Lag,
)
from waterfall.core.planning.scheduling.units import (
    LagUnit as LagUnit,
)
from waterfall.core.planning.scheduling.units import (
    UnitConstants as UnitConstants,
)
