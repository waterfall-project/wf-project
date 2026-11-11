# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the commands of a revision and of its structures read of it, private to the module.

Its status, whether a background task writes in its project (``no_background_task_running``,
US-0970), whether it bears tasks and lines (``revision_has_tasks_and_lines``, EP-06, EP-07),
whether the reference of its project is still correctable (``reference_correctable``, US-0980/L2)
and, for a current revision, whether the proposal of its rates presents a category
(``rate_update_available``, US-1500): the facts ``commands`` judges, read once for a revision and
all its structures.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.projects.interface import no_background_task_running
from waterfall.core.revisions.commands import RevisionState
from waterfall.core.revisions.interface.rates import rate_update_available
from waterfall.core.revisions.interface.reference import (
    reference_correctable,
    revision_has_tasks,
    revision_has_tasks_and_lines,
)
from waterfall.core.revisions.tables import Revision
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def revision_state(session: Session, project_id: UUID, revision_id: UUID) -> RevisionState:
    """Read the state of a revision of a project as its commands judge it; or refuse (404)."""
    status = session.scalar(
        select(Revision.status).where(Revision.project_id == project_id, Revision.id == revision_id)
    )
    if status is None:
        raise NotFoundError(NOT_FOUND)
    idle = no_background_task_running(session, project_id)
    correctable = reference_correctable(session, project_id)
    return state_of(
        session, (project_id, revision_id), status, no_task_running=idle, correctable=correctable
    )


def state_of(
    session: Session,
    revision: tuple[UUID, UUID],
    status: str,
    *,
    no_task_running: bool,
    correctable: bool,
) -> RevisionState:
    """Give the state of a revision whose status, and its project's facts, are read.

    Whether a task writes in the project, and whether its reference is still correctable, are the
    project's, read once for all its revisions. ``revision`` is its project and itself.
    """
    project_id, revision_id = revision
    return RevisionState(
        marked=status == "marked",
        no_task_running=no_task_running,
        has_tasks_and_lines=revision_has_tasks_and_lines(session, revision_id),
        reference_correctable=correctable,
        has_tasks=revision_has_tasks(session, revision_id),
        rate_update_available=status == "draft"
        and rate_update_available(session, project_id, revision_id),
    )
