# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles the lines of a project employ, which the proposal of its contributors reads (US-1540).

``roles_employed`` gives the projects the roles of resources the labour lines of a project employ,
whose accounts ``listContributorSuggestions`` proposes (``register_estimate_facts``, which
US-1490/L3 declares in ``core/projects``, WF-PRJ-0070).

The lines read are those of the current revision, or, the project having none, of its last marked
one: a project whose revision was just marked still proposes the team its estimate calls for.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import node_revisions
from waterfall.core.projects.interface import project_facts
from waterfall.core.revisions.interface import last_marked_revision

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def roles_employed(session: Session, project_id: UUID) -> frozenset[UUID]:
    """Give the roles of resources the labour lines of a project employ.

    Of its current revision, or of its last marked one without a current; none for a project that
    has neither.
    """
    revision = project_facts(session, project_id).current_revision_id
    if revision is None:
        revision = last_marked_revision(session, project_id)
    if revision is None:
        return frozenset()
    held = [
        (node, role)
        for node, role in session.execute(
            select(EstimateLine.node_id, EstimateLine.resource_role_id).where(
                EstimateLine.project_id == project_id, EstimateLine.resource_role_id.is_not(None)
            )
        )
        if role is not None
    ]
    revisions = node_revisions(session, project_id, [node for node, _ in held])
    return frozenset(role for node, role in held if revisions.get(node) == revision)
