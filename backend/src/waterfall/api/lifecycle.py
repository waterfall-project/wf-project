# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cycle of life of a project (§3.3.2).

``getProjectNextState``, ``exitProject`` and ``listProjectStateTransitions`` (US-0980/L1);
``designateReferenceRevision`` (US-0980/L2).

Each names the project and is judged by ``RequiresProject``: the permission of the function of the
life cycle and the quality of the caller on the project (WF-ADM-0110, WF-PRJ-0060). The next state
and the transitions are read by whoever consults the cycle; an exit is declared by a project
manager holding the permission to declare one, an irreversible action of its own (WF-ADM-0100).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.models import NextState, Project, ProjectExit, StateTransition
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import described, viewer_of
from waterfall.core.projects.interface import (
    ExitRequest,
    exit_project,
    list_state_transitions,
    no_background_task_running,
    project_facts,
    read_next_state,
    read_project,
)
from waterfall.core.revisions.interface import abandon_revision, read_revision
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import BadRequestError

router = APIRouter(tags=["projects"])

CONSULT = "lifecycle.read"
EXIT = "project_exit"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
ABANDON = "abandon"


@router.get(
    "/projects/{project_id}/next-state",
    operation_id="getProjectNextState",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model_exclude_unset=True,
)
def get_next_state(project_id: UUID, session: Transaction) -> NextState:
    """Give the next state of a project, its trigger and what it still lacks (WF-CYC-0050)."""
    read = read_next_state(session, project_id)
    return NextState.model_validate(
        {
            "current_state": read.state,
            "next_state": read.next_state,
            "trigger": read.trigger,
            "missing_conditions": list(read.missing_conditions),
        }
    )


@router.get(
    "/projects/{project_id}/state-transitions",
    operation_id="listProjectStateTransitions",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_state_transitions(project_id: UUID, session: Transaction) -> list[dict[str, Any]]:
    """Give the transitions of a project from its creation, dated, with their authors (WF-CYC-0130).

    The author of a transition is the account that realised its fact; the platform when none did.
    """
    views = list_state_transitions(session, project_id)
    authors = read_authors(session, {view.author for view in views if view.author is not None})
    return [
        StateTransition.model_validate(
            {
                "from_state": view.from_state,
                "to_state": view.to_state,
                "occurred_at": view.occurred_at,
                "actor": actor_ref(None if view.author is None else authors.get(view.author)),
                "reason": view.reason,
            }
        ).model_dump(mode="json")
        for view in views
    ]


@router.post(
    "/projects/{project_id}/exit",
    operation_id="exitProject",
    dependencies=[Depends(RequiresProject(CONSULT, EXIT, manager=True))],
    response_model_exclude_unset=True,
)
def post_exit(
    project_id: UUID, body: ProjectExit, actor: Acting, account: Caller, session: Transaction
) -> Project:
    """Take a project out of its cycle, confirmed, at the counter read; only its managers may.

    An exit not confirmed is refused first (400). A current revision abandoned with the exit is
    abandoned first, as the abandonment of a revision locks the revision then the project and no
    route locks them the other way round; the exit then judges under the lock of the project, and
    the whole is undone if it refuses. The marking of the current revision at the exit is the
    worker's, which US-0980/L2 and US-0970 bring (202, #2204): until then the exit refuses it as a
    project that bears a current revision (409 ``no_current_revision``).
    """
    if not body.confirmed:
        raise BadRequestError(CONFIRMATION_REQUIRED)
    act = Act(account.user_id, utc_now())
    viewer = viewer_of(actor)
    fate = None if body.current_revision is None else body.current_revision.root.action
    revision_id = project_facts(session, project_id).current_revision_id
    moved = 0
    if fate == ABANDON and revision_id is not None:
        read = read_revision(session, project_id, revision_id, viewer)
        abandon_revision(session, project_id, revision_id, read.lock_version, act)
        moved = 1
    request = ExitRequest(
        to_state=body.to_state.value,
        reason=body.reason or None,
        lock_version=body.lock_version.root,
        fate=fate,
        moved=moved,
        no_task_running=no_background_task_running(session, project_id),
    )
    exit_project(session, project_id, request, act)
    return described(session, [read_project(session, project_id, viewer)])[0]
