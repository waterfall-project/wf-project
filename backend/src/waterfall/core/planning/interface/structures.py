# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The dates of a structure: the engine replayed on it, its start date and its label written.

``reschedule`` runs the engine (``scheduling``, pure) on a whole structure under its lock, writes
the dates and the floats that change and moves ``scheduled_at`` on (EP-06, "Modules"): every write
of a node does the same through its frame (``writing``, US-1380/L2), which names the task it wrote
when the horizon is crossed; ``reschedule`` serves a write that names none — a calendar, the
constants of the units, the start of the structure (US-1390/L2). ``update_cost_structure`` writes
the date the planning of a structure starts on and its label (``updateCostStructure``, #2170;
US-1390/L2).

Declared by US-1380/L1; ``reschedule`` filled by US-1380/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.dating import dated, horizon_exceeded, kept, replay_of
from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.tree import read_tree
from waterfall.core.revisions.interface import structure_facts, structure_rescheduled

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.tables import TaskLink
    from waterfall.core.planning.tree import Tree
    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class Rescheduled:
    """A structure replayed: its tree as written, its links and calendars, what moved."""

    tree: Tree
    links: list[TaskLink]
    calendars: dict[UUID, Applicable]
    moved: frozenset[UUID]
    counter: int


def reschedule(
    session: Session,
    project_id: UUID,
    structure_id: UUID,
    at: datetime,
    blamed: tuple[UUID | None, str] | None = None,
) -> Rescheduled:
    """Replay the engine on a structure locked, write what changes; give what it moved.

    The structure is locked, its dates' instant moved on to ``at`` and its counter advanced.
    Beyond fifteen years (WF-PLA-0150), refused (422 ``PROJECT_HORIZON_EXCEEDED``), nothing
    written: naming ``blamed`` — the node of the task written, none for a task created, and its
    label — or, without one, the task that finishes last.
    """
    facts = structure_facts(session, project_id, structure_id, lock=True)
    session.flush()
    tree = read_tree(session, project_id, structure_id)
    calendars = calendars_of(session, project_id, tree.tasks)
    replay = replay_of(
        session, (project_id, structure_id, facts.planning_start_on), tree, calendars
    )
    computed = dated(replay)
    beyond = computed.horizon_exceeded_by
    if beyond is not None:
        node_id, label = blamed or (beyond, tree.tasks[beyond].label)
        raise horizon_exceeded(node_id, label)
    moved = kept(replay, computed)
    session.flush()
    counter = structure_rescheduled(session, project_id, structure_id, at)
    return Rescheduled(tree, replay.links, calendars, frozenset(moved), counter)


def update_cost_structure(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Write the start date and the label of a structure, and redate it."""
    msg = "update_cost_structure is filled by US-1390/L2"
    raise NotImplementedError(msg)
