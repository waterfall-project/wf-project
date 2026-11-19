# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of the portfolio (``getPortfolioWorkload``; US-2700).

The documents ``portfolio_workload`` of the projects In progress and of the offers, weighted, summed
by role and by month over the horizon; the roles retained — all the active ones, or those of the
node and its descendants — and their capacity calculated, the rate of load and the zone of each
month, under-load flagged as much as overload (WF-PTF-0060).

Declared by US-2670/L1, the socle of EP-11; filled by US-2700.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked


def read_portfolio_workload(
    session: Session,
    asked: PortfolioAsked,
    at: datetime,
    *,
    horizon_months: int,
    under_load_threshold: Decimal,
) -> Document:
    """Give the workload of the scope at the instant ``at``, over its horizon, at its threshold."""
    msg = "read_portfolio_workload is filled by US-2700"
    raise NotImplementedError(msg)
