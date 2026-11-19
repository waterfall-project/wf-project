# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio reads of several projects at once (EP-11, US-2670).

The projects a scope retains by the state each had at a date, that of its last transition before the
end of that day (WF-CYC-0130), with their probability of winning, the weight of an offer on the
current day (EP-11, "La contribution d'un projet"); the offers that left Pricing in a period, by
the instant of their transition, its bounds included, for the rate of conversion; and, of a list of
projects, those the reader opens (``can_open``, WF-PTF-0030), which a reader who holds
``all_projects_read`` opens all. Each in one query.

Declared by US-2670/L1, the socle of EP-11; filled by US-2670/L3.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import distinct_on

from waterfall.core.projects.commands import TERMINAL
from waterfall.core.projects.tables import STATES, Contributor, Project, ProjectStateTransition

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface.projects import ProjectState, Viewer

# The place of a state in the cycle, the terminal states sharing the last: two transitions of a
# project can share an instant (its creation and its first revision), and the cycle only goes
# forward, so the state reached ranks them, as the history of the project does (WF-CYC-0130).
_RANKS = {state: min(rank, len(STATES) - len(TERMINAL)) for rank, state in enumerate(STATES)}


@dataclass(frozen=True, slots=True)
class ProjectAtDate:
    """A project a scope retains: its state at the date, and its probability of winning now.

    ``entered_at`` is the instant of the transition that brought it to that state: for a project
    Completed, its completion, which a period retains by its day (``PortfolioStates``).
    """

    state: ProjectState
    win_probability: Decimal
    entered_at: datetime


@dataclass(frozen=True, slots=True)
class ClosedOffer:
    """An offer that left Pricing: its project, the state it reached, and when."""

    project_id: UUID
    to_state: ProjectState
    occurred_at: datetime


def projects_in_states_on(
    session: Session, states: Collection[ProjectState], before: datetime | None
) -> dict[UUID, ProjectAtDate]:
    """Give the projects whose state before ``before`` is one of these, with it; now if ``None``.

    The state of a project before an instant is that of its last transition dated before it, two of
    one instant ranked by the state reached; a project created after the instant has none, and is
    left out. Every change of state writes its transition (WF-CYC-0130): without ``before``, the
    last of each project is its state now. One query, every project at once.
    """
    if not states:
        return {}
    rank = case(_RANKS, value=ProjectStateTransition.to_state)
    last = (
        select(
            ProjectStateTransition.project_id,
            ProjectStateTransition.to_state,
            ProjectStateTransition.occurred_at,
        )
        .ext(distinct_on(ProjectStateTransition.project_id))
        .order_by(
            ProjectStateTransition.project_id,
            ProjectStateTransition.occurred_at.desc(),
            rank.desc(),
        )
    )
    if before is not None:
        last = last.where(ProjectStateTransition.occurred_at < before)
    reached = last.subquery()
    rows = session.execute(
        select(
            reached.c.project_id, reached.c.to_state, reached.c.occurred_at, Project.win_probability
        )
        .join(Project, Project.id == reached.c.project_id)
        .where(reached.c.to_state.in_(list(states)))
    )
    return {
        row.project_id: ProjectAtDate(row.to_state, row.win_probability, row.occurred_at)
        for row in rows
    }


def offers_closed_between(session: Session, start: datetime, before: datetime) -> list[ClosedOffer]:
    """Give the offers that left Pricing from ``start`` on and before ``before``, in their order.

    A statistic of a period retains a transition by its instant (WF-CYC-0130): the caller passes the
    start of the first day of the period and that of the day after its last, so that an offer lost
    on a day of it enters it, and that of no other period. Every exit of Pricing is given — won,
    lost, abandoned —: the rate of conversion chooses its denominator. One query.
    """
    rows = session.execute(
        select(
            ProjectStateTransition.project_id,
            ProjectStateTransition.to_state,
            ProjectStateTransition.occurred_at,
        )
        .where(
            ProjectStateTransition.from_state == "pricing",
            ProjectStateTransition.occurred_at >= start,
            ProjectStateTransition.occurred_at < before,
        )
        .order_by(ProjectStateTransition.occurred_at, ProjectStateTransition.project_id)
    )
    return [ClosedOffer(row.project_id, row.to_state, row.occurred_at) for row in rows]


def openable(session: Session, project_ids: Collection[UUID], viewer: Viewer) -> frozenset[UUID]:
    """Give those of the projects the reader opens: contributor of, or reader of them all.

    A reader who holds ``all_projects_read`` (``Viewer.sees_all``, its one definition) opens every
    one; another, those it is inscribed on, of any kind, as the list of the projects keeps them
    (WF-PTF-0030, WF-PRJ-0060). One query, none for the first.
    """
    if not project_ids:
        return frozenset()
    if viewer.sees_all:
        return frozenset(project_ids)
    inscribed = session.scalars(
        select(Contributor.project_id).where(
            Contributor.user_account_id == viewer.user_id,
            Contributor.project_id.in_(list(project_ids)),
        )
    )
    return frozenset(inscribed)
