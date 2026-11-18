# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The series of the curves at the step of the month, and the cash-out (US-1690/L1).

Pure: dates, amounts and dated tasks in, points out, without a database or a clock (the date of
calculation is an argument). The names are imported from here, never from the file that defines
them.
"""

# ``cash_out``: the cash-out by month.
from waterfall.core.indicators.series.cash_out import (
    CashOutMonth as CashOutMonth,
)
from waterfall.core.indicators.series.cash_out import (
    cash_out_by_month as cash_out_by_month,
)

# ``cumulation``: the cumulative series, by month-end and at the date of calculation.
from waterfall.core.indicators.series.cumulation import (
    Point as Point,
)
from waterfall.core.indicators.series.cumulation import (
    cumulative as cumulative,
)
from waterfall.core.indicators.series.cumulation import (
    cumulative_from as cumulative_from,
)
from waterfall.core.indicators.series.cumulation import (
    cumulative_until as cumulative_until,
)
from waterfall.core.indicators.series.cumulation import (
    to_cent as to_cent,
)

# ``months``: the month-ends, and the dated amounts that fall in them.
from waterfall.core.indicators.series.months import (
    end_of as end_of,
)
from waterfall.core.indicators.series.months import (
    events_by_month as events_by_month,
)
from waterfall.core.indicators.series.months import (
    month_before as month_before,
)
from waterfall.core.indicators.series.months import (
    month_end as month_end,
)
from waterfall.core.indicators.series.months import (
    month_ends as month_ends,
)
from waterfall.core.indicators.series.months import (
    month_of as month_of,
)
from waterfall.core.indicators.series.months import (
    months_between as months_between,
)

# ``shares``: the monthly parts of lines.
from waterfall.core.indicators.series.shares import (
    Spreader as Spreader,
)
from waterfall.core.indicators.series.shares import (
    SpreadLine as SpreadLine,
)
from waterfall.core.indicators.series.shares import (
    line_shares as line_shares,
)
from waterfall.core.indicators.series.shares import (
    shifted as shifted,
)
from waterfall.core.indicators.series.shares import (
    spread_lines as spread_lines,
)
