# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of a structure as the planning reads it, private to the module (EP-06, "Modules").

The nodes of a structure, each with its facet task if it is one, ordered as the plan reads them:
under each parent, its lines first, then its subtasks, each kind by its rank (``Node.rank``);
the whole depth first. ``row_number``, ``level`` and ``position`` are computed here, on the whole
structure, whatever a reading returns of it (``Node.row_number``, WF-PLA-0080). A task is a
summary when it bears a subtask (WF-PLA-0040), a milestone when it is a leaf of nought duration
(WF-PLA-0050); its lines do not make it a summary.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import or_, select

from waterfall.core.planning.tables import Node, Task, TaskLink, TrackingEntry

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator

    from sqlalchemy.orm import Session

TASK = "task"
LINE = "estimate_line"


@dataclass(slots=True)
class Tree:
    """A structure read whole: its nodes, their facet task, and the order of the plan."""

    nodes: dict[UUID, Node]
    tasks: dict[UUID, Task]
    children: dict[UUID | None, list[UUID]] = field(default_factory=dict[UUID | None, list[UUID]])
    order: list[UUID] = field(default_factory=list[UUID])
    row_number: dict[UUID, int] = field(default_factory=dict[UUID, int])
    level: dict[UUID, int] = field(default_factory=dict[UUID, int])
    position: dict[UUID, int] = field(default_factory=dict[UUID, int])

    def __post_init__(self) -> None:
        """Order the nodes: under each parent, the lines then the subtasks, each by its rank."""
        for node in sorted(self.nodes.values(), key=lambda each: (each.kind == TASK, each.rank)):
            self.children.setdefault(node.parent_id, []).append(node.id)
        for place, node_id in enumerate(self.children.get(None, []), start=1):
            self.position[node_id] = place
        pending = [(node_id, 1) for node_id in reversed(self.children.get(None, []))]
        while pending:
            node_id, level = pending.pop()
            self.order.append(node_id)
            self.row_number[node_id] = len(self.order)
            self.level[node_id] = level
            below = self.children.get(node_id, [])
            for place, child in enumerate(below, start=1):
                self.position[child] = place
            pending.extend((child, level + 1) for child in reversed(below))

    def subtasks(self, node_id: UUID | None) -> list[UUID]:
        """Give the subtasks of a task — the tasks of the first level for ``None`` —, in order."""
        return [child for child in self.children.get(node_id, []) if child in self.tasks]

    def lines(self, node_id: UUID) -> list[UUID]:
        """Give the lines a task bears, in their order."""
        return [child for child in self.children.get(node_id, []) if child not in self.tasks]

    def is_summary(self, node_id: UUID) -> bool:
        """Tell whether a task bears a subtask: its dates, duration and state are derived."""
        return bool(self.subtasks(node_id))

    def is_milestone(self, node_id: UUID) -> bool:
        """Tell whether a task is a leaf of nought duration (WF-PLA-0050)."""
        task = self.tasks[node_id]
        return not self.is_summary(node_id) and task.duration_value == 0

    def ancestors(self, node_id: UUID) -> list[UUID]:
        """Give the ancestors of a node, its parent first."""
        found: list[UUID] = []
        parent = self.nodes[node_id].parent_id
        while parent is not None:
            found.append(parent)
            parent = self.nodes[parent].parent_id
        return found

    def subtree(self, node_id: UUID) -> Iterator[UUID]:
        """Give a node and every node under it, in the order of the plan."""
        pending = [node_id]
        while pending:
            current = pending.pop()
            yield current
            pending.extend(reversed(self.children.get(current, [])))

    def ordered(self, node_ids: Collection[UUID]) -> list[UUID]:
        """Give nodes of the tree in the order of the plan, each once."""
        return sorted(set(node_ids), key=self.row_number.__getitem__)


def read_tree(session: Session, project_id: UUID, structure_id: UUID) -> Tree:
    """Read the nodes of a structure and their facet task, as they are in the transaction."""
    nodes = session.scalars(
        select(Node)
        .where(Node.project_id == project_id, Node.structure_id == structure_id)
        .execution_options(populate_existing=True)
    ).all()
    tasks = session.scalars(
        select(Task)
        .where(Task.project_id == project_id, Task.structure_id == structure_id)
        .execution_options(populate_existing=True)
    ).all()
    return Tree({node.id: node for node in nodes}, {task.node_id: task for task in tasks})


def read_links(session: Session, project_id: UUID, structure_id: UUID) -> list[TaskLink]:
    """Read the links between the tasks of a structure."""
    return list(
        session.scalars(
            select(TaskLink)
            .where(TaskLink.project_id == project_id, TaskLink.structure_id == structure_id)
            .order_by(TaskLink.id)
            .execution_options(populate_existing=True)
        )
    )


def links_of(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, list[TaskLink]]:
    """Read the links of nodes, each kept under its predecessor and under its successor."""
    found: dict[UUID, list[TaskLink]] = {node_id: [] for node_id in node_ids}
    if not node_ids:
        return found
    rows = session.scalars(
        select(TaskLink)
        .where(
            TaskLink.project_id == project_id,
            or_(TaskLink.predecessor_id.in_(node_ids), TaskLink.successor_id.in_(node_ids)),
        )
        .order_by(TaskLink.id)
    )
    for link in rows:
        for end in {link.predecessor_id, link.successor_id} & found.keys():
            found[end].append(link)
    return found


def tracking_of(
    session: Session, project_id: UUID, lineage_ids: Collection[UUID]
) -> dict[UUID, list[TrackingEntry]]:
    """Read the inscriptions of lineages, by lineage, the time/time tracking first."""
    found: dict[UUID, list[TrackingEntry]] = {lineage: [] for lineage in lineage_ids}
    if not lineage_ids:
        return found
    rows = session.scalars(
        select(TrackingEntry)
        .where(TrackingEntry.project_id == project_id, TrackingEntry.lineage_id.in_(lineage_ids))
        .order_by(TrackingEntry.kind, TrackingEntry.created_at, TrackingEntry.id)
    )
    for entry in rows:
        found[entry.lineage_id].append(entry)
    return found
