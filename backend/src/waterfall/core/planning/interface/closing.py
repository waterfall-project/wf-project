# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning does before a revision is abandoned: its nodes deleted.

Registered at the import of the interface in the closing of the revisions (``register_closing``),
under the stage ``content``, after the history's, and before the structures of EP-04 are deleted
(EP-06, "Les points d'extension"): the nodes of an abandoned revision go with their facets, their
links and the facets of the later modules (``register_facet``), so that its abandonment leaves no
row (WF-DAT-0010). A marking deletes nothing.

Declared by US-1380/L1; filled by US-1380/L2: the facets of the later kinds are deleted by their
hooks first, then the nodes, whose facet task, links and children follow by the keys that cascade
inside a current revision. The inscriptions of the lineages no node holds any more go too
(US-3340): one a marked revision still holds keeps its own.

The nodes of a structure that goes with its owner — the own estimate of a risk deleted
(``delete_structure_nodes``, US-2590/L1) — are kept whole by its owner first, for the undoing of
the deletion, which creates the structure again and writes its nodes back under their identifiers
(``structure_nodes``, ``restore_structure_nodes``; US-2590/L2).
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.history.interface import Restoring
from waterfall.core.planning.inscriptions import delete_orphan_inscriptions
from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.restoring import bring_back
from waterfall.core.planning.snapshotting import taken
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import read_tree
from waterfall.core.planning.writing import facts_of

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import Snapshot
    from waterfall.core.planning.writing import Place, Writer
    from waterfall.core.revisions.interface import RevisionClosing


def delete_nodes(closing: RevisionClosing) -> None:
    """Delete the nodes of a revision about to be abandoned, their facets and their links."""
    if closing.kind != "abandoned":
        return
    session, project_id = closing.session, closing.project_id
    _delete_where(session, project_id, Node.revision_id == closing.revision_id)


def delete_structure_nodes(session: Session, project_id: UUID, structure_id: UUID) -> None:
    """Delete the nodes of a structure about to go, their facets and their links (US-2590/L1).

    The own estimate of a risk deleted with it (``deleteRisk``, the abandonment of the revision
    that declared it): the facets of the later kinds first, by their hooks, then the nodes, whose
    facet task, links and children follow by the keys that cascade. The structure is locked by the
    caller, which deletes it after.
    """
    _delete_where(session, project_id, Node.structure_id == structure_id)


def structure_node_ids(session: Session, project_id: UUID, structure_id: UUID) -> list[UUID]:
    """Give the identifiers of the nodes of a structure about to go (#4154).

    What the history needs to forget the entries that name them (``forget_structure``), before
    ``delete_structure_nodes`` removes them.
    """
    return list(
        session.scalars(
            select(Node.id).where(Node.project_id == project_id, Node.structure_id == structure_id)
        )
    )


def structure_nodes(session: Session, project_id: UUID, structure_id: UUID) -> Snapshot:
    """Give every node of a structure as the history keeps one, in the order of its plan.

    Their rows, their facets, their links and their inscriptions (``snapshot``): what the undoing
    of the deletion of the structure writes back.
    """
    tree = read_tree(session, project_id, structure_id)
    return taken(session, project_id, tree.ordered(tree.nodes))


def restore_structure_nodes(
    session: Session, place: Place, states: Snapshot, writer: Writer
) -> Snapshot:
    """Write back the nodes of a structure created again empty, as ``structure_nodes`` kept them.

    Under the lock of the structure, taken here: each node created again under its identifier, at
    the counter that follows the one kept, with its facet, its links and its inscriptions, then the
    structure redated, as the undoing of a deletion of nodes does (``restoring``). Gives the nodes
    as they are left.
    """
    if not states:
        return ()
    facts = facts_of(session, place, lock=True)
    ids = tuple(state.object_id for state in states)
    restoring = Restoring("node_create", ids, ((), states), 0, undoing=False)
    bring_back(session, place, facts, restoring, writer)
    return restoring.present()


def _delete_where(session: Session, project_id: UUID, scope: ColumnElement[bool]) -> None:
    """Delete the nodes of a project a scope retains, their facets first."""
    where = (Node.project_id == project_id, scope)
    lineages = set(
        session.scalars(select(Node.lineage_id).join(Task, Task.node_id == Node.id).where(*where))
    )
    for kind, hooks in facets().items():
        held = session.scalars(select(Node.id).where(*where, Node.kind == kind)).all()
        if held:
            hooks.delete(session, project_id, held)
    session.execute(delete(Node).where(*where).execution_options(synchronize_session=False))
    delete_orphan_inscriptions(session, project_id, lineages)
