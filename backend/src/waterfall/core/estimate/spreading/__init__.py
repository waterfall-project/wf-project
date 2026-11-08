# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spreading of a load or an amount over the years and months of a task (US-1520).

Pure: dates, a weekly calendar and an amount in, the shares by period out, without a database or a
clock (WF-DEV-0040-A, WF-DEV-0070-A, WF-DEV-0080-A). The year of consumption of a line, the
workload and the planned value share this module. The names are imported from here, never from the
file that defines them.
"""

# ``planned``: the planned value on given lines and dates.
from waterfall.core.estimate.spreading.planned import (
    PlannedLine as PlannedLine,
)
from waterfall.core.estimate.spreading.planned import (
    planned_value as planned_value,
)

# ``spread``: the shares of a load or an amount by month and by year.
from waterfall.core.estimate.spreading.spread import (
    Month as Month,
)
from waterfall.core.estimate.spreading.spread import (
    Placement as Placement,
)
from waterfall.core.estimate.spreading.spread import (
    spread_by_month as spread_by_month,
)
from waterfall.core.estimate.spreading.spread import (
    spread_by_year as spread_by_year,
)

# ``week``: the hours worked by a weekly calendar between two instants.
from waterfall.core.estimate.spreading.week import (
    WorkWeek as WorkWeek,
)
