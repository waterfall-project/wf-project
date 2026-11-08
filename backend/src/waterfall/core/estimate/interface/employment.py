# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the lines employ of the reference and of the project, as the modules below ask it.

``category_is_employed`` tells the cost settings the categories a line employs, which a change of
the kind of a nature or of a category refuses (``register_employment``, WF-REF-0030,
WF-REF-0040); ``subproject_is_cited`` and ``subproject_is_estimated`` tell the projects whether a
line names a subproject, which its deletion refuses (``register_estimate_facts``, which US-1490/L3
declares in ``core/projects``, WF-PRJ-0050).

Declared by US-1490/L1, unregistered: US-1490/L4 fills and registers them, and gives each its
arguments and its result; each raises ``NotImplementedError`` naming it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def category_is_employed(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those a line of an estimate employs."""
    msg = "category_is_employed is filled by US-1490/L4"
    raise NotImplementedError(msg)


def subproject_is_cited(session: Session, subproject_id: UUID) -> bool:
    """Tell whether a marked revision cites a subproject by its lines."""
    msg = "subproject_is_cited is filled by US-1490/L4"
    raise NotImplementedError(msg)


def subproject_is_estimated(session: Session, subproject_id: UUID) -> bool:
    """Tell whether a line of the current revision bears a subproject."""
    msg = "subproject_is_estimated is filled by US-1490/L4"
    raise NotImplementedError(msg)
