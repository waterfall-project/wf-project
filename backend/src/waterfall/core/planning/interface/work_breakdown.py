# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning tells the work breakdown of the tasks attached to it (WF-PLA-0170).

Registered at the import of the interface in the registry of the projects
(``register_attachments``): whether a task of a marked revision bears a work package or an order
item, the lock of the structures of the current revision, taken before the elements it removes,
and the withdrawal of an element from the tasks of that revision, which ``set_work_breakdown``
asks of them.

The withdrawal is a write of the planning: it writes the tasks of a structure under its lock and
advances its counter, on which the front leans every write (US-2250/L3, #3600). Every structure of
the current revision is locked before the elements, in the order of their identifier
(``hold_work_breakdown_items``), as a write of the tree locks its structure before it shares the
element it attaches a task to: not only those whose tasks bear an element, which a read before the
lock would give, and which a task attached between that read and the lock would leave short — the
withdrawal would then wait for a structure another write holds while it waits for the element, a
deadlock, and write that structure's tasks without its counter. The structures of a revision are
fixed under the lock of the project, which ``set_work_breakdown`` holds, and which the opening and
the marking of a revision take: the set locked is the set written. The withdrawal reads the
structures it writes under that lock, and advances their counters alone.

Declared by US-1380/L1, filled by US-1380/L3: a task of a revision other than the current one of
its project is one of a marked revision — an abandoned revision leaves no task —; the tasks of the
current revision lose the element, those of the marked ones keep it, which their revision freezes.
"""

from typing import TYPE_CHECKING

from sqlalchemy import or_, select, update

from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import LINE
from waterfall.core.revisions.interface import (
    current_revision,
    revision_structures,
    structure_counted,
    structure_facts,
)

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def work_package_lines(
    session: Session, project_id: UUID, structure_id: UUID
) -> dict[UUID, frozenset[UUID]]:
    """Give, for each work package a task of a structure bears, the lines of that task's subtree.

    The task, summary or leaf, and every task under it: a work package whose task bears no line
    maps to none, a work package no task bears is left out (WF-PLA-0170, WF-DEV-0060).
    """
    nodes = session.execute(
        select(Node.id, Node.parent_id, Node.kind).where(
            Node.project_id == project_id, Node.structure_id == structure_id
        )
    ).all()
    children: dict[UUID, list[tuple[UUID, str]]] = {}
    for node_id, parent_id, kind in nodes:
        if parent_id is not None:
            children.setdefault(parent_id, []).append((node_id, kind))
    bearers = session.execute(
        select(Task.work_package_id, Task.node_id).where(
            Task.project_id == project_id,
            Task.structure_id == structure_id,
            Task.work_package_id.is_not(None),
        )
    ).all()
    found: dict[UUID, frozenset[UUID]] = {}
    for package_id, task_id in bearers:
        if package_id is None:
            continue
        lines: set[UUID] = set()
        pending = [task_id]
        while pending:
            for node_id, kind in children.get(pending.pop(), ()):
                if kind == LINE:
                    lines.add(node_id)
                else:
                    pending.append(node_id)
        found[package_id] = frozenset(lines)
    return found


def work_breakdown_item_cited(session: Session, item_id: UUID) -> bool:
    """Tell whether a task of a marked revision bears an element of the work breakdown."""
    bearing = session.execute(
        select(Node.project_id, Node.revision_id)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(or_(Task.work_package_id == item_id, Task.order_item_id == item_id))
        .distinct()
    ).all()
    return any(
        revision_id != current_revision(session, project_id) for project_id, revision_id in bearing
    )


def _bearing(session: Session, project_id: UUID, current: UUID, item_id: UUID) -> list[UUID]:
    """Give the structures whose tasks of the current revision bear an element, in their order.

    To be read under the lock of every structure of the revision (``_held``): no task can come to
    bear the element after.
    """
    found = session.scalars(
        select(Node.structure_id)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(
            Node.project_id == project_id,
            Node.revision_id == current,
            or_(Task.work_package_id == item_id, Task.order_item_id == item_id),
        )
        .distinct()
    )
    return sorted(found)


def _held(session: Session, project_id: UUID, current: UUID) -> None:
    """Lock every structure of the current revision, ``FOR UPDATE``, in the order of their ids.

    As every write that locks several does (``reprice_revision``); a structure held already costs
    nothing.
    """
    for structure_id in revision_structures(session, project_id, current):
        structure_facts(session, project_id, structure_id, lock=True)


def hold_work_breakdown_items(
    session: Session, project_id: UUID, item_ids: Collection[UUID]
) -> None:
    """Lock every structure of the current revision before the elements removed, when there are.

    Asked by ``set_work_breakdown`` under the lock of the project, before it writes or locks an
    element it removes: every structure, not those whose tasks bear one, which a read before the
    lock would give and a task attached meanwhile would leave short (#3600).
    """
    if not item_ids:
        return
    current = current_revision(session, project_id)
    if current is not None:
        _held(session, project_id, current)


def detach_work_breakdown_item(session: Session, project_id: UUID, item_id: UUID) -> None:
    """Withdraw an element of the work breakdown from the tasks of the current revision.

    The node of each task it writes counts the write, its counter advanced (``Node.lock_version``)
    in a statement of its own, before the tasks are written: a write of the tree that would read
    such a task again rests on that counter (``reshaped``, US-2250/L2, #3562), and an entry made
    on the task as it was is refused at the counter it read (412). Every structure of the revision
    is locked first, held already when ``hold_work_breakdown_items`` took them; those whose tasks
    it writes, read under that lock, have their counter advanced once their tasks are written
    (``structure_counted``, #3600): a write of the tree reads none of them halfway, and the front
    knows its reading stale.
    """
    current = current_revision(session, project_id)
    if current is None:
        return
    _held(session, project_id, current)
    structures = _bearing(session, project_id, current, item_id)
    if not structures:
        return
    of_current = select(Node.id).where(Node.project_id == project_id, Node.revision_id == current)
    bearing = select(Task.node_id).where(
        Task.project_id == project_id,
        or_(Task.work_package_id == item_id, Task.order_item_id == item_id),
        Task.node_id.in_(of_current),
    )
    session.execute(
        update(Node)
        .where(Node.project_id == project_id, Node.id.in_(bearing))
        .values(lock_version=Node.lock_version + 1)
        .execution_options(synchronize_session=False)
    )
    for column in (Task.work_package_id, Task.order_item_id):
        session.execute(
            update(Task)
            .where(Task.project_id == project_id, column == item_id, Task.node_id.in_(of_current))
            .values({column.key: None})
            .execution_options(synchronize_session=False)
        )
    for structure_id in structures:
        structure_counted(session, project_id, structure_id)
