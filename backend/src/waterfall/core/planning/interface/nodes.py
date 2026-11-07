# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The nodes of a structure: the tree read and written, what the revisions ask of it, its copy.

The planning registers, at the import of its interface, the copy of the nodes of a revision opened
from a marked one (``copy_nodes``, after the structures', whose copies it finds in
``RevisionCopy.identifiers``) and the question the designation of the reference asks of its tasks
(``revision_has_tasks``, WF-CYC-0030). The reading and the writes of the tree — ``listNodes``,
``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies``, ``resolveRowNumber`` — are
US-1380/L2's, the deletion and the move (``deleteNode``, ``moveNodes``) US-1380/L3's; each write
locks its structure, replays the engine (``reschedule``) and keeps its entry of the history
(``history.recording``). ``load_task`` writes a task of the witness at the identifiers and the
instant it imposes (US-1480/L2).

Declared by US-1380/L1: the copy copies nothing until US-1380/L2 creates nodes; the others raise
``NotImplementedError`` naming the story that fills them, which gives each its arguments and its
result.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionCopy
    from waterfall.platform.audit import Act

TASK = "task"


def revision_has_tasks(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears a task: the planning's part of a designation (WF-CYC-0030)."""
    return bool(
        session.scalar(select(exists().where(Node.revision_id == revision_id, Node.kind == TASK)))
    )


def copy_nodes(copy: RevisionCopy) -> None:
    """Copy the nodes of the source, their facet task and their links (WF-DAT-0010).

    Nothing until US-1380/L2, which creates the nodes and fills this copy.
    """
    del copy


def list_nodes(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Read the nodes of a structure, depth first, numbered and filtered (``listNodes``)."""
    msg = "list_nodes is filled by US-1380/L2"
    raise NotImplementedError(msg)


def create_node(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Create a task of a structure, and give the nodes written (``createNode``)."""
    msg = "create_node is filled by US-1380/L2"
    raise NotImplementedError(msg)


def update_task_facet(session: Session, project_id: UUID, node_id: UUID, act: Act) -> None:
    """Write what is sent of the facet of a task, at the counter read (``updateTaskFacet``)."""
    msg = "update_task_facet is filled by US-1380/L2"
    raise NotImplementedError(msg)


def computed_value_dependencies(session: Session, project_id: UUID, node_id: UUID) -> None:
    """Name what a computed value of a node depends on (``getComputedValueDependencies``)."""
    msg = "computed_value_dependencies is filled by US-1380/L2"
    raise NotImplementedError(msg)


def resolve_row_number(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Give the node of a number of row of a structure (``resolveRowNumber``)."""
    msg = "resolve_row_number is filled by US-1380/L2"
    raise NotImplementedError(msg)


def delete_node(session: Session, project_id: UUID, node_id: UUID, act: Act) -> None:
    """Delete a node and its subtree, and give the nodes written (``deleteNode``)."""
    msg = "delete_node is filled by US-1380/L3"
    raise NotImplementedError(msg)


def move_nodes(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Move a selection of nodes under a parent, and give the nodes written (``moveNodes``)."""
    msg = "move_nodes is filled by US-1380/L3"
    raise NotImplementedError(msg)


def load_task(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Write a task of the witness, at the identifiers and the instant it imposes."""
    msg = "load_task is filled by US-1480/L2"
    raise NotImplementedError(msg)
