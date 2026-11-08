# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports: the exporters a module registers, the task that runs one, and its result.

An exporter gives the file of a kind of export, its type and its name, which the worker deposits
under ``exports/<task_id>.<ext>`` (EP-06, "Les exports"). The exchanges find the one of a kind
(``ExportKind``) in their registry, filled by the module that serves it at the import of its
interface — the planning for ``ms_project_schedule`` and ``task_tree_image`` (US-1430, US-1440),
EP-07 and EP-09 for theirs. ``request_export`` deposits the task (``requestExport``), the worker
runs it through ``run_export``, and ``result_of`` and ``consumed`` serve its file once
(``getBackgroundTaskResult``).

Declared by US-1380/L1; US-1430/L2 fills the mechanics. The purge of the exports whose file nobody
downloaded is US-1420/L2's.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal, Protocol
from uuid import UUID

from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.interface import list_cost_structures, read_revision
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, ForbiddenError, NotFoundError
from waterfall.platform.registry import Registry
from waterfall.platform.tasks import BackgroundTask, read_task, submit

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket
    from waterfall.platform.tasks import Task

# The kinds of an export, as the contract says them (``ExportKind``).
type ExportKind = Literal["ms_project_schedule", "estimate", "remaining", "task_tree_image"]

# The exports live in the bucket the settings name, under this prefix (EP-06, "Ce que le cadrage
# décide").
EXPORTS_PREFIX = "exports/"
# The command of a revision that judges each kind of export (``RevisionCommand``), and the
# permission that command asks for, which a refusal names (WF-CYC-0110).
EXPORT_COMMANDS: Mapping[ExportKind, tuple[str, str]] = {
    "ms_project_schedule": ("export_planning", "planning.read"),
    "estimate": ("export_estimate", "estimate.read"),
    "remaining": ("export_remaining", "remaining.read"),
    "task_tree_image": ("export_task_tree_image", "planning.read"),
}
# The key of the result of a task ``export`` that says its file is gone — downloaded to the end, or
# expired — and its link with it.
CONSUMED = "consumed"
MAIN = "main"
NOT_FOUND = "NOT_FOUND"
PERMISSION_MISSING = "PERMISSION_MISSING"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
TASK_SUCCEEDED = "task_succeeded"
# The key of the payload that names the project: not ``project_id``, which makes the project wait
# for the task (``project_task_pending``) — an export reads, and blocks no write.
PROJECT = "project"


@dataclass(frozen=True, slots=True)
class ExportOrder:
    """What an export is asked of: the revision, its structure, and the account that asks.

    ``depth`` is the level an image of the task tree keeps (null, the whole depth), and the account
    names the language of a header; ``review_date`` is the one of a remaining to commit (EP-09).
    """

    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    requested_by: UUID
    depth: int | None
    review_date: date | None


@dataclass(frozen=True, slots=True)
class ExportedFile:
    """The file of an export: its content, its type and the name it is downloaded under."""

    content: bytes
    media_type: str
    filename: str


class Exporter(Protocol):
    """What gives the file of a kind of export, in the transaction of the task ``export``."""

    def export(self, session: Session, order: ExportOrder) -> ExportedFile:
        """Give the file of an export, writing nothing."""
        ...


@dataclass(frozen=True, slots=True)
class ExportAsked:
    """What ``requestExport`` asks: the kind, the revision, its structure and the kind's options."""

    kind: ExportKind
    revision_id: UUID
    structure_id: UUID | None
    depth: int | None
    review_date: date | None


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Where the file of an export lies, and how it is given: its key, its name, its type."""

    object_key: str
    filename: str
    media_type: str


# The exporter of each kind of export, in the order of their registration.
_EXPORTERS: Registry[tuple[ExportKind, Exporter]] = Registry("exchanges.exporters")


def register_exporter(kind: ExportKind, exporter: Exporter) -> Callable[[], None]:
    """Add the exporter of a kind of export; give its withdrawal; refused if the kind has one."""
    if kind in exporters():
        msg = f"the kind {kind} has an exporter already"
        raise ValueError(msg)
    return _EXPORTERS.register((kind, exporter))


def exporters() -> Mapping[ExportKind, Exporter]:
    """Give the exporter of each kind of export registered, by kind."""
    return dict(_EXPORTERS.entries())


def request_export(
    session: Session, queue: TaskQueue, project_id: UUID, asked: ExportAsked, viewer: Viewer
) -> UUID:
    """Deposit the task of an export, under the command ``export_*`` of its revision; give it.

    The revision is the project's, and so is the structure, the main one by default, or 404. The
    command of the kind lacks no condition: it is listed to whoever holds the permission to consult
    the function and absent otherwise, which is refused naming that permission (403). The review
    date of a remaining to commit is the day of the request unless it is named. Nothing is written
    but the task, which makes no project wait.
    """
    revision = read_revision(session, project_id, asked.revision_id, viewer)
    structures = list_cost_structures(session, project_id, asked.revision_id, viewer)
    if asked.structure_id is None:
        named = [each.structure_id for each in structures if each.kind == MAIN]
    else:
        named = [
            each.structure_id for each in structures if each.structure_id == asked.structure_id
        ]
    if not named:
        raise NotFoundError(NOT_FOUND)
    structure_id = named[0]
    command, permission = EXPORT_COMMANDS[asked.kind]
    if command not in {each.command for each in revision.commands}:
        raise ForbiddenError(PERMISSION_MISSING, {"missing_permission": permission})
    review_date = asked.review_date
    if asked.kind == "remaining" and review_date is None:
        review_date = current_day(utc_now())
    payload = {
        PROJECT: project_id,
        "kind": asked.kind,
        "revision_id": asked.revision_id,
        "structure_id": structure_id,
        "depth": asked.depth,
        "review_date": review_date,
    }
    return submit(session, queue, "export", viewer.user_id, payload)


def run_export(session: Session, task: Task, bucket: Bucket) -> Mapping[str, Any]:
    """Write the file of an export under ``exports/<task_id>.<ext>``, in the task's transaction.

    The exporter of the kind gives the file, and the task keeps where it lies. The object is
    written before the transaction commits: a task run again writes the same key.
    """
    payload = task.payload
    if task.requested_by is None:
        message = "an export is asked by an account"
        raise ValueError(message)
    kind: ExportKind = payload["kind"]
    review_date = payload["review_date"]
    order = ExportOrder(
        project_id=UUID(payload[PROJECT]),
        revision_id=UUID(payload["revision_id"]),
        structure_id=UUID(payload["structure_id"]),
        requested_by=task.requested_by,
        depth=payload["depth"],
        review_date=None if review_date is None else date.fromisoformat(review_date),
    )
    made = exporters()[kind].export(session, order)
    key = f"{EXPORTS_PREFIX}{task.task_id}{PurePosixPath(made.filename).suffix}"
    bucket.put(key, made.content, made.media_type)
    return {"object_key": key, "filename": made.filename, "media_type": made.media_type}


def has_file(result: Mapping[str, Any] | None) -> bool:
    """Tell whether the result of a task ``export`` that succeeded still has a file to download."""
    return result is not None and not result.get(CONSUMED)


def result_of(session: Session, task_id: UUID, requested_by: UUID) -> ExportResult:
    """Give where the file of an export that succeeded lies, unless it was consumed.

    A task of another account, or one that gives no file — another kind, or an export whose file
    was downloaded or expired — does not exist for the caller (404); an export that has not
    succeeded has no file yet (409 ``task_succeeded``, WF-ARC-0090).
    """
    row = read_task(session, task_id, requested_by)
    if row is None or row.kind != "export":
        raise NotFoundError(NOT_FOUND)
    if row.status != "succeeded":
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": TASK_SUCCEEDED})
    kept = row.result
    if kept is None or not has_file(kept):
        raise NotFoundError(NOT_FOUND)
    return ExportResult(kept["object_key"], kept["filename"], kept["media_type"])


def consumed(session: Session, task_id: UUID) -> None:
    """Mark the result of an export consumed, once its last byte is sent (WF-DAT-0120)."""
    row = session.get(BackgroundTask, task_id)
    if row is not None and row.result is not None:
        row.result = {**row.result, CONSUMED: True}
