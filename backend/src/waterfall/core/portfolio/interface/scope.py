# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scope of a view of the portfolio: its states, its date, its period, its node (US-2670).

What every view is asked, as the query of the contract says it, and the scope it retains
(``PortfolioScope``), which each answer gives back (WF-PTF-0010): the states asked or, without
them, the projects In progress, a state the view does not count being without effect, never
refused; the date of calculation, the current day of the time zone of the installation without
``as_of``; the period, the default one — the twelve months that end at the date — included, null
for a view that retains none, and its refusal (``PortfolioPeriodRefused``, 422); the node and its
label, an unknown node refused (422 on ``/query/org_node_id``); the number of projects retained.
One function resolves it for the eight views, the state of a project at a date being that of its
last transition dated that day or before (WF-CYC-0130).

Declared by US-2670/L1, the socle of EP-11; filled by US-2670/L3.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import ProjectState


@dataclass(frozen=True, slots=True)
class PortfolioAsked:
    """What a view is asked: ``states``, ``from``, ``to``, ``as_of`` and ``org_node_id``.

    Each absent when the query leaves it out: ``states`` empty for the default, ``as_of`` ``None``
    for the current day.
    """

    states: tuple[ProjectState, ...] = ()
    period_from: date | None = None
    period_to: date | None = None
    as_of: date | None = None
    org_node_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class PortfolioScope:
    """The scope a view retains (``PortfolioScope``).

    ``period_from`` and ``period_to`` are both null for a view that retains no period,
    ``org_node_label`` without a node.
    """

    states: tuple[ProjectState, ...]
    as_of: date
    period_from: date | None
    period_to: date | None
    org_node_id: UUID | None
    org_node_label: str | None
    project_count: int


def resolve_scope(
    session: Session, asked: PortfolioAsked, at: datetime, *, period: bool
) -> PortfolioScope:
    """Resolve what a view is asked at the instant ``at``, with a period if the view retains one.

    Refuses a period inverted or that starts after its default end (422), and an unknown node (422).
    """
    msg = "resolve_scope is filled by US-2670/L3"
    raise NotImplementedError(msg)
