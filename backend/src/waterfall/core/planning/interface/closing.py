# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning does before a revision is abandoned: its nodes deleted.

Registered at the import of the interface in the closing of the revisions (``register_closing``),
under the stage ``content``, after the history's, and before the structures of EP-04 are deleted
(EP-06, "Les points d'extension"): the nodes of an abandoned revision go with their facets, their
links and the facets of the later modules (``register_facet``), so that its abandonment leaves no
row (WF-DAT-0010). A marking deletes nothing.

Declared by US-1380/L1, without effect until US-1380/L2 creates nodes: the cascade of the keys
deletes them with their structure meanwhile.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from waterfall.core.revisions.interface import RevisionClosing


def delete_nodes(closing: RevisionClosing) -> None:
    """Delete the nodes of a revision about to be abandoned, their facets and their links.

    Nothing before US-1380/L2.
    """
    del closing
