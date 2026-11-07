# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risk settings (FBS-3.3) offer to the API and the other modules.

The matrix of risks, read and written through ``cost_settings``, its rules held here: the six
bounds strictly increasing on each axis (WF-REF-0160); and the zone of a cell — a probability and a
severity — for the risks (EP-08). Another module imports from here.
"""

from waterfall.core.risk_settings.matrix import (
    BOUNDS_NOT_ORDERED as BOUNDS_NOT_ORDERED,
)
from waterfall.core.risk_settings.matrix import (
    level_of as level_of,
)
from waterfall.core.risk_settings.matrix import (
    matrix_faults as matrix_faults,
)
from waterfall.core.risk_settings.matrix import (
    zone_of as zone_of,
)
