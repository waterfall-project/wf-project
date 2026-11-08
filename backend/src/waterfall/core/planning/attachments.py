# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The attachment of a task to the work breakdown, judged, private to the module (WF-PLA-0170).

A task bears a work package or an order item of its project, never both; an element is borne by
one task of a structure at a time; the main structure alone bears any (``TaskFacetUpdate``). When
the work package of an order item is borne, the task of the order item lies in the subtree of the
task of the work package: an attachment, a creation or a move that would take it out is refused
(``ORDER_ITEM_OUTSIDE_WORK_PACKAGE``), the tasks named by their node and their label.

The elements sent are read under a shared lock (``work_breakdown_items``): the work breakdown
written meanwhile neither deletes nor marks deleted the one a task is being attached to.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.projects.interface import work_breakdown_items
from waterfall.platform.errors import FieldError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import Tree
    from waterfall.core.projects.interface import WorkBreakdownItem

WORK_PACKAGE_ID = "work_package_id"
ORDER_ITEM_ID = "order_item_id"
# The fields of the attachment, each with the nature of the element it names.
FIELDS = ((WORK_PACKAGE_ID, "work_package"), (ORDER_ITEM_ID, "order_item"))
MAIN_STRUCTURE_ONLY = "WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY"
UNKNOWN_ITEM = "UNKNOWN_WORK_BREAKDOWN_ITEM"
EXCLUSIVE = "WORK_BREAKDOWN_ITEMS_EXCLUSIVE"
ALREADY_ATTACHED = "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED"
OUTSIDE = "ORDER_ITEM_OUTSIDE_WORK_PACKAGE"


@dataclass(frozen=True, slots=True)
class Bearer:
    """The task an attachment is judged for: its node, its label, its ancestors, what it bears.

    A task created has its node already, absent from the tree; ``ancestors`` are those it will
    have, its parent first; ``carried`` its work package and its order item.
    """

    node_id: UUID
    label: str
    ancestors: tuple[UUID, ...]
    carried: tuple[UUID | None, UUID | None] = (None, None)


@dataclass(frozen=True, slots=True)
class Attached:
    """What a write leaves a task bearing, and the refusals of what it sends."""

    work_package_id: UUID | None
    order_item_id: UUID | None
    faults: tuple[FieldError, ...] = ()


def _named(tree: Tree, node_id: UUID, label: str | None = None) -> dict[str, str]:
    """Name a task by its node and its label."""
    return {"node_id": str(node_id), "label": label or tree.tasks[node_id].label}


def carriers(tree: Tree, besides: UUID | None = None) -> dict[UUID, UUID]:
    """Give the task of the structure that bears each element, ``besides`` left out."""
    found: dict[UUID, UUID] = {}
    for node_id, task in tree.tasks.items():
        if node_id == besides:
            continue
        for item_id in (task.work_package_id, task.order_item_id):
            if item_id is not None:
                found[item_id] = node_id
    return found


def strays(
    items: Mapping[UUID, WorkBreakdownItem],
    borne: Mapping[UUID, UUID],
    is_under: Callable[[UUID, UUID], bool],
) -> list[tuple[UUID, list[UUID]]]:
    """Give each task of a work package with the tasks of its order items outside its subtree.

    ``borne`` gives the task that bears each element; ``is_under(task, summary)`` tells whether a
    task lies in the subtree of another.
    """
    found: dict[UUID, list[UUID]] = {}
    for item_id, task_id in borne.items():
        item = items.get(item_id)
        if item is None or item.work_package_id is None:
            continue
        package_task = borne.get(item.work_package_id)
        if package_task is not None and not is_under(task_id, package_task):
            found.setdefault(package_task, []).append(task_id)
    return list(found.items())


def stray_fault(
    tree: Tree, pointer: str, stray: tuple[UUID, list[UUID]], labels: Mapping[UUID, str]
) -> FieldError:
    """Refuse a task of an order item outside the subtree of the task of its work package."""
    package_task, item_tasks = stray
    ordered = sorted(item_tasks, key=lambda each: tree.row_number.get(each, 0))
    params = {
        "work_package_task": _named(tree, package_task, labels.get(package_task)),
        "order_item_tasks": [_named(tree, each, labels.get(each)) for each in ordered],
    }
    return FieldError(pointer, OUTSIDE, params)


def judged_attachment(
    session: Session,
    held: tuple[UUID, Tree, bool],
    bearer: Bearer,
    sent: Mapping[str, UUID | None],
    prefix: str,
) -> Attached:
    """Judge what a write sends of the attachment of a task; give what it leaves it bearing.

    ``held`` is the project, the tree read under the lock of its structure, and whether the
    structure is the main one; ``sent`` the fields sent, ``None`` removing; ``prefix`` where the
    pointers start. Every reason that applies is named at its field (``TaskFacetUpdate``); the
    subtree of the task of a work package is judged once the rest is accepted.
    """
    project_id, tree, is_main = held
    package, item = (
        sent.get(name, carried)
        for name, carried in zip((WORK_PACKAGE_ID, ORDER_ITEM_ID), bearer.carried, strict=True)
    )
    given = {name: value for name, value in sent.items() if value is not None}
    if not given:
        return Attached(package, item)
    if not is_main:
        refused = tuple(FieldError(f"{prefix}/{name}", MAIN_STRUCTURE_ONLY) for name in given)
        return Attached(package, item, refused)
    items = work_breakdown_items(session, project_id, shared=list(given.values()))
    borne = carriers(tree, bearer.node_id)
    faults: list[FieldError] = []
    result = {WORK_PACKAGE_ID: package, ORDER_ITEM_ID: item}
    for name, kind in FIELDS:
        if name not in given:
            continue
        pointer = f"{prefix}/{name}"
        other = ORDER_ITEM_ID if name == WORK_PACKAGE_ID else WORK_PACKAGE_ID
        if result[other] is not None:
            faults.append(FieldError(pointer, EXCLUSIVE))
        element = items.get(given[name])
        if element is None or element.kind != kind or element.deleted:
            faults.append(FieldError(pointer, UNKNOWN_ITEM))
            continue
        holder = borne.get(given[name])
        if holder is not None:
            named = {
                "conflicting_object_id": str(holder),
                "conflicting_object_label": tree.tasks[holder].label,
            }
            faults.append(FieldError(pointer, ALREADY_ATTACHED, named))
    if not faults:
        faults += _outside(tree, items, bearer, (given, result), prefix)
    return Attached(package, item, tuple(faults))


def _outside(
    tree: Tree,
    items: Mapping[UUID, WorkBreakdownItem],
    bearer: Bearer,
    sent: tuple[Mapping[str, UUID], Mapping[str, UUID | None]],
    prefix: str,
) -> list[FieldError]:
    """Refuse an attachment that takes the task of an order item out of that of its package."""
    given, result = sent
    borne = carriers(tree, bearer.node_id)
    for item_id in result.values():
        if item_id is not None:
            borne[item_id] = bearer.node_id

    def is_under(task_id: UUID, summary: UUID) -> bool:
        above = bearer.ancestors if task_id == bearer.node_id else tuple(tree.ancestors(task_id))
        return summary in above

    labels = {bearer.node_id: bearer.label}
    faults: list[FieldError] = []
    for stray in strays(items, borne, is_under):
        package_task, item_tasks = stray
        if WORK_PACKAGE_ID in given and package_task == bearer.node_id:
            faults.append(stray_fault(tree, f"{prefix}/{WORK_PACKAGE_ID}", stray, labels))
        elif ORDER_ITEM_ID in given and bearer.node_id in item_tasks:
            only = (package_task, [bearer.node_id])
            faults.append(stray_fault(tree, f"{prefix}/{ORDER_ITEM_ID}", only, labels))
    return faults
