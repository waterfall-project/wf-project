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

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface.projects import ProjectState, Viewer


@dataclass(frozen=True, slots=True)
class ProjectAtDate:
    """A project a scope retains: its state at the date, and its probability of winning now."""

    state: ProjectState
    win_probability: Decimal


@dataclass(frozen=True, slots=True)
class ClosedOffer:
    """An offer that left Pricing: its project, the state it reached, and when."""

    project_id: UUID
    to_state: ProjectState
    occurred_at: datetime


def projects_in_states_on(
    session: Session, states: Collection[ProjectState], before: datetime | None
) -> dict[UUID, ProjectAtDate]:
    """Give the projects whose state before ``before`` is one of these, with it; now if ``None``."""
    msg = "projects_in_states_on is filled by US-2670/L3"
    raise NotImplementedError(msg)


def offers_closed_between(session: Session, start: datetime, before: datetime) -> list[ClosedOffer]:
    """Give the offers that left Pricing from ``start`` on and before ``before``, in their order."""
    msg = "offers_closed_between is filled by US-2670/L3"
    raise NotImplementedError(msg)


def openable(session: Session, project_ids: Collection[UUID], viewer: Viewer) -> frozenset[UUID]:
    """Give those of the projects the reader opens: contributor of, or reader of them all."""
    msg = "openable is filled by US-2670/L3"
    raise NotImplementedError(msg)
