# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The marking of a revision, in the background task ``revision_mark`` (WF-REV-0020, WF-REV-0090).

``markRevision`` asks for it: under the lock of the revision, read under it, refused if unknown
(404), at another counter (412), once marked (409 ``revision_draft``), while a background task
writes in its project (409 ``no_background_task_running``), or under a name of version a marked
revision of the project bears (409 ``ALREADY_EXISTS`` on ``/version_name``); otherwise its task is
submitted in the transaction of the request (``submit_marking``), and while it is queued or runs,
the commands that would write in the revision name ``no_background_task_running``.

The worker marks (``run_marking``), in the one transaction of the task, under the lock of the
revision taken ``FOR UPDATE`` (#2104): the guard of the revised tables reads the revision under
``FOR KEY SHARE``, which this lock excludes, so that no row enters a revision once it is judged
current here. It judges again what the request judged — still current, its name free —, computes
and keeps its indicators (``compute_indicators``, which EP-10 extends by ``register_indicators``),
marks it with its moment and its name, takes it from its project as the current revision, and
inscribes ``revision_mark`` in the journal, its author the requester. A refusal or a computation
that raises fails the task with nothing written; a worker stopped during it leaves the database as
it was (WF-DAT-0040, WF-ARC-0090). The locks are taken in one order: the revision, then its project.

An exit of the project that marks its current revision (``exitProject``, WF-CYC-0090, #2204) asks
the same marking, its task carrying the state aimed at and the reason (``exit_state``,
``exit_reason`` of the request): the worker, once it has marked, exits the project in the one
transaction of the task, the project having no current revision any more. A task that fails
applies neither, and the project keeps its state and its revision.

``load_marking`` marks a revision of the witness at the instant it imposes, by the same
transaction as the worker.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from waterfall.core.projects.interface import (
    ExitRequest,
    exit_project,
    no_background_task_running,
    set_current_revision,
    stored_lock_version,
)
from waterfall.core.revisions.commands import NO_BACKGROUND_TASK_RUNNING, REVISION_DRAFT
from waterfall.core.revisions.interface.shared import (
    STALE_LOCK_VERSION,
    found_revision,
    inscribe_revision,
    refuse,
)
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.tables import Revision
from waterfall.platform.errors import ConflictError, FieldError, PreconditionFailedError
from waterfall.platform.tasks import PROJECT, submit

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.platform.queue import TaskQueue

ALREADY_EXISTS = "ALREADY_EXISTS"
VERSION_NAME = "/version_name"
# What the task of a marking carries besides its project: the revision, its name, its description.
REVISION = "revision_id"
NAME = "version_name"
DESCRIPTION = "description"
# What it carries besides when the marking is the one of an exit of the project.
EXIT_STATE = "exit_state"
EXIT_REASON = "exit_reason"

# What computes and keeps the indicators of a revision being marked, in their order: EP-10's.
_INDICATORS: Registry[Callable[[Session, UUID], None]] = Registry()


@dataclass(frozen=True, slots=True)
class MarkingRequest:
    """A marking asked for: which revision, under which name, at the counter read.

    ``exit_state`` and ``exit_reason`` are those of the exit of the project that asks it, if any.
    """

    project_id: UUID
    revision_id: UUID
    version_name: str
    description: str | None
    lock_version: int
    exit_state: str | None = None
    exit_reason: str | None = None


def _name_taken(revision_id: UUID) -> ConflictError:
    """Refuse a name of version a marked revision of the project bears, naming it (WF-REV-0020)."""
    params = {"conflicting_object_id": str(revision_id)}
    return ConflictError(ALREADY_EXISTS, fields=(FieldError(VERSION_NAME, ALREADY_EXISTS, params),))


def _judge_name(session: Session, revision: Revision, version_name: str) -> None:
    """Refuse a name of version another marked revision of the same project bears."""
    holder = session.scalar(
        select(Revision.id).where(
            Revision.project_id == revision.project_id,
            Revision.status == "marked",
            Revision.version_name == version_name,
            Revision.id != revision.id,
        )
    )
    if holder is not None:
        raise _name_taken(holder)


def submit_marking(session: Session, queue: TaskQueue, request: MarkingRequest, act: Act) -> UUID:
    """Judge a marking asked for, then submit its task, in the transaction of the request.

    Under the lock of the revision, read under it, in the order of the contract: unknown (404), a
    stale counter (412), a marked revision (409 ``revision_draft``), a background task that writes
    in the project — another marking among them — (409 ``no_background_task_running``), a name of
    version taken (409 ``ALREADY_EXISTS``). Nothing is written then.
    """
    project_id = request.project_id
    revision = found_revision(session, request.revision_id, project_id, lock=True)
    if revision.lock_version != request.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": revision.lock_version}
        )
    if revision.status != "draft":
        raise refuse(REVISION_DRAFT)
    if not no_background_task_running(session, project_id):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)
    _judge_name(session, revision, request.version_name)
    payload: dict[str, Any] = {
        PROJECT: str(project_id),
        REVISION: str(revision.id),
        NAME: request.version_name,
        DESCRIPTION: request.description,
    }
    if request.exit_state is not None:
        payload[EXIT_STATE] = request.exit_state
        payload[EXIT_REASON] = request.exit_reason
    return submit(session, queue, "revision_mark", act.author, payload)


def run_marking(session: Session, payload: Mapping[str, Any], act: Act) -> None:
    """Mark the revision a task of marking names, in the transaction of the task (the worker's).

    The exit of the project the task carries, if it does, follows the marking: refused (409), it
    fails the task and undoes the marking with it. The counter of the project was judged by the
    request, and the marking has moved it since: the exit is judged on the state, as the project
    stands under its lock, and on no background task but this one.
    """
    mark_revision(session, UUID(payload[REVISION]), payload[NAME], payload.get(DESCRIPTION), act)
    exit_state = payload.get(EXIT_STATE)
    if exit_state is not None:
        project_id = UUID(payload[PROJECT])
        counter = stored_lock_version(session, project_id)
        request = ExitRequest(exit_state, payload.get(EXIT_REASON), counter)
        exit_project(session, project_id, request, act)


def mark_revision(
    session: Session, revision_id: UUID, version_name: str, description: str | None, act: Act
) -> None:
    """Mark the current revision of a project, in the transaction of the task.

    Under the lock of the revision: refused if unknown (404), marked already (409
    ``revision_draft``), or under a name of version taken (409 ``ALREADY_EXISTS``): a project has
    one current revision, locked here, and a marked one never changes its name, so that no other
    marking races this one for a name — the unique index of the names is the rampart of the base.
    Its indicators are computed before anything is written: a computation that raises leaves the
    revision current.
    """
    revision = found_revision(session, revision_id, lock=True)
    if revision.status != "draft":
        raise refuse(REVISION_DRAFT)
    _judge_name(session, revision, version_name)
    compute_indicators(session, revision_id)
    revision.status = "marked"
    revision.version_name = version_name
    revision.description = description
    revision.marked_at = act.at
    revision.updated_at = act.at
    revision.updated_by = act.author
    revision.lock_version += 1
    session.flush()
    set_current_revision(session, revision.project_id, None, act)
    inscribe_revision(session, revision, "revision_mark", revision.version_name, act)
    session.flush()


def register_indicators(compute: Callable[[Session, UUID], None]) -> Callable[[], None]:
    """Add what computes and keeps indicators of a revision being marked; give its withdrawal."""
    return _INDICATORS.register(compute)


def compute_indicators(session: Session, revision_id: UUID) -> None:
    """Compute and keep the indicators of a revision being marked, by each computation registered.

    Nothing, until EP-10 registers its own.
    """
    for compute in _INDICATORS.entries():
        compute(session, revision_id)


def load_marking(
    session: Session, revision_id: UUID, version_name: str, description: str | None, act: Act
) -> None:
    """Mark a revision of the witness, at the instant it imposes, as the worker marks it."""
    mark_revision(session, revision_id, version_name, description, act)
