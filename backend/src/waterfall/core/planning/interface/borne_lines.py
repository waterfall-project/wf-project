# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines another module writes under a task of a structure: the provision lines (EP-08).

A risk bears its provision line under a task of the main structure, the one it designates or the
first task of the first level (WF-RIS-0010, #786). The planning tells the risks the tasks they may
name, as it reads them — the first of the first level (``first_task``), a task of a structure
(``task_of``), the task of a lineage in it (``task_of_lineage``), the tasks bearing lines
(``bearing_of``) — and places the line they ask for (``create_borne_line``): framed as any write of
the tree — its revision judged, the structure locked and read under the lock, redated once written
—, but under a task whatever its state, a provision entering no state of its task (WF-PLA-0040), and
kept out of the history, whose entry the module that asks frames for all it writes (EP-08,
US-2590/L2). Its facet is written by the hooks of its kind, which the module that asks addresses
(``FacetCreation.entry``).

Filled by US-2570/L1.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, select

from waterfall.core.planning.interface.lines import judge_line_creation, write_line_node
from waterfall.core.planning.interface.nodes import NodeCreation
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import LINE, TASK
from waterfall.core.planning.writing import Writer, writing
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.writing import Place


@dataclass(frozen=True, slots=True)
class TaskNamed:
    """A task as another module names it: its node, its lineage, its label."""

    node_id: UUID
    lineage_id: UUID
    label: str


def _named(session: Session, project_id: UUID, *criteria: ColumnElement[bool]) -> list[TaskNamed]:
    """Read the tasks of a project the criteria retain, in the order of their rank."""
    rows = session.execute(
        select(Node.id, Node.lineage_id, Task.label)
        .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
        .where(Node.project_id == project_id, Node.kind == TASK, *criteria)
        .order_by(Node.rank, Node.id)
    )
    return [TaskNamed(node_id, lineage_id, label) for node_id, lineage_id, label in rows]


def first_task(session: Session, project_id: UUID, structure_id: UUID) -> TaskNamed | None:
    """Give the first task of the first level of a structure, none for a structure without one."""
    found = _named(session, project_id, Node.structure_id == structure_id, Node.parent_id.is_(None))
    return found[0] if found else None


def task_of(
    session: Session, project_id: UUID, structure_id: UUID, node_id: UUID
) -> TaskNamed | None:
    """Give a node of a structure that is a task; none for a line, another's, an unknown node."""
    found = _named(session, project_id, Node.structure_id == structure_id, Node.id == node_id)
    return found[0] if found else None


def task_of_lineage(
    session: Session, project_id: UUID, structure_id: UUID, lineage_id: UUID
) -> TaskNamed | None:
    """Give the task of a structure that is of a lineage (WF-DAT-0030), none if it holds none."""
    found = _named(
        session, project_id, Node.structure_id == structure_id, Node.lineage_id == lineage_id
    )
    return found[0] if found else None


def bearing_of(
    session: Session, project_id: UUID, line_ids: Collection[UUID]
) -> dict[UUID, TaskNamed]:
    """Give the task that bears each line named, by line; a line unknown is left out."""
    if not line_ids:
        return {}
    bearers = dict(
        session.execute(
            select(Node.id, Node.parent_id).where(
                Node.project_id == project_id, Node.id.in_(list(line_ids)), Node.kind == LINE
            )
        ).all()
    )
    tasks = {
        each.node_id: each for each in _named(session, project_id, Node.id.in_([*bearers.values()]))
    }
    return {
        line: tasks[parent]
        for line, parent in bearers.items()
        if parent is not None and parent in tasks
    }


def create_borne_line(
    session: Session, place: Place, task_id: UUID, entry: object, writer: Writer
) -> UUID:
    """Create a line under a task of a structure for another module, after its lines; give it.

    Framed as a write of the tree (``writing``): refused as one (404, 409), then if the task is
    none of the structure (422 ``UNKNOWN_TASK``), whatever its state; the facet of the line written
    by the hooks of its kind from ``entry``, which refuse what they do not accept. No entry of the
    history is kept: the module that asks keeps its own. The structure is redated, and the lines of
    the task priced again.
    """
    node_id = new_id()
    unrecorded = Writer(writer.act, None, writer.running)
    with writing(session, place, unrecorded, ("node_create", (node_id,))) as write:
        tree = write.tree
        creation = NodeCreation(task_id, None, after_given=False, kind=LINE, facet=entry)
        judged = judge_line_creation(tree, creation, node_id)
        write.before(judged.touched)
        write_line_node(write, judged, entry)
        write.redate((task_id, tree.tasks[task_id].label), None, (task_id,))
        write.after(judged.touched)
    return node_id
