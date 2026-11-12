# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of an import, run by the worker in their one transaction, private to the module.

The analysis reads the file from the storage, then the format analyses it against the structure
aimed at — the current revision's, or the last marked one's when the application creates the
revision —, in a transaction frozen at its first read (``frozen_reading``, #2679), writing nothing
but the report, which then awaits its decision twenty-four hours (WF-ARC-0100). The application
reads the file and the format prepares it — reads it into its model (#2582, #2739) —, then, under
the lock of the import, of the current revision and of the project, judges again the requester — the
permission of the kind and the quality of contributor, as they stand now —, the state of the project
and the conditions of the kind; refused, the import is ``refused``. It then creates the current
revision if there is none, by the rules of ``createRevision`` (``open_revision_by_task``,
WF-INTF-0090), and the format applies the report with the model prepared to the structure, under its
lock: a refusal of the format, or anything that breaks, fails the import. Applied, the import is
inscribed in the journal (WF-SEC-0030); the undo history receives nothing (WF-IHM-0110). The file is
deleted once the transaction is committed, whatever the end. The file is read and prepared before
any lock is taken: nothing slow is done under a lock (python.md). A file the format refuses at the
preparation fails the import where its application failed it before (#2582), once the import is
judged again.

Either fails by ``UndoneError``: the worker undoes the work of the task — nothing of the project
written (WF-INTF-0080) —, then writes the end of the import in its place, ``failed`` or
``refused``, and fails the task with its cause. A worker stopped during either leaves the
database unchanged, the import where it stood; the task runs again from the start (WF-ARC-0090).
"""

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.exchanges.judgments import (
    IMPORT_KEY,
    REPORT_LIFETIME,
    REVISION_KEY,
    FormJudgment,
    ImportTarget,
    Judge,
    Standing,
    judge_import,
    judge_state,
)
from waterfall.core.exchanges.records import (
    aimed_by,
    end_without_writing,
    locked_import,
    remove_once_committed,
)
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.projects.interface import (
    lock_project,
    project_code,
    project_facts,
    project_label,
)
from waterfall.core.revisions.interface import (
    open_revision_by_task,
    revision_draft,
)
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import (
    Act,
    AuditObject,
    AuditProject,
    AuditRevision,
    Inscription,
    record,
)
from waterfall.platform.database import frozen_reading, utc_now
from waterfall.platform.errors import ServiceError
from waterfall.platform.tasks import UndoneError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface.imports import Format
    from waterfall.core.projects.interface import Viewer
    from waterfall.platform.storage import Bucket
    from waterfall.platform.tasks import Task

    # What finds the format of a kind of import, ``None`` if no module serves the kind.
    type Formats = Callable[[str], Format[Any] | None]


@dataclass(frozen=True, slots=True)
class Requester:
    """The account that confirmed an import, as it stands when the task runs, and its judge."""

    viewer: Viewer
    judge: Judge


def _content(files: Bucket, key: str) -> bytes:
    """Read the file of an import whole from the storage, by chunks: 10 MiB at most."""
    return b"".join(files.stream(key))


def _format(formats: Formats, kind: str) -> Format[Any]:
    """Give the format of a kind; one withdrawn since the opening fails the task (500)."""
    form = formats(kind)
    if form is None:
        msg = f"no format serves the kind {kind} any more"
        raise LookupError(msg)
    return form


def analyse(
    session: Session, task: Task, files: Bucket, formats: Formats
) -> Mapping[str, Any] | None:
    """Analyse the file of the import a task names, and keep its report for its decision.

    An import that no longer awaits this analysis — abandoned meanwhile, or of a later task — is
    left as it stands, nothing written. The format reads in a transaction of its own, frozen at its
    first read: the structure, its tree and its links as they stood together (#2679). What is read
    before the block — the row of the import, its revision and structure aimed at — is the import's
    own, not the project's: it is read in the session of the task, which the block cannot see, to
    decide whether to analyse at all, and the format reads the project only inside the block. The
    report is written under the lock of the import, read again under it: an abandonment that came
    during the analysis wins. An analysis that fails — the file gone, the format refusing or
    breaking — fails the import, its file deleted.
    """
    import_id = UUID(task.payload[IMPORT_KEY])
    row = session.get(ImportReport, import_id)
    if row is None or row.status != "analysing" or row.task_id != task.task_id:
        return None
    revision = task.payload.get(REVISION_KEY)
    aimed = None if revision is None else UUID(revision)
    target = ImportTarget(row.project_id, aimed, row.structure_id)
    try:
        form = _format(formats, row.kind)
        content = _content(files, row.object_key)
        with frozen_reading(session) as frozen:
            report = dict(form.analyse(frozen, target, content))
    except Exception as error:
        raise _undone(error, import_id, "analysing", files) from error
    row = locked_import(session, import_id)
    if row is None or row.status != "analysing" or row.task_id != task.task_id:
        return None
    now = utc_now()
    row.report = report
    row.status = "analysed"
    row.analysed_at = now
    row.expires_at = now + REPORT_LIFETIME
    session.flush()
    return None


def _undone(error: Exception, import_id: UUID, status: str, files: Bucket) -> UndoneError:
    """Fail an import that stands ``status`` with its task, once the work of the task is undone."""

    def trace(session: Session) -> None:
        end_without_writing(session, import_id, status, "failed", files)

    return UndoneError(error, trace)


def _refusal(error: Exception, import_id: UUID, files: Bucket) -> UndoneError:
    """Refuse an import being applied with its task: the conditions judged again failed it."""

    def trace(session: Session) -> None:
        end_without_writing(session, import_id, "applying", "refused", files)

    return UndoneError(error, trace)


def apply(
    session: Session, task: Task, files: Bucket, formats: Formats, requester: Requester
) -> Mapping[str, Any] | None:
    """Apply the report of the import a task names, judged again, in the transaction of the task.

    An import that no longer awaits this application is left as it stands, nothing written. The
    format prepares the file before the first lock (#2582, #2739).
    """
    import_id = UUID(task.payload[IMPORT_KEY])
    found = session.get(ImportReport, import_id)
    if found is None or found.status != "applying" or found.task_id != task.task_id:
        return None
    try:
        content = _content(files, found.object_key)
        form = _format(formats, found.kind)
        prepared = _Prepared.of(form, content)
    except Exception as error:
        raise _undone(error, import_id, "applying", files) from error
    row = locked_import(session, import_id)
    if row is None or row.status != "applying" or row.task_id != task.task_id:
        return None
    try:
        target = _judged(session, row, form, requester, task)
    except ServiceError as refusal:
        raise _refusal(refusal, import_id, files) from refusal
    except Exception as error:
        raise _undone(error, import_id, "applying", files) from error
    act = Act(task.requested_by, utc_now())
    try:
        form.apply(session, target, prepared.model(), row.report or {}, act)
    except Exception as error:
        raise _undone(error, import_id, "applying", files) from error
    row.status = "applied"
    row.applied_at = act.at
    row.revision_id = target.revision_id
    row.structure_id = target.structure_id
    session.flush()
    _inscribe(session, row, act)
    remove_once_committed(session, files, row.object_key)
    return None


@dataclass(frozen=True, slots=True)
class _Prepared:
    """The model a format read a file into, or the error it raised instead."""

    read: Any
    refusal: ServiceError | None

    @classmethod
    def of(cls, form: Format[Any], content: bytes) -> _Prepared:
        """Have a format read a file, holding no lock; keep its refusal for the application.

        A refusal of the file (``FILE_FORMAT_UNREADABLE``, a ``ServiceError``) waits for the
        import to be judged again, as when applying read the file under the locks (#2582): the
        project turned terminal refuses the import. Any other error is a defect of the format: it
        fails the import at once, as the reading of the file from the storage does.
        """
        try:
            return cls(form.prepare(content), None)
        except ServiceError as refusal:
            return cls(None, refusal)

    def model(self) -> Any:
        """Give the model read, or raise again the refusal of the preparation."""
        if self.refusal is not None:
            raise self.refusal
        return self.read


def _judged(
    session: Session, row: ImportReport, form: Format[Any], requester: Requester, task: Task
) -> ImportTarget:
    """Judge an import again as its task runs, then give what it writes; or raise the refusal.

    The requester's permission and quality first, as they stand now (WF-ARC-0100); then, under the
    lock of the current revision, then of the project — the order of the locks of EP-04 —, the
    state of the project, and the revision created if there is none, under its own rules; then the
    conditions of the kind on what it writes.
    """
    project_id = row.project_id
    requester.judge(session, project_id, form.permission)
    if form.scope != "structure":
        standing = Standing(project_id, lock_project(session, project_id), form.scope)
        target = ImportTarget(
            project_id,
            None,
            None,
            task.task_id,
            import_id=row.id,
            period_from=row.period_from,
            period_to=row.period_to,
        )
        judge_import(
            session,
            standing,
            requester.viewer,
            FormJudgment(partial(form.judge, session, target), form.judged_first),
            task.task_id,
        )
        return target
    current = project_facts(session, project_id).current_revision_id
    if current is not None:
        revision_draft(session, current)
    facts = lock_project(session, project_id)
    if facts.current_revision_id != current:
        # A revision marked or opened between the two reads: judged as it stands under the lock.
        current = facts.current_revision_id
        if current is not None:
            revision_draft(session, current)
    # A format judged first sees the revision as it stands, possibly none: it reads the project.
    provisional = ImportTarget(project_id, current, None, task.task_id, import_id=row.id)
    judge_state(
        session,
        Standing(project_id, facts, form.scope),
        requester.viewer,
        task.task_id,
        partial(form.judge, session, provisional) if form.judged_first else None,
    )
    if current is None:
        # The opening shares the lock of the reference while this one holds the lock of the
        # project, against the order "reference, then project" (#2510). Safe as long as no holder
        # of the reference waits for the lock of a project (``share_reference``): the change that
        # redates locks only the structures of the current revisions and those revisions, and this
        # project has none.
        # It is not shared before the project's: a write of the planning never locks the reference,
        # and whether the import opens the revision is known only under the lock of the project.
        act = Act(task.requested_by, utc_now())
        current = open_revision_by_task(session, project_id, act, task.task_id)
    target = ImportTarget(
        project_id, current, aimed_by(session, row, current), task.task_id, import_id=row.id
    )
    if not form.judged_first:
        form.judge(session, target)
    return target


def _inscribe(session: Session, row: ImportReport, act: Act) -> None:
    """Inscribe the application of an import in the journal: it, its revision, its project.

    The revision of an import is the current one, which bears no name yet (WF-SEC-0030).
    """
    label = project_label(session, row.project_id)
    named = (
        None
        if label is None
        else AuditProject(row.project_id, project_code(session, row.project_id), label)
    )
    revision = None if row.revision_id is None else AuditRevision(row.revision_id, None)
    audited = AuditObject("import", row.id, row.filename, revision)
    actor = inscribed_actor(session, act.author)
    params = {"import_kind": row.kind}
    record(session, Inscription("import_apply", actor, audited, act.at, named, params))
