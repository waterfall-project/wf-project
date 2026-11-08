# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The plan of a planning of MS Project written into its structure, private to the module.

The application of an import (US-1430/L3) builds its plan again under the lock of the structure
(``importing``), refuses it as the analysis would — the first refusal of the whole file, its code
and its parameters (``ImportReport.refusals``) —, then writes it in the transaction of its task:
the start of the structure, the links the file replaces, the places of the tree — every node
whose place changes parked first above any rank, so that the rank stays unique under its parent
at each statement, the tasks the file no longer carries removed once the others left them —, the
facets, then the engine replayed on the structure (``rescheduling``), which dates it, moves its
instant on and advances its counter. A task matched keeps its lineage, its state, its attachment
and its external identifier (WF-INTF-0040); a summary the file makes a leaf takes the state its
subordinates gave it (WF-PLA-0040). The undo history receives nothing (WF-IHM-0110).
"""

from dataclasses import replace
from itertools import count
from typing import TYPE_CHECKING

from sqlalchemy import insert

# By its module: its own imports reach the interface, which reaches this module again.
from waterfall.core.planning import importing
from waterfall.core.planning.dating import MANUAL, conflicts_of
from waterfall.core.planning.rescheduling import Holding, replayed
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.shaping import PARKED, deleted, emptied, stamp
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import TASK
from waterfall.core.planning.views import NOT_STARTED
from waterfall.core.revisions.interface import write_structure
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.importing import Facet, Pair, Plan, Row
    from waterfall.core.revisions.interface import StructureFacts
    from waterfall.platform.audit import Act


def _refuse(plan: Plan) -> None:
    """Refuse a file the plan rejects whole, by its first reason (WF-INTF-0040, WF-PLA-0150)."""
    if plan.refusals:
        first = plan.refusals[0]
        raise UnprocessableError(first["code"], first["params"])


def _links(session: Session, plan: Plan, facts: StructureFacts) -> list[dict[str, object]]:
    """Replace the links of the structure by the file's; give those to add once the tasks are.

    The links kept change in place; those removed go before any node, which would take some away
    by its cascade.
    """
    held: dict[Pair, TaskLink] = {
        (link.predecessor_id, link.successor_id): link for link in plan.aimed.links
    }
    for pair, link in held.items():
        if pair not in plan.links:
            session.delete(link)
    added: list[dict[str, object]] = []
    for pair, (link_type, lag) in plan.links.items():
        link = held.get(pair)
        if link is None:
            added.append(
                {
                    "project_id": plan.aimed.project_id,
                    "id": new_id(),
                    "revision_id": facts.revision_id,
                    "structure_id": facts.structure_id,
                    "predecessor_id": pair[0],
                    "successor_id": pair[1],
                    "link_type": link_type,
                    "lag_value": lag.value,
                    "lag_unit": lag.unit,
                    "in_conflict": False,
                }
            )
            continue
        link.link_type, link.lag_value, link.lag_unit = link_type, lag.value, lag.unit
    session.flush()
    return added


def _node(plan: Plan, facts: StructureFacts, node_id: UUID, act: Act) -> Node:
    """Give the node of a task the file creates, its lineage its own, its rank to be set."""
    return Node(
        project_id=plan.aimed.project_id,
        id=node_id,
        revision_id=facts.revision_id,
        structure_id=facts.structure_id,
        lineage_id=node_id,
        kind=TASK,
        parent_id=plan.parent_of(node_id),
        rank=PARKED,
        origin_risk_id=None,
        lock_version=1,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
    )


def _places(session: Session, plan: Plan, facts: StructureFacts, act: Act) -> set[UUID]:
    """Write the tree the file gives: the nodes created, the others moved; give those moved.

    Every node whose place changes is parked first; the tasks removed go once no node the file
    keeps lies under them, then each node takes its rank among its siblings.
    """
    tree = plan.aimed.tree
    final = {
        child: (parent, rank)
        for parent, children in plan.children.items()
        for rank, child in enumerate(children, start=1)
    }
    turn = count(PARKED + 1)
    created: dict[UUID, Node] = {}
    for node_id in plan.order:
        if node_id not in tree.nodes:
            created[node_id] = _node(plan, facts, node_id, act)
            created[node_id].rank = next(turn)
            session.add(created[node_id])
    # A node moved under a task created needs it written: an update would come first.
    session.flush()
    moved: set[UUID] = set()
    for node_id, place in final.items():
        node = tree.nodes.get(node_id)
        if node is not None and (node.parent_id, node.rank) != place:
            node.parent_id, node.rank = place[0], next(turn)
            moved.add(node_id)
    session.flush()
    if plan.removed:
        deleted(session, plan.aimed.project_id, tree, plan.removed)
    for node_id in [*created, *moved]:
        (created.get(node_id) or tree.nodes[node_id]).rank = final[node_id][1]
    session.flush()
    return moved


def _created(row: Row, facet: Facet, facts: StructureFacts) -> dict[str, object]:
    """Give the facet of a task the file creates: not started, its ``UID`` kept (WF-INTF-0040).

    An automatic task stands at the planning start until the engine places it.
    """
    start = facet.start or WorkInstant(facts.planning_start_on)
    finish = facet.finish or start
    return {
        "node_id": row.node_id,
        "structure_id": facts.structure_id,
        "kind": TASK,
        "label": facet.label,
        "description": facet.description,
        "scheduling_mode": facet.mode,
        "duration_value": facet.duration.value,
        "duration_unit": facet.duration.unit,
        "start_date": start.day,
        "start_hours": start.hours,
        "finish_date": finish.day,
        "finish_hours": finish.hours,
        "progress": NOT_STARTED,
        "external_id": str(row.task.uid),
        "total_float_days": None,
        "is_critical": False,
    }


def _update(plan: Plan, row: Row) -> bool:
    """Write on a task matched what the file gives it, its state and attachment untouched.

    A summary the file makes a leaf takes first the state its subordinates gave it. Tell whether
    the task changed.
    """
    tree, facet = plan.aimed.tree, row.facet
    if facet is None:
        return False
    changed = bool(importing.task_fields(plan, row))
    task = tree.tasks[row.node_id]
    if tree.is_summary(row.node_id) and not plan.is_summary(row.node_id):
        emptied(tree, row.node_id)
        changed = True
    task.label, task.description = facet.label, facet.description
    if not plan.is_summary(row.node_id):
        started = task.progress != NOT_STARTED and facet.duration.value == 0
        task.scheduling_mode = facet.mode
        if not started:
            task.duration_value, task.duration_unit = facet.duration.value, facet.duration.unit
        if facet.mode == MANUAL and facet.start is not None and facet.finish is not None:
            task.start_date, task.start_hours = facet.start.day, facet.start.hours
            task.finish_date, task.finish_hours = facet.finish.day, facet.finish.hours
    return changed


def apply_plan(session: Session, plan: Plan, act: Act) -> None:
    """Write the plan of an import into its structure, held under its lock, and redate it."""
    _refuse(plan)
    facts = plan.aimed.facts
    if facts is None:
        msg = "an import is applied to a structure the current revision holds"
        raise ValueError(msg)
    project_id, structure_id = plan.aimed.project_id, facts.structure_id
    conflicts = conflicts_of(plan.aimed.links)
    if plan.start is not None and plan.start != facts.planning_start_on:
        write_structure(session, project_id, structure_id, (plan.start, None), act)
        facts = replace(facts, planning_start_on=plan.start)
    added = _links(session, plan, facts)
    moved = _places(session, plan, facts, act)
    tree = plan.aimed.tree
    facets: list[dict[str, object]] = []
    for row in plan.by_node.values():
        if row.old is None and row.facet is not None:
            facets.append({**_created(row, row.facet, facts), "project_id": project_id})
        elif _update(plan, row) or row.node_id in moved:
            stamp(tree.nodes[row.node_id], act)
    session.flush()
    if facets:
        session.execute(insert(Task), facets)
    if added:
        session.execute(insert(TaskLink), added)
    replayed(session, project_id, structure_id, act.at, Holding(facts, None, conflicts))
