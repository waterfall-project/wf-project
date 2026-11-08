# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Whether the revision a project would open carries a task: what the planning tells the project.

A registry of this module (EP-06, "Les points d'extension"), filled by the planning at the import of
its interface. The project that has no current revision lists the generation of the planning
skeleton (``ProjectCommand.generate_skeleton``, WF-PRJ-0030, US-1460): it judges it on the revision
its opening would create, a copy of the last marked revision, whose tasks the planning alone knows.
"""

from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

# What each module tells of the revision a project would open, in their order.
_OPENING: Registry[Callable[[Session, Collection[UUID]], frozenset[UUID]]] = Registry(
    "projects.opening"
)


def register_opening_question(
    question: Callable[[Session, Collection[UUID]], frozenset[UUID]],
) -> Callable[[], None]:
    """Add a question on the revisions projects would open: which carry a task? Give its withdrawal.

    It answers for the projects it is given at once, so that a list of projects reads them in one
    statement and not one each.
    """
    return _OPENING.register(question)


def opening_with_tasks(session: Session, project_ids: Collection[UUID]) -> frozenset[UUID]:
    """Tell which of the projects would open a revision that carries a task, by any module."""
    found: set[UUID] = set()
    for question in _OPENING.entries():
        found |= question(session, project_ids)
    return frozenset(found)
