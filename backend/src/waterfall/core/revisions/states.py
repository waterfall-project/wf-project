# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the commands of a revision and of its structures read of it, private to the module.

Its status, whether a background task writes in its project (``no_background_task_running``,
US-0970), and whether it bears tasks and lines (``revision_has_tasks_and_lines``, EP-06, EP-07):
the facts ``commands`` judges, read once for a revision and all its structures.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.projects.interface import no_background_task_running
from waterfall.core.revisions.commands import RevisionState
from waterfall.core.revisions.interface.reference import revision_has_tasks_and_lines
from waterfall.core.revisions.tables import Revision
from waterfall.platform.errors import NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

NOT_FOUND = "NOT_FOUND"


def revision_state(session: Session, project_id: UUID, revision_id: UUID) -> RevisionState:
    """Read the state of a revision of a project as its commands judge it; or refuse (404)."""
    status = session.scalar(
        select(Revision.status).where(Revision.project_id == project_id, Revision.id == revision_id)
    )
    if status is None:
        raise NotFoundError(NOT_FOUND)
    return state_of(session, project_id, revision_id, status)


def state_of(session: Session, project_id: UUID, revision_id: UUID, status: str) -> RevisionState:
    """Give the state of a revision whose status is read already."""
    return RevisionState(
        marked=status == "marked",
        no_task_running=no_background_task_running(session, project_id),
        has_tasks_and_lines=revision_has_tasks_and_lines(session, revision_id),
    )
