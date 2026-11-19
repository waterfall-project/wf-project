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

It gives each view, besides that scope, the projects it retains (``ResolvedScope``): those whose
state at the date is both asked and one the view counts, which the view names (``counted``) — a
project Completed by its completion in the period (``PortfolioStates``) —, so that
``project_count`` is their number for every view (EP-11, "Les vues"); and, for each, its
state, the revision it contributes by and its weight (EP-11, "La contribution d'un projet"). A view
reads the contributions of these projects and of no other, and does not resolve them again.

Declared by US-2670/L1, the socle of EP-11; filled by US-2670/L3.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date, datetime
    from decimal import Decimal
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


@dataclass(frozen=True, slots=True)
class RetainedProject:
    """A project a view retains: its state at the date, the revision it contributes by, its weight.

    ``revision_id`` is, on the current day, the current revision of the project — the revision in
    progress or, without one, the last marked —, and at a past date its last revision marked by the
    end of that day; it is null for a project none of whose revisions was marked by then, which is
    retained by its state and contributes to no sum. ``weight`` is one for a project In progress or
    Completed; for an offer, the probability of winning its revision kept at the marking, or that of
    the project on the current day; null when ``revision_id`` is.
    """

    state: ProjectState
    revision_id: UUID | None
    weight: Decimal | None


@dataclass(frozen=True, slots=True)
class ResolvedScope:
    """The scope a view gives back, and the projects it retains, by their identifier.

    ``scope.project_count`` is the number of ``projects``; ``on_current_day`` says whether the
    contributions are read for the current day (``day_documents_of``) or kept by the revisions
    retained (``kept_documents_of``).
    """

    scope: PortfolioScope
    projects: Mapping[UUID, RetainedProject]
    on_current_day: bool


def resolve_scope(
    session: Session,
    asked: PortfolioAsked,
    at: datetime,
    *,
    counted: frozenset[ProjectState],
    period: bool,
) -> ResolvedScope:
    """Resolve what a view is asked at the instant ``at``, with a period if the view retains one.

    ``counted`` is the states the view counts: a state asked outside it stays in ``scope.states``
    and retains no project. Refuses a period inverted or that starts after its default end (422),
    and an unknown node (422).
    """
    msg = "resolve_scope is filled by US-2670/L3"
    raise NotImplementedError(msg)
