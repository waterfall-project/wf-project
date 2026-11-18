# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of the summary tasks, which the planning asks the indicators (US-1680).

A registry of this module (EP-10, "Les points d'extension"), filled by the indicators at the import
of their interface: a reading of a structure asks it once, for the summaries it gives, and sets
``TaskFacet.physical_progress``; none while nothing answers. What it is asked holds what the reading
holds already (``SummariesAsked``) — the structure, the summaries, each task with its parent and
whether it is completed, a summary's state derived from its subordinates (WF-PLA-0040) —, and the
budgeted amounts each task bears, the provisions left out, are read by the tally of the facets of
the structure in one statement grouped by task (``earnable_amounts``), or handed on by a reading of
the tasks alone, which read them already (EP-10, "L'avancement physique"). The share answered is
opaque here: a value, or the reason it is not computed (``PhysicalShare``).

Declared by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the planning; filled
by US-1680, which gives what it is asked its form: the summaries of one structure, which their
revision alone does not name.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.tallying import tallies_of
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface.facets import Tally
    from waterfall.core.planning.writing import Place


@dataclass(frozen=True, slots=True)
class ProgressTask:
    """A task of a structure as the physical progress reads it: its parent, whether completed."""

    parent_id: UUID | None
    completed: bool


@dataclass(frozen=True, slots=True)
class SummariesAsked:
    """What a reading asks the physical progress of: the summaries of a structure it gives.

    ``tasks`` every task of the structure, by its node; ``tallies`` what a reading of the tasks
    alone read already of the nodes each bears, none for a reading that did not.
    """

    place: Place
    summaries: frozenset[UUID]
    tasks: Mapping[UUID, ProgressTask]
    tallies: Mapping[UUID, Tally] | None = None


@dataclass(frozen=True, slots=True)
class PhysicalShare:
    """The physical progress of a summary: its value, or the reason it is not computed."""

    value: Decimal | None
    reason: str | None


# What gives, of the summaries asked, the physical progress of each.
type PhysicalProgress = Callable[[Session, SummariesAsked], Mapping[UUID, PhysicalShare]]

_PHYSICAL_PROGRESS: Registry[PhysicalProgress] = Registry("planning.physical_progress")


def register_physical_progress(progress: PhysicalProgress) -> Callable[[], None]:
    """Add what gives the physical progress of the summary tasks; give its withdrawal.

    It answers for the summaries it is asked at once, so that a reading asks once and not once a
    summary.
    """
    return _PHYSICAL_PROGRESS.register(progress)


def physical_progress_of(session: Session, asked: SummariesAsked) -> dict[UUID, PhysicalShare]:
    """Give the physical progress of the summaries asked, by any module; none while none answers."""
    found: dict[UUID, PhysicalShare] = {}
    if not asked.summaries:
        return found
    for progress in _PHYSICAL_PROGRESS.entries():
        found.update(progress(session, asked))
    return found


def earnable_amounts(session: Session, asked: SummariesAsked) -> dict[UUID, Decimal]:
    """Give the budgeted amounts each task of the structure bears, the provisions left out.

    Of the tallies the reading handed on, or read once, in one statement grouped by task by kind
    (``Tally.earnable``); a task that bears nothing is left out.
    """
    tallies = tallies_of(session, asked.place) if asked.tallies is None else asked.tallies
    return {task_id: tally.earnable for task_id, tally in tallies.items()}
