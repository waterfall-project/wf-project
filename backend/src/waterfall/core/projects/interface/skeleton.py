# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Whether the main structure of the revision a project would open carries a task.

A registry of this module (EP-06, "Les points d'extension"), filled by the planning at the import of
its interface. The project that has no current revision lists the generation of the planning
skeleton (``ProjectCommand.generate_skeleton``, WF-PRJ-0030, US-1460) and the declaration of a risk
(WF-RIS-0010): it judges them on the revision its opening would create, a copy of the last marked
revision, whose tasks the planning alone knows. Both judge its main structure alone, whichever
tasks a differential bears (#2541).
"""

from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

# What each module tells of the main structure of the revision a project would open.
_OPENING_MAIN: Registry[Callable[[Session, Collection[UUID]], frozenset[UUID]]] = Registry(
    "projects.opening_main"
)


def register_opening_main_question(
    question: Callable[[Session, Collection[UUID]], frozenset[UUID]],
) -> Callable[[], None]:
    """Add a question on the revisions projects would open: which main structure carries a task.

    It answers for the projects it is given at once, so that a list of projects reads them in one
    statement and not one each. Give its withdrawal.
    """
    return _OPENING_MAIN.register(question)


def opening_main_with_tasks(session: Session, project_ids: Collection[UUID]) -> frozenset[UUID]:
    """Tell which of the projects would open a revision whose main structure carries a task.

    The questions registered are combined as ``main_structure_has_task`` combines its own, of a
    revision: by AND, a project every question retains, none while no question is registered
    (#4004). The planning is the only one today.
    """
    questions = _OPENING_MAIN.entries()
    if not questions:
        return frozenset()
    found = frozenset(project_ids)
    for question in questions:
        found &= question(session, project_ids)
    return found
