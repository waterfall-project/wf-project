# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine replayed on a whole structure under its lock, private to the module.

What every write of the planning does once it has written (``writing``), and what a change of the
reference does to each structure of a current revision (``reference``): the structure locked, its
tree read under the lock, the engine run on it, the dates and the floats that change written, its
dates' instant moved on and its counter advanced. The interface offers it as ``reschedule``
(``interface.structures``); the frame of a write calls it here, so that the interface may frame a
write of the structure itself without the two files importing each other. A write that holds the
lock of the structure already hands the replay what it read under it (``Holding``, #2492): the
structure, not read again, what the engine's refusal names, and the links in conflict; and the
tree it read under the lock, which is brought to what the write made of it rather than read a
second time (``reshaped``, US-2250, #3169). The nodes of the other kinds under the tasks it
redated, and under those the write names, are then priced again by the hooks of their facets
(``FacetHooks.reinflate``, EP-07, "Le calcul des montants").

The base of a differential is replayed too, with the other structures of its revision (US-3050),
and no one reads it: the refusal that concerns one of its tasks names the task of the differential
of the same lineage, never a node of the base (#4213).

Written by US-1380/L2 in ``interface.structures``, moved here by US-1390/L2; ``Holding`` posed by
US-1380/L3, its tree by US-2250.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.planning.dating import dated, horizon_exceeded, kept, replay_of
from waterfall.core.planning.interface.facets import BearingTask, calendars_of, facets
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import TASK, read_tree, reshaped
from waterfall.core.planning.views import state_of
from waterfall.core.revisions.interface import (
    base_differential,
    structure_facts,
    structure_rescheduled,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import Origin
    from waterfall.core.planning.tables import TaskLink
    from waterfall.core.planning.tree import Conflict, Tree
    from waterfall.core.revisions.interface import StructureFacts


@dataclass(frozen=True, slots=True)
class Rescheduled:
    """A structure replayed: its tree as written, its links and calendars, what moved.

    ``is_main`` whether it is the main structure; ``reinflated`` the nodes of the other kinds whose
    amounts or year their hooks changed.
    """

    tree: Tree
    links: list[TaskLink]
    calendars: dict[UUID, Applicable]
    moved: frozenset[UUID]
    counter: int
    is_main: bool
    reinflated: frozenset[UUID] = frozenset()


@dataclass(frozen=True, slots=True)
class Named:
    """A task as the refusal of the horizon names it: its node, null for a task created, its label.

    ``row`` the row of the block of a paste that writes it, counted from zero as a refusal of the
    paste counts it (``PasteRejection.row``), so that two tasks created with one label are told
    apart (#3624); none for any other write.
    """

    node_id: UUID | None
    label: str
    row: int | None = None


@dataclass(frozen=True, slots=True)
class Blamed:
    """What a write names when the engine refuses it: the task it writes, where a loop starts.

    ``named`` the task beyond the horizon, or, for a write of several tasks, what each is named, by
    task: the task the engine finds beyond the horizon is named as it is there when it is one of
    them, and as the tree has it otherwise — a task the write moves without writing it. ``origin``
    the task whose predecessors are entered, a loop being named from it.
    """

    named: Named | Mapping[UUID, Named]
    origin: Origin = None


@dataclass(frozen=True, slots=True)
class Holding:
    """What a write of the tree under the lock of its structure hands the replay of the engine.

    ``facts`` the structure as the write read it under its lock, not read again (#2492), none to
    read it; ``blamed`` what the write names when the engine refuses it; ``conflicts`` the links
    in conflict read under the lock before the write, each by its two tasks and the manual task it
    names: a link it deletes in conflict moves the tasks it named that stay (``kept``). ``None``
    takes the conflicts of the structure as they are, which a recalculation writes none of.
    ``repriced`` the tasks whose nodes of the other kinds are priced again whether they moved or
    not: the bearer of a line written. ``tree`` the tree the write read under the lock, before it
    wrote, none to read it: the replay brings it to what the write made of it (``reshaped``),
    whatever the write created, deleted or moved.
    """

    facts: StructureFacts | None = None
    blamed: Blamed | None = None
    conflicts: Collection[Conflict] | None = None
    repriced: Collection[UUID] = ()
    tree: Tree | None = None


def replayed(
    session: Session,
    project_id: UUID,
    structure_id: UUID,
    at: datetime,
    held: Holding | None = None,
) -> Rescheduled:
    """Replay the engine on a structure locked, write what changes; give what it moved.

    The structure is locked (read under its lock unless ``held`` hands what the write read), its
    lines priced again, then its dates' instant moved on to ``at`` and its counter advanced: what
    follows the counter of the own estimate of a risk reads its total (EP-08, US-2570/L1). A tree
    ``held`` hands is brought to what the write made of it (``reshaped``), not read again.
    Beyond fifteen years (WF-PLA-0150), refused (422 ``PROJECT_HORIZON_EXCEEDED``), nothing
    written: naming the task the write blames — its node, none for a task created, its label, and
    the row of the block of a paste — or, without one, the task that finishes last; of a base, as
    its differential holds it (``_visible``). A loop of
    links is named from the origin the write gives (422 ``LINK_CYCLE``), a link across the
    hierarchy refused (``LINK_FORBIDDEN``).
    """
    held = held or Holding()
    blamed = held.blamed
    # The base of a differential is redated with the other structures of its revision (US-3050): a
    # base whose dates did not follow the calendars would make its differential read modified.
    facts = held.facts or structure_facts(session, project_id, structure_id, lock=True, base=True)
    session.flush()
    tree = (
        read_tree(session, project_id, structure_id)
        if held.tree is None
        else reshaped(session, project_id, structure_id, held.tree)
    )
    calendars = calendars_of(session, project_id, tree.tasks)
    replay = replay_of(
        session, (project_id, structure_id, facts.planning_start_on), tree, calendars
    )
    computed = dated(session, replay, None if blamed is None else blamed.origin)
    beyond = computed.horizon_exceeded_by
    if beyond is not None:
        named = _named(blamed, beyond, tree)
        if blamed is None:
            named = _visible(
                session, (project_id, structure_id), tree.nodes[beyond].lineage_id, named
            )
        raise horizon_exceeded(named.node_id, named.label, named.row)
    moved = kept(session, replay, computed, held.conflicts)
    session.flush()
    bearers = {each for each in moved if each in tree.tasks}
    for each in held.repriced:
        node = tree.nodes.get(each)
        bearer = each if each in tree.tasks else None if node is None else node.parent_id
        if bearer is not None:
            bearers.add(bearer)
    reinflated = _reinflated(session, (project_id, facts.is_main), tree, calendars, bearers)
    # Last, once the lines are priced: what follows the counter of an own estimate reads its total.
    counter = structure_rescheduled(session, project_id, structure_id, at)
    return Rescheduled(
        tree, replay.links, calendars, frozenset(moved), counter, facts.is_main, reinflated
    )


def _named(blamed: Blamed | None, beyond: UUID, tree: Tree) -> Named:
    """Name the task the engine finds beyond the horizon: as the write blames it, or as read."""
    named = None if blamed is None else blamed.named
    if isinstance(named, Named):
        return named
    found = Named(beyond, tree.tasks[beyond].label)
    return found if named is None else named.get(beyond, found)


def _visible(
    session: Session, structure: tuple[UUID, UUID], lineage_id: UUID, named: Named
) -> Named:
    """Name a task of a base by the task of its differential of the same lineage (#4213).

    ``structure`` is the project and the structure replayed: another than a base names its own
    task. No operation serves the base (US-3050), whose nodes no one reads: the differential's task
    is named by its node and its label as the differential has it, and a task the differential
    no longer holds by its label alone, its node null.
    """
    project_id, structure_id = structure
    differential = base_differential(session, project_id, structure_id)
    if differential is None:
        return named
    found = session.execute(
        select(Node.id, Task.label)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(
            Node.project_id == project_id,
            Node.structure_id == differential,
            Node.lineage_id == lineage_id,
            Node.kind == TASK,
        )
    ).first()
    return Named(None, named.label) if found is None else Named(found.id, found.label)


def _reinflated(
    session: Session,
    structure: tuple[UUID, bool],
    tree: Tree,
    calendars: dict[UUID, Applicable],
    bearers: Collection[UUID],
) -> frozenset[UUID]:
    """Price again the nodes of the other kinds the tasks named bear; give those that changed.

    ``structure`` is the project of the tree, and whether it is the main structure.
    """
    project_id, is_main = structure
    changed: set[UUID] = set()
    for kind, hooks in facets().items():
        held: dict[UUID, BearingTask] = {}
        for task_id in bearers:
            task = tree.tasks[task_id]
            bearer = BearingTask(
                task_id,
                tree.nodes[task_id].revision_id,
                task.label,
                WorkInstant(task.start_date, task.start_hours),
                WorkInstant(task.finish_date, task.finish_hours),
                calendars[task_id].calendar.week,
                state_of(tree, task_id).progress,
                is_main,
            )
            for line in tree.lines(task_id):
                if tree.nodes[line].kind == kind:
                    held[line] = bearer
        if held:
            changed |= hooks.reinflate(session, project_id, held)
    return frozenset(changed)
