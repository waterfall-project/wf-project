# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The nodes of a structure: what the revisions ask of them, their copy and their tasks.

The planning registers, at the import of its interface, the copy of the nodes of a revision opened
from a marked one (``copy_nodes``, after the structures', whose copies it finds in
``RevisionCopy.identifiers``) and the question the designation of the reference asks
(``revision_has_tasks``, WF-CYC-0030). The reading and the writes of the tree — ``listNodes``,
``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies``, ``resolveRowNumber`` — are
US-1380/L2's, the deletion, the move and the attachment US-1380/L3's.

Declared by US-1380/L1: the copy copies nothing until US-1380/L2 creates nodes.
"""

from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionCopy

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
