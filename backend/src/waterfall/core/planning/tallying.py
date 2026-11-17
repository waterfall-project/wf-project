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
    from uuid import UUID

    from sqlalchemy import Subquery
    from sqlalchemy.orm import Session

    from waterfall.core.planning.writing import Place


def _named(place: Place, kind: str) -> Subquery:
    """Name the nodes of a kind to the hooks: ``node_id``, ``task_id`` bearing it, ``from_risk``."""
    return (
        select(
            Node.id.label("node_id"),
            Node.parent_id.label("task_id"),
            Node.origin_risk_id.is_not(None).label("from_risk"),
        )
        .where(
            Node.project_id == place.project_id,
            Node.structure_id == place.structure_id,
            Node.kind == kind,
        )
        .subquery()
    )


def tallies_of(session: Session, place: Place) -> dict[UUID, Tally]:
    """Give, by task, what the nodes of the other kinds it bears count, a statement by kind.

    Each kind's hooks count its nodes of the structure, which the planning names to them as a
    subquery — the node, the task bearing it, whether a risk provides for it —, grouped by task;
    the tallies of several kinds under a task are added.
    """
    found: dict[UUID, Tally] = {}
    for kind, hooks in facets().items():
        for task_id, tally in hooks.tally(session, place.project_id, _named(place, kind)).items():
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


def provisions_of(session: Session, place: Place) -> set[UUID]:
    """Give the nodes of the structure that are lines of provision, whatever their amount.

    Each kind's hooks name those of its nodes of the structure, given as a subquery, not one by
    one: a statement by kind, whatever the size of the plan (WF-IND-0060).
    """
    return {
        node_id
        for kind, hooks in facets().items()
        for node_id in hooks.provisions(session, place.project_id, _named(place, kind))
    }
