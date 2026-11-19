# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the commands of a revision and of its structures read of it, private to the module.

Its status, whether a background task writes in its project (``no_background_task_running``,
US-0970), whether it bears tasks and lines (``revision_has_tasks_and_lines``, EP-06, EP-07),
whether the reference of its project is still correctable (``reference_correctable``, US-0980/L2)
and, for a current revision, whether the proposal of its rates presents a category
(``rate_update_available``, US-1500); whether it holds a differential not merged, and whether it is
the last marked revision of a project without a current revision, which its merge would open
(``merge_structure``, US-2560/L2): the facts ``commands`` judges, read once for a revision and all
its structures.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from waterfall.core.cost_settings.interface import provision_category_active
from waterfall.core.projects.interface import no_background_task_running
from waterfall.core.revisions.commands import RevisionState
from waterfall.core.revisions.interface.rates import rate_update_available
from waterfall.core.revisions.interface.reference import (
    main_structure_has_task,
    reference_correctable,
    revision_has_tasks_and_lines,
)
from waterfall.core.revisions.interface.shared import AMENDMENT
from waterfall.core.revisions.tables import CostStructure, Revision
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
    standing = ProjectStanding(
        no_background_task_running(session, project_id), reference_correctable(session, project_id)
    )
    return state_of(session, (project_id, revision_id), status, standing)


@dataclass(frozen=True, slots=True)
class ProjectStanding:
    """What the commands of the revisions of a project read of it, once for all of them.

    Whether no background task writes in it, whether its reference is still correctable, and the
    revision whose merge would open the current one — its last marked, when it has none (#790).
    """

    no_task_running: bool
    correctable: bool
    opening: UUID | None = None


def state_of(
    session: Session, revision: tuple[UUID, UUID], status: str, standing: ProjectStanding
) -> RevisionState:
    """Give the state of a revision whose status, and its project's facts, are read.

    ``revision`` is its project and itself, ``standing`` what its project says of it.
    """
    project_id, revision_id = revision
    unmerged = session.scalar(
        select(
            exists().where(
                CostStructure.project_id == project_id,
                CostStructure.revision_id == revision_id,
                CostStructure.kind == AMENDMENT,
                CostStructure.is_merged.is_(False),
            )
        )
    )
    return RevisionState(
        marked=status == "marked",
        no_task_running=standing.no_task_running,
        has_tasks_and_lines=revision_has_tasks_and_lines(session, revision_id),
        reference_correctable=standing.correctable,
        has_main_task=main_structure_has_task(session, project_id, revision_id),
        rate_update_available=status == "draft"
        and rate_update_available(session, project_id, revision_id),
        provision_category_active=status != "draft" or provision_category_active(session),
        source=revision_id == standing.opening,
        unmerged_differential=bool(unmerged),
    )
