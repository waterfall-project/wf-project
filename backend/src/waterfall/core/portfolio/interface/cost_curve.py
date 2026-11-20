# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The S-curve of the portfolio (``getPortfolioCostCurve``; US-2740).

The documents ``cost_curve`` and ``cost_curve_payment_delays`` of the indicators, and
``portfolio_offer_curves`` weighted, summed month by month over the twelve months before that of
the date and the horizon; on request, the cash-out with the payment delays, detailed by month.
Nothing is calculated again (WF-PTF-0100).

Declared by US-2670/L1, the socle of EP-11; filled by US-2740.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked, PortfolioReading


def read_portfolio_cost_curve(
    session: Session,
    asked: PortfolioAsked,
    reading: PortfolioReading,
    *,
    horizon_months: int,
    payment_delays: bool,
) -> Document:
    """Give the S-curve of the scope read by ``reading``, over its horizon."""
    msg = "read_portfolio_cost_curve is filled by US-2740"
    raise NotImplementedError(msg)
