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

``load_marking`` marks a revision of the witness at the instant it imposes, by the same
transaction as the worker.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from waterfall.core.projects.interface import (
    no_background_task_running,
    project_code,
    project_label,
    set_current_revision,
)
from waterfall.core.revisions.commands import NO_BACKGROUND_TASK_RUNNING, REVISION_DRAFT
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.tables import Revision
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditObject, AuditProject, Inscription, record
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
)
from waterfall.platform.tasks import PROJECT, submit

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.platform.queue import TaskQueue

NOT_FOUND = "NOT_FOUND"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
ALREADY_EXISTS = "ALREADY_EXISTS"
VERSION_NAME = "/version_name"
# What the task of a marking carries besides its project: the revision, its name, its description.
REVISION = "revision_id"
NAME = "version_name"
DESCRIPTION = "description"

# What computes and keeps the indicators of a revision being marked, in their order: EP-10's.
_INDICATORS: Registry[Callable[[Session, UUID], None]] = Registry()


@dataclass(frozen=True, slots=True)
class MarkingRequest:
    """A marking asked for: which revision, under which name, at the counter read."""

    project_id: UUID
    revision_id: UUID
    version_name: str
    description: str | None
    lock_version: int


def _refuse(condition: str) -> ConflictError:
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": condition})


def _name_taken(revision_id: UUID) -> ConflictError:
    """Refuse a name of version a marked revision of the project bears, naming it (WF-REV-0020)."""
    params = {"conflicting_object_id": str(revision_id)}
    return ConflictError(ALREADY_EXISTS, fields=(FieldError(VERSION_NAME, ALREADY_EXISTS, params),))


def _locked(session: Session, revision_id: UUID, project_id: UUID | None = None) -> Revision:
    """Lock a revision ``FOR UPDATE``, then read it under the lock; or refuse (404).

    ``FOR UPDATE``, not the ``FOR NO KEY UPDATE`` of an ``UPDATE`` alone: it excludes the
    ``FOR KEY SHARE`` under which the guard of a revised table reads the revision (#2104).
    """
    query = select(Revision).where(Revision.id == revision_id)
    if project_id is not None:
        query = query.where(Revision.project_id == project_id)
    query = query.with_for_update().execution_options(populate_existing=True)
    revision = session.scalars(query).first()
    if revision is None:
        raise NotFoundError(NOT_FOUND)
    return revision


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
    revision = _locked(session, request.revision_id, project_id)
    if revision.lock_version != request.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": revision.lock_version}
        )
    if revision.status != "draft":
        raise _refuse(REVISION_DRAFT)
    if not no_background_task_running(session, project_id):
        raise _refuse(NO_BACKGROUND_TASK_RUNNING)
    _judge_name(session, revision, request.version_name)
    payload = {
        PROJECT: str(project_id),
        REVISION: str(revision.id),
        NAME: request.version_name,
        DESCRIPTION: request.description,
    }
    return submit(session, queue, "revision_mark", act.author, payload)


def run_marking(session: Session, payload: Mapping[str, Any], act: Act) -> None:
    """Mark the revision a task of marking names, in the transaction of the task (the worker's)."""
    mark_revision(session, UUID(payload[REVISION]), payload[NAME], payload.get(DESCRIPTION), act)


def _inscribe(session: Session, revision: Revision, act: Act) -> None:
    """Inscribe the marking in the journal: the revision by its name of version, its project."""
    code = project_code(session, revision.project_id)
    label = project_label(session, revision.project_id)
    # The journal names a project by both its code and its label, or not at all (#927).
    named = (
        None if code is None or label is None else AuditProject(revision.project_id, code, label)
    )
    audited = AuditObject("revision", revision.id, revision.version_name)
    actor = inscribed_actor(session, act.author)
    record(session, Inscription("revision_mark", actor, audited, act.at, project=named))


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
    revision = _locked(session, revision_id)
    if revision.status != "draft":
        raise _refuse(REVISION_DRAFT)
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
    _inscribe(session, revision, act)
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
