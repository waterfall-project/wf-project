# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cycle of life of a project (§3.3.2).

``getProjectNextState``, ``exitProject`` and ``listProjectStateTransitions`` (US-0980/L1);
``designateReferenceRevision`` (US-0980/L2), which ``exitProject`` completes by marking the current
revision (202, ``revision_mark``, #2204).

Each names the project and is judged by ``RequiresProject``: the permission of the function of the
life cycle and the quality of the caller on the project (WF-ADM-0110, WF-PRJ-0060). The next state
and the transitions are read by whoever consults the cycle; an exit is declared by a project
manager holding the permission to declare one, an irreversible action of its own (WF-ADM-0100); the
reference is designated by a project manager holding the permission of that action.
"""

from dataclasses import replace
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import (
    CurrentRevisionMark,
    NextState,
    Project,
    ProjectExit,
    ReferenceDesignation,
    StateTransition,
)
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import described, viewer_of
from waterfall.api.tasks import task_ref
from waterfall.core.access_roles.interface import require
from waterfall.core.projects.interface import (
    ExitRequest,
    exit_project,
    judge_exit_unlocked,
    list_state_transitions,
    no_background_task_running,
    project_facts,
    read_next_state,
    read_project,
    stored_lock_version,
)
from waterfall.core.revisions.interface import (
    MarkingRequest,
    abandon_revision,
    designate_reference,
    read_revision,
    submit_marking,
)
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    BadRequestError,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
)
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import BackgroundTask

router = APIRouter(tags=["projects"])

CONSULT = "lifecycle.read"
EXIT = "project_exit"
DESIGNATE = "reference_designate"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
ABANDON = "abandon"
MARK = "mark"
REVISION_ABANDON = "revision_abandon"
REVISION_MARK = "revision_mark"
ALREADY_EXISTS = "ALREADY_EXISTS"
VERSION_NAME = "/current_revision/version_name"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"


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
        ).model_dump(mode="json", exclude_unset=True)
        for view in views
    ]


def _stale_if_moved(session: Session, project_id: UUID, read: int) -> None:
    """Tell the counter moved (412) if the project is not at the counter read; else do nothing.

    A revision found no more because another exit disposed of it first moved the counter of the
    project; one that is unknown for another reason (out of the reader's scope) did not, and its
    404 stands.
    """
    stored = stored_lock_version(session, project_id)
    if stored != read:
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": stored})


def _marking_exit(
    session: Session, queue: TaskQueue, request: MarkingRequest, act: Act
) -> JSONResponse:
    """Ask the marking of the current revision for an exit, and say where the task stands (202).

    The name of version taken is told at the place of the body that holds it.
    """
    try:
        task_id = submit_marking(session, queue, request, act)
    except ConflictError as error:
        if error.code != ALREADY_EXISTS:
            raise
        params = error.fields[0].params
        raise ConflictError(
            ALREADY_EXISTS, fields=(FieldError(VERSION_NAME, ALREADY_EXISTS, params),)
        ) from None
    task = task_ref(session.get_one(BackgroundTask, task_id))
    return JSONResponse(task.model_dump(mode="json", exclude_unset=True), status_code=202)


@router.post(
    "/projects/{project_id}/exit",
    operation_id="exitProject",
    dependencies=[Depends(RequiresProject(CONSULT, EXIT, manager=True))],
    response_model=None,
    responses={202: {"description": "The exit that marks, queued"}},
)
def post_exit(
    project_id: UUID, body: ProjectExit, actor: Acting, session: Transaction, services: ServicesOf
) -> dict[str, Any] | JSONResponse:
    """Take a project out of its cycle, confirmed, at the counter read; only its managers may.

    An exit that disposes of the current revision asks besides for the permission to abandon or to
    mark one (403). An exit not confirmed is refused (400), then judged on the facts read without
    a lock, so that the first refusal of the contract is told. A current revision abandoned with
    the exit is abandoned first, as the abandonment of a revision locks the revision then the
    project and no route locks them the other way round; the exit then judges under the lock of
    the project, and the whole is undone if it refuses. One marked with the exit is the worker's
    (202 and the task ``revision_mark``, which exits the project once it has marked it, #2204):
    nothing is written here but the task.
    """
    fate = None if body.current_revision is None else body.current_revision.root
    action = None if fate is None else fate.action
    if action == ABANDON:
        # The abandonment is an abandonment of a revision (WF-ADM-0100): the permission to abandon
        # one is asked besides the permission to exit, at the evaluation of ``abandonRevision``.
        require(actor, REVISION_ABANDON)
    if action == MARK:
        require(actor, REVISION_MARK)
    if not body.confirmed:
        raise BadRequestError(CONFIRMATION_REQUIRED)
    act = Act(actor.user_id, utc_now())
    viewer = viewer_of(actor)
    read = body.lock_version.root
    revision_id = project_facts(session, project_id).current_revision_id
    request = ExitRequest(
        to_state=body.to_state.value,
        reason=body.reason or None,
        lock_version=read,
        fate=action,
        no_task_running=no_background_task_running(session, project_id),
    )
    # Judged before the revision is disposed of, on what is read without a lock: the first refusal
    # of the contract is told, not the refusal of the revision. The judgment under the lock rules.
    judge_exit_unlocked(session, project_id, request)
    if isinstance(fate, CurrentRevisionMark) and revision_id is not None:
        try:
            revision = read_revision(session, project_id, revision_id, viewer)
            marking = MarkingRequest(
                project_id,
                revision_id,
                fate.version_name,
                fate.description,
                revision.lock_version,
                exit_state=request.to_state,
                exit_reason=request.reason,
                exit_lock_version=read,
            )
            return _marking_exit(session, services.queue, marking, act)
        except NotFoundError:
            _stale_if_moved(session, project_id, read)
            raise
    if action == ABANDON and revision_id is not None:
        try:
            revision = read_revision(session, project_id, revision_id, viewer)
            abandon_revision(session, project_id, revision_id, revision.lock_version, act)
        except NotFoundError:
            # Another exit abandoned the revision first (the revision is locked before the
            # project, so we waited for it): the counter this one read is stale (412).
            _stale_if_moved(session, project_id, read)
            raise
        request = replace(
            request, moved=1, no_task_running=no_background_task_running(session, project_id)
        )
    exit_project(session, project_id, request, act)
    project = described(session, [read_project(session, project_id, viewer)])[0]
    return project.model_dump(mode="json", exclude_unset=True)


@router.put(
    "/projects/{project_id}/reference-revision",
    operation_id="designateReferenceRevision",
    dependencies=[Depends(RequiresProject(CONSULT, DESIGNATE, manager=True))],
    response_model_exclude_unset=True,
)
def put_reference_revision(
    project_id: UUID,
    body: ReferenceDesignation,
    actor: Acting,
    account: Caller,
    session: Transaction,
) -> Project:
    """Designate the reference revision of a project, confirmed, at the counter read.

    Only a manager of the project holding the permission of that action may. An unconfirmed
    designation is refused (400) before anything is read; the revisions judge the rest under the
    lock of the project, and the response is built before the transaction is committed.
    """
    if not body.confirmed:
        raise BadRequestError(CONFIRMATION_REQUIRED)
    act = Act(account.user_id, utc_now())
    designate_reference(session, project_id, body.revision_id.root, body.lock_version.root, act)
    return described(session, [read_project(session, project_id, viewer_of(actor))])[0]
