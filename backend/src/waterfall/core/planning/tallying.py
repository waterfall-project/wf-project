# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the nodes of the other kinds count under each task of a structure, private to the module.

The tallies of a structure (``FacetHooks.tally``; EP-26, "L'agrégat d'abord"): what a reading of
the tasks alone derives their numbers, their sums and their calendars from (US-2280), and what the
physical progress of the summaries weighs (``Tally.earnable``, US-1680). Moved out of ``reading`` by
US-1680, so that what the views ask of the physical progress reads them without importing the
reading, which imports the views.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.planning.interface.facets import Tally, facets
from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.writing import Place


def tallies_of(
    session: Session, place: Place, *, own_task: Collection[UUID] | None = None
) -> dict[UUID, Tally]:
    """Give, by task, what the nodes of the other kinds it bears count, a statement by kind.

    ``own_task`` the nodes to count each as its own task, and only them: what each weighs, by its
    node (``weighing``); every node of the structure, under the task bearing it, when none.

    Each kind's hooks count its nodes of the structure, which the planning names to them as a
    subquery — the node, the task bearing it, whether a risk provides for it —, grouped by task;
    the tallies of several kinds under a task are added.
    """
    found: dict[UUID, Tally] = {}
    for kind, hooks in facets().items():
        wanted = select(
            Node.id.label("node_id"),
            (Node.id if own_task is not None else Node.parent_id).label("task_id"),
            Node.origin_risk_id.is_not(None).label("from_risk"),
        ).where(
            Node.project_id == place.project_id,
            Node.structure_id == place.structure_id,
            Node.kind == kind,
        )
        if own_task is not None:
            wanted = wanted.where(Node.id.in_(list(own_task)))
        nodes = wanted.subquery()
        for task_id, tally in hooks.tally(session, place.project_id, nodes).items():
            held = found.get(task_id)
            found[task_id] = (
                tally
                if held is None
                else Tally(
                    held.amounts + tally.amounts,
                    held.count + tally.count,
                    held.own or tally.own,
                    held.held_open or tally.held_open,
                    held.calendars | tally.calendars,
                    held.earnable + tally.earnable,
                )
            )
    return found


def weighing(session: Session, place: Place, node_ids: Collection[UUID]) -> set[UUID]:
    """Give those of the nodes that weigh in the physical progress: a provision line does not.

    Each node counted as its own task, a statement by kind, none for no node (``Tally.earnable``,
    WF-IND-0060).
    """
    if not node_ids:
        return set()
    return {
        node_id
        for node_id, tally in tallies_of(session, place, own_task=node_ids).items()
        if tally.earnable
    }
