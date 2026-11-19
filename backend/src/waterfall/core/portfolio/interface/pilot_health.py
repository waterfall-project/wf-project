# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The health of the control of the projects (``getPortfolioPilotHealth``; US-2750).

Four signals on the projects In progress: the review overdue on the delay of the reference
settings, the risks not reviewed (``reviewed_since``), no cost imported since the last marked
revision (``last_imports``), the tracked milestone overdue (``portfolio_milestones``); their zone,
their parameters and ``can_open`` (WF-PTF-0110, WF-REF-0180).

Declared by US-2670/L1, the socle of EP-11; filled by US-2750.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked
    from waterfall.core.projects.interface import Viewer


def read_pilot_health(
    session: Session, asked: PortfolioAsked, at: datetime, viewer: Viewer
) -> Document:
    """Give the signals of the projects of the scope at the instant ``at``."""
    msg = "read_pilot_health is filled by US-2750"
    raise NotImplementedError(msg)
