# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The pure arithmetic of the portfolio, without a database (EP-11, US-2670/L2).

What every view of the portfolio computes from the documents of the projects: the weight of an
offer, the sums of amounts already rounded, the ratios of sums, the shares that sum to one, the
conversion rate, the distribution by zone, the quarters of a period and the zone of a month of load.
No view adds a function here: the examples of the document are tests of this package
(``tests/examples``), run with the sockets closed (WF-QUA-0020). A view imports the names from here.
"""

# ``conversion``.
from waterfall.core.portfolio.aggregation.conversion import (
    conversion_rate as conversion_rate,
)

# ``curves``.
from waterfall.core.portfolio.aggregation.curves import (
    value_at as value_at,
)

# ``periods``.
from waterfall.core.portfolio.aggregation.periods import (
    Quarter as Quarter,
)
from waterfall.core.portfolio.aggregation.periods import (
    last_day_of as last_day_of,
)
from waterfall.core.portfolio.aggregation.periods import (
    month_label as month_label,
)
from waterfall.core.portfolio.aggregation.periods import (
    month_of as month_of,
)
from waterfall.core.portfolio.aggregation.periods import (
    months_window as months_window,
)
from waterfall.core.portfolio.aggregation.periods import (
    quarter_of as quarter_of,
)
from waterfall.core.portfolio.aggregation.periods import (
    quarters_touched as quarters_touched,
)
from waterfall.core.portfolio.aggregation.periods import (
    reading_day as reading_day,
)

# ``ratios``.
from waterfall.core.portfolio.aggregation.ratios import (
    Aggregate as Aggregate,
)
from waterfall.core.portfolio.aggregation.ratios import (
    ProjectFigures as ProjectFigures,
)
from waterfall.core.portfolio.aggregation.ratios import (
    aggregate as aggregate,
)
from waterfall.core.portfolio.aggregation.ratios import (
    ratio_of as ratio_of,
)
from waterfall.core.portfolio.aggregation.ratios import (
    shares_of as shares_of,
)

# ``sums``.
from waterfall.core.portfolio.aggregation.sums import (
    ZERO_AMOUNT as ZERO_AMOUNT,
)
from waterfall.core.portfolio.aggregation.sums import (
    count_by_key as count_by_key,
)
from waterfall.core.portfolio.aggregation.sums import (
    sum_by_key as sum_by_key,
)
from waterfall.core.portfolio.aggregation.sums import (
    sum_by_month as sum_by_month,
)
from waterfall.core.portfolio.aggregation.sums import (
    total_of as total_of,
)

# ``weighting``.
from waterfall.core.portfolio.aggregation.weighting import (
    CostLine as CostLine,
)
from waterfall.core.portfolio.aggregation.weighting import (
    included_hours as included_hours,
)
from waterfall.core.portfolio.aggregation.weighting import (
    sum_by_nature as sum_by_nature,
)
from waterfall.core.portfolio.aggregation.weighting import (
    weight_of as weight_of,
)
from waterfall.core.portfolio.aggregation.weighting import (
    weighted_amount as weighted_amount,
)
from waterfall.core.portfolio.aggregation.weighting import (
    weighted_hours as weighted_hours,
)

# ``zones``.
from waterfall.core.portfolio.aggregation.zones import (
    ALERT as ALERT,
)
from waterfall.core.portfolio.aggregation.zones import (
    NOMINAL as NOMINAL,
)
from waterfall.core.portfolio.aggregation.zones import (
    WATCH as WATCH,
)
from waterfall.core.portfolio.aggregation.zones import (
    Zone as Zone,
)
from waterfall.core.portfolio.aggregation.zones import (
    ZoneCount as ZoneCount,
)
from waterfall.core.portfolio.aggregation.zones import (
    load_ratio as load_ratio,
)
from waterfall.core.portfolio.aggregation.zones import (
    load_zone as load_zone,
)
from waterfall.core.portfolio.aggregation.zones import (
    zone_distribution as zone_distribution,
)
