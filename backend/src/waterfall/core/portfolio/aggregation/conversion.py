# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The conversion rate: the offers won over the offers out of pricing in a period (WF-PTF-0050).

Pure. The destinations are those of the offers that left the Pricing state in the period, scope or
not (WF-CYC-0130): a transition to In progress is a win, one to Lost a loss; an offer abandoned
counts in neither, so that it does not change the rate.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.portfolio.aggregation.ratios import ratio_of

if TYPE_CHECKING:
    from collections.abc import Iterable

    from waterfall.core.indicators.interface import Computable

NO_OFFER_OUT_OF_PRICING = "no_offer_out_of_pricing"
WON = "in_progress"
LOST = "lost"


def conversion_rate(destinations: Iterable[str]) -> Computable:
    """Give the share of the offers out of pricing that went to In progress, to four decimals.

    Not computable, ``no_offer_out_of_pricing``, when none went to In progress or to Lost.
    """
    held = list(destinations)
    won = held.count(WON)
    out = won + held.count(LOST)
    return ratio_of(Decimal(won), Decimal(out), NO_OFFER_OUT_OF_PRICING)
