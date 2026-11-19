# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the projects of the portfolio (``getPortfolioProjects``; US-2690).

One row by project retained, formed of the documents ``project``, ``estimate`` and ``remaining``
of the indicators (WF-PTF-0040): its label, its code, its state, its reference budget or its current
estimate and its probability, the projection of its manager, its variance to the reference and its
indices for a project In progress, and the instant of its last marked revision. The filter, the
sort and the paging are made on the rows formed, in memory (EP-11, "Les vues"). A project the
reader cannot open is listed under its label and its code, ``can_open`` false (WF-PTF-0030).

Declared by US-2670/L1, the socle of EP-11; filled by US-2690/L2, which adds to ``PortfolioListing``
the filters by column US-2690/L1 writes in the contract.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document
    from waterfall.core.portfolio.interface.scope import PortfolioAsked
    from waterfall.core.projects.interface import Viewer


@dataclass(frozen=True, slots=True)
class PortfolioListing:
    """How the list is searched, filtered by zone, sorted and paged, as the query says it.

    ``sort_by`` is a column of the contract, the label by default.
    """

    limit: int
    offset: int
    search: str | None = None
    zones: tuple[str, ...] = ()
    sort_by: str = "label"
    descending: bool = False


def read_portfolio_projects(
    session: Session, asked: PortfolioAsked, listing: PortfolioListing, at: datetime, viewer: Viewer
) -> Document:
    """Give the page of the projects of the scope at the instant ``at``, as the contract says it."""
    msg = "read_portfolio_projects is filled by US-2690/L2"
    raise NotImplementedError(msg)
