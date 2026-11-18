# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio is worth (``getPortfolioValue``; US-2690).

The order book of the projects In progress, the pipeline of the offers, gross and weighted by their
probabilities of winning, the value delivered by the projects completed in the period, and the rate
of conversion of the offers closed in it (WF-PTF-0050, WF-PTF-0020): the documents ``project``,
``estimate`` and ``remaining`` of the indicators, summed.

Declared by US-2670/L1, the socle of EP-11; filled by US-2690/L2.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked


def read_portfolio_value(session: Session, asked: PortfolioAsked, at: datetime) -> Document:
    """Give the values of the portfolio of the scope at the instant ``at``."""
    msg = "read_portfolio_value is filled by US-2690/L2"
    raise NotImplementedError(msg)
