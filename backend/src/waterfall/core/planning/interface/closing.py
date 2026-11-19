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
inside a current revision. The inscriptions follow the lineage, which the project keeps.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

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


def _delete_where(session: Session, project_id: UUID, scope: ColumnElement[bool]) -> None:
    """Delete the nodes of a project a scope retains, their facets first."""
    where = (Node.project_id == project_id, scope)
    for kind, hooks in facets().items():
        held = session.scalars(select(Node.id).where(*where, Node.kind == kind)).all()
        if held:
            hooks.delete(session, project_id, held)
    session.execute(delete(Node).where(*where).execution_options(synchronize_session=False))
