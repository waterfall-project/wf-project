# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The skeleton of a planning, engendered from the work breakdown of its project.

``generatePlanningSkeleton``, under the command ``generate_skeleton`` of the revision (EP-06,
US-1460): on the main structure of a revision that has no task, one summary task per work package
and per order item, attached to it (WF-PLA-0170), that of an item under that of its work package,
one leaf of a day, automatic, per deliverable under its item, and an end milestone per item and per
work package, with their links: the milestone of an item follows the deliverables of the item, that
of a work package the milestones of its items, finish to start without lag. The plan is written in
one entry of the history, the structure redated once, and given back as every write of the grid is
(``NodesWritten``), in the order of the plan. Nothing links the tasks to the work breakdown but
their attachment: modifying it afterwards moves no task (WF-PRJ-0030).

The work breakdown is read before the structure is locked, and the work packages and items it
names are locked ``FOR SHARE`` meanwhile — as a task attached to one does — so that
``set_work_breakdown`` neither deletes nor marks them before this transaction ends; an element
that left it between the reading and the lock is left out of the plan.

Declared by US-1380/L1; filled by US-1460.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import exists, insert, select

from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import TASK
from waterfall.core.planning.writing import facts_of, writing
from waterfall.core.projects.interface import (
    WorkBreakdownFilters,
    read_work_breakdown,
    work_breakdown_items,
)
from waterfall.core.revisions.interface import last_marked_revisions, revision_draft
from waterfall.platform.errors import ConflictError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.writing import NodesWritten, Place, Write, Writer

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
MAIN_STRUCTURE_WITHOUT_TASKS = "main_structure_without_tasks"
NOT_STARTED = "not_started"
AUTOMATIC = "automatic"
# The longest label of a task; the end milestone of an element adds its words to the element's.
LABEL_LENGTH = 300
END_OF = "Fin de « {} »"
ELLIPSIS = "…"


@dataclass(frozen=True, slots=True)
class _Planned:
    """A task to create: its node, its parent, its rank, its label, its attachment, its duration.

    ``predecessors`` are the nodes of the tasks it follows, finish to start without lag.
    """

    node_id: UUID
    parent_id: UUID | None
    rank: int
    label: str
    work_package_id: UUID | None = None
    order_item_id: UUID | None = None
    days: int = 0
    predecessors: tuple[UUID, ...] = ()


def _end_label(label: str) -> str:
    """Give the label of the end milestone of an element, cut so that it fits a task's."""
    room = LABEL_LENGTH - len(END_OF.format(""))
    kept = label if len(label) <= room else label[: room - 1] + ELLIPSIS
    return END_OF.format(kept)


def _locked(session: Session, project_id: UUID) -> frozenset[UUID]:
    """Lock the work packages and items of the work breakdown read; give those that remain.

    They are locked ``FOR SHARE`` and read again: an element marked deleted before the lock is
    left out, one deleted for good is no longer there.
    """
    read = read_work_breakdown(session, project_id, WorkBreakdownFilters())
    named = [
        element
        for package in read.work_packages
        for element in (
            package.work_package_id,
            *(each.order_item_id for each in package.order_items),
        )
    ]
    held = work_breakdown_items(session, project_id, shared=named)
    return frozenset(each for each in named if each in held and not held[each].deleted)


def _plan(session: Session, project_id: UUID) -> list[_Planned]:
    """Give the tasks of the skeleton in the order of the plan, the work breakdown locked.

    A work package, then each of its items followed by its deliverables and its end milestone, then
    its own end milestone: the order of the plan, and that of the ranks under each parent.
    """
    kept = _locked(session, project_id)
    planned: list[_Planned] = []
    roots = 0
    for package in read_work_breakdown(session, project_id, WorkBreakdownFilters()).work_packages:
        if package.work_package_id not in kept:
            continue
        summary, roots = new_id(), roots + 1
        planned.append(
            _Planned(summary, None, roots, package.label, work_package_id=package.work_package_id)
        )
        ends: list[UUID] = []
        for item in (each for each in package.order_items if each.order_item_id in kept):
            under = new_id()
            planned.append(
                _Planned(
                    under, summary, len(ends) + 1, item.label, order_item_id=item.order_item_id
                )
            )
            leaves = [new_id() for _ in item.deliverables]
            planned += [
                _Planned(leaf, under, rank, each.label, days=1)
                for rank, (leaf, each) in enumerate(zip(leaves, item.deliverables, strict=True), 1)
            ]
            end = new_id()
            planned.append(
                _Planned(
                    end, under, len(leaves) + 1, _end_label(item.label), predecessors=tuple(leaves)
                )
            )
            ends.append(end)
        planned.append(
            _Planned(
                new_id(),
                summary,
                len(ends) + 1,
                _end_label(package.label),
                predecessors=tuple(ends),
            )
        )
    return planned


def _has_tasks(session: Session, place: Place) -> bool:
    return bool(
        session.scalar(
            select(exists().where(Node.structure_id == place.structure_id, Node.kind == TASK))
        )
    )


def _refuse() -> ConflictError:
    missing = {"missing_condition": MAIN_STRUCTURE_WITHOUT_TASKS}
    return ConflictError(STATE_FORBIDS_OPERATION, missing)


def _judge_empty_first(session: Session, place: Place) -> None:
    """Refuse a structure that has a task before the conditions of the write name theirs.

    ``main_structure_without_tasks`` comes first among the conditions of the command, ahead of
    the background task a write refuses on; a marked revision lacks ``revision_draft`` alone, which
    the write names. Judged again under the lock of the structure, where it holds.
    """
    try:
        revision_draft(session, place.revision_id)
    except ConflictError:
        return
    if _has_tasks(session, place):
        raise _refuse()


def generate_skeleton(session: Session, place: Place, writer: Writer) -> NodesWritten:
    """Engender the tasks of a structure from the work breakdown of its project, and give them.

    Refused if the structure is not the main one of its revision (404), if the revision is marked
    or the project terminal, if the structure has a task, or while a background task writes in
    the project (409, in the order of the command ``generate_skeleton``). The tasks are given in
    ``nodes``, in the order of the plan, none in ``ancestors`` nor ``rescheduled``.
    """
    facts_of(session, place, lock=False)
    _judge_empty_first(session, place)
    plan = _plan(session, place.project_id)
    ids = tuple(each.node_id for each in plan)
    with writing(session, place, writer, ("node_create", ids)) as write:
        if write.tree.tasks:
            raise _refuse()
        write.before(ids)
        _insert(write, plan)
        redated = write.redate(None)
        write.after(ids)
        return redated.written(ids)


def _insert(write: Write, plan: list[_Planned]) -> None:
    """Write the nodes, the facets and the links of the plan, in this order."""
    session, place, act = write.session, write.place, write.writer.act
    session.execute(
        insert(Node),
        [
            {
                "project_id": place.project_id,
                "id": each.node_id,
                "revision_id": place.revision_id,
                "structure_id": place.structure_id,
                "lineage_id": each.node_id,
                "kind": TASK,
                "parent_id": each.parent_id,
                "rank": each.rank,
                "origin_risk_id": None,
                "lock_version": 1,
                "created_at": act.at,
                "created_by": act.author,
                "updated_at": act.at,
                "updated_by": act.author,
            }
            for each in plan
        ],
    )
    # An automatic task is placed by the engine; it stands at the planning start meanwhile.
    start = WorkInstant(write.facts.planning_start_on)
    session.execute(
        insert(Task),
        [
            {
                "project_id": place.project_id,
                "node_id": each.node_id,
                "structure_id": place.structure_id,
                "kind": TASK,
                "label": each.label,
                "description": None,
                "scheduling_mode": AUTOMATIC,
                "duration_value": Decimal(each.days),
                "duration_unit": "d",
                "start_date": start.day,
                "start_hours": start.hours,
                "finish_date": start.day,
                "finish_hours": start.hours,
                "progress": NOT_STARTED,
                "work_package_id": each.work_package_id,
                "order_item_id": each.order_item_id,
                "total_float_days": None,
                "is_critical": False,
            }
            for each in plan
        ],
    )
    links = [
        {
            "project_id": place.project_id,
            "id": new_id(),
            "revision_id": place.revision_id,
            "structure_id": place.structure_id,
            "predecessor_id": predecessor,
            "successor_id": each.node_id,
            "link_type": "finish_to_start",
            "lag_value": Decimal(0),
            "lag_unit": "d",
            "in_conflict": False,
        }
        for each in plan
        for predecessor in each.predecessors
    ]
    if links:
        session.execute(insert(TaskLink), links)


def opening_with_tasks(session: Session, project_ids: Collection[UUID]) -> frozenset[UUID]:
    """Tell which of the projects would open a revision that carries a task.

    It is a copy of the last marked revision, without a task if the project has none: what
    ``ProjectCommand.generate_skeleton`` judges, a project without a current revision having no
    structure yet (WF-PRJ-0030, WF-REV-0010). One statement for the revisions, one for the tasks.
    """
    sources = last_marked_revisions(session, project_ids)
    if not sources:
        return frozenset()
    bearing = session.scalars(
        select(Node.revision_id)
        .where(Node.revision_id.in_(sources.values()), Node.kind == TASK)
        .distinct()
    )
    held = set(bearing)
    return frozenset(project for project, revision in sources.items() if revision in held)
