# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the indicator settings (FBS-3.4) offer to the API and the other modules.

The thresholds of the indices and the delay between two reviews, read and written through
``cost_settings``, their rules held here (WF-REF-0170, WF-REF-0180); and the zone of an index for
the indicators (EP-10). Another module imports from here.
"""

from waterfall.core.indicator_settings.thresholds import (
    ThresholdTexts as ThresholdTexts,
)
from waterfall.core.indicator_settings.thresholds import (
    delay_faults as delay_faults,
)
from waterfall.core.indicator_settings.thresholds import (
    index_zone as index_zone,
)
from waterfall.core.indicator_settings.thresholds import (
    read_thresholds as read_thresholds,
)
