# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles the lines of a project employ, which the proposal of its contributors reads (US-1540).

``roles_employed`` gives the projects the roles of resources the labour lines of a project employ,
whose accounts ``listContributorSuggestions`` proposes (``register_estimate_facts``, which
US-1490/L3 declares in ``core/projects``).

Declared by US-1490/L1, unregistered; it raises ``NotImplementedError`` naming the story that
fills it, which registers it and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def roles_employed(session: Session, project_id: UUID) -> frozenset[UUID]:
    """Give the roles of resources the labour lines of a project employ."""
    msg = "roles_employed is filled by US-1540"
    raise NotImplementedError(msg)
