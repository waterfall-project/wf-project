# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The performance of the portfolio (``getPortfolioPerformance``; US-2710).

The quantities of the documents ``project`` of the projects In progress summed, then the formulas of
the indicators applied to the sums — an index of the portfolio is a ratio of sums, never an average
of indices (WF-PTF-0020) —, the variances, the three projections, the distribution by zone, and the
evolution by quarter, each past quarter read at its last day (WF-PTF-0070).

Declared by US-2670/L1, the socle of EP-11; filled by US-2710.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked


def read_portfolio_performance(session: Session, asked: PortfolioAsked, at: datetime) -> Document:
    """Give the performance of the scope at the instant ``at``."""
    msg = "read_portfolio_performance is filled by US-2710"
    raise NotImplementedError(msg)
