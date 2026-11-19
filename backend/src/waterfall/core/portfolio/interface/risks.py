# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the portfolio (``getPortfolioRisks``; US-2730).

The documents ``portfolio_risks``, without weighting: the total of the identified provisions, the
heaviest risks with their project and ``can_open``, the matrix classified on the current bounds; the
coverage summed from the documents ``remaining``; the provisions occurred and dismissed in the
period (WF-PTF-0090).

Declared by US-2670/L1, the socle of EP-11; filled by US-2730.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked
    from waterfall.core.projects.interface import Viewer


def read_portfolio_risks(
    session: Session, asked: PortfolioAsked, at: datetime, viewer: Viewer
) -> Document:
    """Give the risks of the scope at the instant ``at``, the projects the reader opens told."""
    msg = "read_portfolio_risks is filled by US-2730"
    raise NotImplementedError(msg)
