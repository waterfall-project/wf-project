# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine replayed on a whole structure under its lock, private to the module.

What every write of the planning does once it has written (``writing``), and what a change of the
reference does to each structure of a current revision (``reference``): the structure locked, its
tree read under the lock, the engine run on it, the dates and the floats that change written, its
dates' instant moved on and its counter advanced. The interface offers it as ``reschedule``
(``interface.structures``); the frame of a write calls it here, so that the interface may frame a
write of the structure itself without the two files importing each other.

Written by US-1380/L2 in ``interface.structures``, moved here by US-1390/L2.
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
    from waterfall.core.planning.scheduling import Origin
    from waterfall.core.planning.tables import TaskLink
    from waterfall.core.planning.tree import Tree


@dataclass(frozen=True, slots=True)
class Rescheduled:
    """A structure replayed: its tree as written, its links and calendars, what moved."""

    tree: Tree
    links: list[TaskLink]
    calendars: dict[UUID, Applicable]
    moved: frozenset[UUID]
    counter: int


@dataclass(frozen=True, slots=True)
class Blamed:
    """What a write names when the engine refuses it: the task it writes, where a loop starts.

    ``node_id`` and ``label`` name the task beyond the horizon — the node null for a task created
    —, ``origin`` the task whose predecessors are entered, a loop being named from it.
    """

    node_id: UUID | None
    label: str
    origin: Origin = None


def replayed(
    session: Session,
    project_id: UUID,
    structure_id: UUID,
    at: datetime,
    blamed: Blamed | None = None,
) -> Rescheduled:
    """Replay the engine on a structure locked, write what changes; give what it moved.

    The structure is locked, its dates' instant moved on to ``at`` and its counter advanced.
    Beyond fifteen years (WF-PLA-0150), refused (422 ``PROJECT_HORIZON_EXCEEDED``), nothing
    written: naming ``blamed`` — the node of the task written, none for a task created, and its
    label — or, without one, the task that finishes last. A loop of links is named from the
    origin ``blamed`` gives (422 ``LINK_CYCLE``), a link across the hierarchy refused
    (``LINK_FORBIDDEN``).
    """
    facts = structure_facts(session, project_id, structure_id, lock=True)
    session.flush()
    tree = read_tree(session, project_id, structure_id)
    calendars = calendars_of(session, project_id, tree.tasks)
    replay = replay_of(
        session, (project_id, structure_id, facts.planning_start_on), tree, calendars
    )
    computed = dated(replay, None if blamed is None else blamed.origin)
    beyond = computed.horizon_exceeded_by
    if beyond is not None:
        if blamed is None:
            raise horizon_exceeded(beyond, tree.tasks[beyond].label)
        raise horizon_exceeded(blamed.node_id, blamed.label)
    moved = kept(replay, computed)
    session.flush()
    counter = structure_rescheduled(session, project_id, structure_id, at)
    return Rescheduled(tree, replay.links, calendars, frozenset(moved), counter)
