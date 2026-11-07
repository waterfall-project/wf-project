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
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from waterfall.core.projects.interface import (
    ExitRequest,
    Viewer,
    exit_project,
    lock_counter,
    lock_project,
    no_background_task_running,
    require_project_manager,
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
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, FieldError, PreconditionFailedError
from waterfall.platform.tasks import PROJECT, submit

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    from sqlalchemy.orm import Session

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
EXIT_LOCK_VERSION = "exit_lock_version"

# What computes and keeps the indicators of a revision being marked, in their order: EP-10's.
_INDICATORS: Registry[Callable[[Session, UUID], None]] = Registry()


class Kept(Enum):
    """A description the marking does not send: the one kept at the creation stays (#2171)."""

    DESCRIPTION = "kept"


KEPT = Kept.DESCRIPTION


@dataclass(frozen=True, slots=True)
class MarkingRequest:
    """A marking asked for: which revision, under which name, at the counter read.

    ``exit_state``, ``exit_reason`` and ``exit_lock_version`` (the counter of the project the chief
    read) are those of the exit of the project that asks it, if any.
    """

    project_id: UUID
    revision_id: UUID
    version_name: str
    description: str | Kept | None
    lock_version: int
    exit_state: str | None = None
    exit_reason: str | None = None
    exit_lock_version: int | None = None


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


def _judge_project_counter(session: Session, project_id: UUID, read: int) -> None:
    """Refuse (412) an exit whose project was written since the chief read it (WF-IHM-0110).

    The project is locked after the revision, the order of the marking; the counter is read under
    its lock.
    """
    stored = lock_counter(session, project_id)
    if stored != read:
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": stored})


def submit_marking(
    session: Session, queue: TaskQueue, request: MarkingRequest, act: Act, viewer: Viewer
) -> UUID:
    """Judge a marking asked for, then submit its task, in the transaction of the request.

    Under the lock of the revision, read under it, then the lock of the project, under which the
    requester is judged again as a project manager (#2207) — in the request, not in the worker —
    in the order of the contract: unknown (404), no project manager (403, 404), a stale counter
    (412), a marked revision (409 ``revision_draft``), a background task that writes
    in the project — another marking among them — (409 ``no_background_task_running``), a name of
    version taken (409 ``ALREADY_EXISTS``). For an exit, the counter of the project the chief read
    is judged last, under the lock of the project (412). Nothing is written then.
    """
    project_id = request.project_id
    revision = found_revision(session, request.revision_id, project_id, lock=True)
    lock_project(session, project_id)
    require_project_manager(session, project_id, viewer)
    if revision.lock_version != request.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": revision.lock_version}
        )
    if revision.status != "draft":
        raise refuse(REVISION_DRAFT)
    if not no_background_task_running(session, project_id):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)
    _judge_name(session, revision, request.version_name)
    if request.exit_lock_version is not None:
        _judge_project_counter(session, project_id, request.exit_lock_version)
    payload: dict[str, Any] = {
        PROJECT: str(project_id),
        REVISION: str(revision.id),
        NAME: request.version_name,
    }
    # An absent description stays absent from the payload, down to the write; a null one is kept.
    if not isinstance(request.description, Kept):
        payload[DESCRIPTION] = request.description
    if request.exit_state is not None:
        payload[EXIT_STATE] = request.exit_state
        payload[EXIT_REASON] = request.exit_reason
        payload[EXIT_LOCK_VERSION] = request.exit_lock_version
    return submit(session, queue, "revision_mark", act.author, payload)


def run_marking(session: Session, payload: Mapping[str, Any], act: Act) -> None:
    """Mark the revision a task of marking names, in the transaction of the task (the worker's).

    The instant of the marking is taken once the revision and the project are locked, not when the
    task began: a designation validated while the task waited for the project is older than the
    marking it is judged against (``reference_correctable``, WF-REV-0040).

    The exit of the project the task carries, if it does, follows the marking: refused (409), it
    fails the task and undoes the marking with it. The counter of the project the chief read is
    judged again before anything is written, under the lock of the project taken after the one of
    the revision: a project written since the request is not exited on a state the chief did not
    confirm (412, the task fails). The marking then moves the counter: the exit is judged on the
    state, as the project stands under its lock, and on no background task but this one.
    """
    # The revision is locked, then the project, and the instant of the marking is taken under the
    # two: a designation validated meanwhile is older than the marking (WF-REV-0040, #2274).
    revision = found_revision(session, UUID(payload[REVISION]), lock=True)
    lock_project(session, revision.project_id)
    act = Act(act.author, utc_now())
    exit_state = payload.get(EXIT_STATE)
    if exit_state is not None:
        _judge_project_counter(session, UUID(payload[PROJECT]), payload[EXIT_LOCK_VERSION])
    description = payload.get(DESCRIPTION, KEPT)
    mark_revision(session, UUID(payload[REVISION]), payload[NAME], description, act)
    if exit_state is not None:
        project_id = UUID(payload[PROJECT])
        counter = stored_lock_version(session, project_id)
        request = ExitRequest(exit_state, payload.get(EXIT_REASON), counter)
        # The requester was judged a project manager in the request. The worker judges the quality
        # again, under the lock, for an exit alone: a marking alone writes no project.
        exit_project(session, project_id, request, act, Viewer(UUID(str(act.author)), ()))


def mark_revision(
    session: Session,
    revision_id: UUID,
    version_name: str,
    description: str | Kept | None,
    act: Act,
) -> None:
    """Mark the current revision of a project, in the transaction of the task.

    The description follows the rule of ``updateProject`` for ``client``: kept (``KEPT``), the one
    given at the creation stays; given, it replaces it; null, it clears it (#2171).

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
    if not isinstance(description, Kept):
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
