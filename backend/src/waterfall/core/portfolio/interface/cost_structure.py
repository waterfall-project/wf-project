# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of the costs of the portfolio (``getPortfolioCostStructure``; US-2720).

The documents ``portfolio_cost_structure``, weighted: the reference budget by cost type, provisions
left out, the remaining to commit by cost type, provisions included, their shares summing to one,
and the labour grouped by the current node of its role (WF-PTF-0080).

Declared by US-2670/L1, the socle of EP-11; filled by US-2720.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked


def read_portfolio_cost_structure(
    session: Session, asked: PortfolioAsked, at: datetime
) -> Document:
    """Give the structure of the costs of the scope at the instant ``at``."""
    msg = "read_portfolio_cost_structure is filled by US-2720"
    raise NotImplementedError(msg)
