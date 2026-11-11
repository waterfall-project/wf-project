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
    from waterfall.core.revisions.interface import RevisionClosing


def delete_nodes(closing: RevisionClosing) -> None:
    """Delete the nodes of a revision about to be abandoned, their facets and their links."""
    if closing.kind != "abandoned":
        return
    session, project_id = closing.session, closing.project_id
    of_revision = (Node.project_id == project_id, Node.revision_id == closing.revision_id)
    for kind, hooks in facets().items():
        held = session.scalars(select(Node.id).where(*of_revision, Node.kind == kind)).all()
        if held:
            hooks.delete(session, project_id, held)
    session.execute(delete(Node).where(*of_revision).execution_options(synchronize_session=False))
