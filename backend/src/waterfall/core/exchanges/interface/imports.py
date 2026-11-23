# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports in two steps: the formats a module registers, the deposit, the analysis, the apply.

A format knows four things: read the header of a file deposited and say whether it recognises it,
analyse the file against the structure aimed at and give a report in codes without writing anything,
read the file into its model before the application takes a lock, and apply a report with that model
in the transaction of the task, judging again what the analysis accepted (EP-06, "L'import en deux
temps"; EP-09, "La préparation des imports hors verrou et la lecture figée"). The exchanges know no
format: they find the one of a kind (``ExchangeKind``) in their registry, filled by the module that
serves it at the import of its interface — the planning for ``ms_project_schedule`` (US-1430), EP-07
and EP-09 for theirs —, and read of the file only the header the format asks for
(``Format.header_length``). The header is parsed before the lock of the project, out of any
transaction (``parse_head``), and judged under it (US-3190/L2, #4419): a workbook read does not hold
the writes of the project.

The deposit of a file (``uploadFile``: ``deposit``), the opening of an import (``open_import``:
the header by the format, the conditions, the task of the analysis), its reading and its list
(``read_import``, ``list_imports``), its abandonment (``abandon_import``), its application
(``apply_import``: the conditions judged again, the task) and the rule of the durations of a
planning in calendar gap (``set_duration_rule``: a new analysis under it, US-2000) serve the API;
the worker runs the analysis and the application (``import_analysis``, ``import_apply``) through
``run_analysis`` and ``run_apply``. An import ends ``applied``, or without writing —
``abandoned``, ``expired``, ``failed``, ``refused`` —, and its file is deleted from the storage once
the transaction that ends it is committed (WF-ARC-0100, WF-DAT-0120). The permission and the
quality an import asks of who acts on it are judged by the caller's ``Judge``, the API's or the
worker's: the evaluation of the permissions sits above this module (WF-ADM-0110).

Declared by US-1380/L1; filled by US-1420/L1. The purge of what expired is US-1420/L2's.
"""

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, Literal, Protocol

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import defer

from waterfall.core.exchanges import running
from waterfall.core.exchanges.judgments import (
    IMPORT_KEY,
    PASSING,
    REVISION_KEY,
    DurationRule,
    FormJudgment,
    ImportScope,
    ImportTarget,
    Judge,
    Standing,
    judge_import,
    refused,
)
from waterfall.core.exchanges.records import (
    aimed_by,
    end_unwritten,
    found_import,
    remove_once_committed,
)
from waterfall.core.exchanges.states import (
    AWAITING_DECISION,
    ENDED_WITHOUT_WRITING,
    NOT_APPLIED,
    RUNNING,
    abandon_lacks,
    apply_lacks,
    commands_of,
    expiry_read,
    rule_lacks,
    rule_of,
    status_read,
)
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.exchanges.unchanged import judge_unchanged, written_at_request
from waterfall.core.projects.interface import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    CommandAvailability,
    contributor_kind,
    lock_project,
)
from waterfall.core.revisions.interface import aimed_structure, last_marked_revision
from waterfall.platform.database import unique_violated
from waterfall.platform.errors import (
    NOT_FOUND,
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id
from waterfall.platform.registry import Registry
from waterfall.platform.tasks import PROJECT, BackgroundTask, submit
from waterfall.platform.uploads import (
    IMPORT,
    MOST_PENDING,
    FileUpload,
    Whole,
    pending_imports,
    record_whole,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.platform.audit import Act
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket
    from waterfall.platform.tasks import Task

# The kinds of an import, as the contract says them (``ExchangeKind``).
type ExchangeKind = Literal["ms_project_schedule", "estimate", "remaining", "actual_costs"]

FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
FILE_TOO_LARGE = "FILE_TOO_LARGE"
PENDING_UPLOADS_BELOW_LIMIT = "pending_uploads_below_limit"
UPLOAD_PURPOSE_MISMATCH = "UPLOAD_PURPOSE_MISMATCH"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
# A file of an import: 10 MiB at most, the size of an MS Project file (§4.6.2); a name as long as
# a deposit keeps.
LARGEST_FILE = 10 * 1024**2
LONGEST_NAME = 255
UPLOAD_INDEX = "uq_import_report_upload_id"


class Format[Prepared, Parsed](Protocol):
    """What reads, analyses, prepares and applies a file of a kind of import.

    ``header_length`` is the number of bytes of the head of the file ``parse_header`` receives;
    ``scope`` what an import of the kind writes; ``reading`` the permission to consult the function
    the kind is of (``planning.read`` for a planning, ``estimate.read`` for an estimate…), without
    which the imports of the kind do not exist for the caller (404; #2473); ``permission`` the
    permission it asks of who opens, applies or abandons it — and of its requester again when its
    task runs —, the quality of contributor with it (``planning.write`` for a planning).
    The header is read in two steps (US-3190/L2). ``parse_header`` parses the head of a file before
    the opening takes the lock of the project, reading nothing of the database. The refusals of
    format it knows — a head it does not recognise, a file damaged or beyond the bounds — are kept
    in what it gives, ``Parsed``, never raised, as is what the second step needs of the head; a
    defect it does not know still raises. ``Parsed`` is typed inside each format only: the registry
    holds ``Format[Any, Any]``, and erases it. ``judge_header`` judges that under the lock, at the
    place the contract gives the refusal in the order of ``openImport``, raising it then by a typed
    exception (422 ``FILE_FORMAT_UNREADABLE``, ``expected_format``, ``expected_version``) — and
    judging what depends on the database, the mapping of the actual costs. ``judge`` refuses an
    import of the kind on the state of the project or of the structure aimed at, by the condition
    the contract names after those of the exchanges (409 ``project_before_in_progress`` for an
    estimate of the main structure, ``actual_cost_mapping_complete`` for the actual costs), or
    before them when ``judged_first`` is set — ``project_in_progress`` of a remaining to commit,
    which ``ProjectCommand.import_remaining`` names first (US-1630; #2796) —, at the opening, at the
    application and again when its task runs: refused after the analysis, the import is
    ``refused``. A format that is ``judged_first`` is judged, when its task runs, on a target whose
    structure may be missing — the revision is not opened yet, nor the structure aimed at known —:
    its ``judge`` reads the project and the revision only.

    ``analyse`` gives the report of the file against the structure aimed at, in codes
    and parameters (``ImportReport`` as the contract reads it), writing nothing, in a transaction
    frozen at its first read (``REPEATABLE READ``, read only; #2679).

    The application comes in two steps (#2582, #2739). ``prepare`` reads the file and gives its
    model in memory — the slow part: a workbook, a planning of 10 MiB —, before the task takes any
    lock, reading nothing of the database; a file it cannot read fails the import as the
    application would have. ``apply`` writes the report into the structure with that model, in the
    transaction of the task — taking the lock of the structure, and redating it —, judging again
    what the analysis accepted: a refusal then fails the import. It only judges again and writes.

    The ``target`` ``judge`` receives is that of the write: at the application, the structure of
    the current revision — the copy of the one analysed when that was of the last marked revision —,
    the revision and the structure aimed at when there is no current revision yet.
    """

    header_length: int
    scope: ImportScope
    reading: str
    permission: str
    judged_first: bool

    def parse_header(self, head: bytes) -> Parsed:
        """Parse the head of a file, before any lock: a refusal is kept, never raised."""
        ...

    def judge_header(self, session: Session, parsed: Parsed) -> None:
        """Refuse, under the lock of the project, a head the format does not recognise."""
        ...

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import of the kind on the state of the project or of its structure (409)."""
        ...

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Give the report of a file against the structure aimed at, writing nothing."""
        ...

    def prepare(self, content: bytes) -> Prepared:
        """Read a file into its model, before any lock: nothing of the database is read."""
        ...

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        prepared: Prepared,
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write a report into the structure, judging again what the analysis accepted."""
        ...


@dataclass(frozen=True, slots=True)
class ImportMeans:
    """Where the imports put what they leave: the queue of the worker, the bucket of the storage."""

    queue: TaskQueue
    files: Bucket


@dataclass(frozen=True, slots=True)
class Confirmer:
    """Who acts on an import, and when; its permissions, and what judges its standing (403)."""

    act: Act
    viewer: Viewer
    judge: Judge


@dataclass(frozen=True, slots=True)
class DepositedFile:
    """A file deposited for an import, as ``uploadFile`` gives it back."""

    upload_id: UUID
    filename: str
    size_bytes: int
    uploaded_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class HeadToRead:
    """Where the head of a deposited file lies, and how many bytes its format reads of it."""

    object_key: str
    length: int


@dataclass(frozen=True, slots=True)
class ParsedHead:
    """The head of a deposited file as the format of its kind parsed it, before any lock.

    ``parsed`` is what ``Format.parse_header`` gave, which ``judge_header`` judges under the lock
    of the project: wrapped, so that a format whose parse gives ``None`` when it recognises the head
    is not taken for a file the storage lost.
    """

    parsed: object


@dataclass(frozen=True, slots=True)
class ImportOpening:
    """An import asked for (``ImportRequest``): its kind, its deposit, its structure, its period."""

    project_id: UUID
    kind: ExchangeKind
    upload_id: UUID
    structure_id: UUID | None = None
    period_from: date | None = None
    period_to: date | None = None


@dataclass(frozen=True, slots=True)
class ImportView:
    """An import as it is read: its state judged at the reading, its report, task and commands.

    The commands are those the reader holds the permission of, none otherwise, and none in a list.
    """

    import_id: UUID
    kind: str
    filename: str
    structure_id: UUID | None
    revision_id: UUID | None
    period_from: date | None
    period_to: date | None
    status: str
    created_at: datetime
    expires_at: datetime | None
    report: Mapping[str, Any] | None
    task_id: UUID | None
    commands: tuple[CommandAvailability, ...]


@dataclass(frozen=True, slots=True)
class ImportPage:
    """The page of the imports of a project a list asks for: how many, from which."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ImportList:
    """A page of the imports of a project, and how many it has."""

    views: list[ImportView]
    total: int


@dataclass(frozen=True, slots=True)
class RuleChange:
    """The rule of the durations asked for an import of a project (``ImportDurationRuleWrite``)."""

    project_id: UUID
    import_id: UUID
    rule: DurationRule


@dataclass(frozen=True, slots=True)
class ImportRefused:
    """An application refused for good: the import is written ``refused``, its file to delete.

    The caller commits it — the file goes once committed —, then answers ``refusal``.
    """

    refusal: ServiceError


# The format of each kind of import, in the order of their registration.
_FORMATS: Registry[tuple[ExchangeKind, Format[Any, Any]]] = Registry("exchanges.formats")


def register_format(kind: ExchangeKind, form: Format[Any, Any]) -> Callable[[], None]:
    """Add the format of a kind of import; give its withdrawal; refused if the kind has one."""
    if kind in formats():
        msg = f"the kind {kind} has a format already"
        raise ValueError(msg)
    return _FORMATS.register((kind, form))


def formats() -> Mapping[ExchangeKind, Format[Any, Any]]:
    """Give the format of each kind of import registered, by kind."""
    return dict(_FORMATS.entries())


def _format_named(kind: str) -> Format[Any, Any] | None:
    """Give the format of a kind read from a row or a request, ``None`` if no module serves it."""
    return next((form for named, form in _FORMATS.entries() if named == kind), None)


def _format_of(kind: str) -> Format[Any, Any]:
    """Give the format of a kind; a kind no module serves is a file no format recognises (422)."""
    form = _format_named(kind)
    if form is None:
        raise UnprocessableError(FILE_FORMAT_UNREADABLE, {"expected_format": kind})
    return form


def _readable(kind: str, viewer: Viewer) -> bool:
    """Tell whether the imports of a kind exist for ``viewer``: it consults the kind's function.

    The route judges the project's visibility alone; the kind is judged here, a kind no module
    serves being read by no one (#2473).
    """
    form = _format_named(kind)
    return form is not None and form.reading in viewer.permissions


def _judge_acting(
    session: Session, project_id: UUID, form: Format[Any, Any], confirmer: Confirmer
) -> None:
    """Judge who acts on an import of a kind: the reading of the kind, then its permission.

    Without the reading, the import is refused as unknown (404), as ``getImport`` refuses it; then
    the permission of the kind and the quality of contributor (403). Judged with the import, under
    its lock, so that an application whose requester lost either refuses it for good (#1789).
    """
    confirmer.judge(session, project_id, form.reading)
    confirmer.judge(session, project_id, form.permission)


def judge_deposit(purpose: str, filename: str | None, size_bytes: int) -> None:
    """Refuse a file deposited for an import before it is kept, nothing written.

    A backup is deposited by parts, never here (422 ``/purpose``, ``UPLOAD_PURPOSE_MISMATCH``); a
    file beyond 10 MiB is refused (413 ``FILE_TOO_LARGE``); an empty file, or one without a name,
    is refused on ``/file`` (422 ``VALUE_REQUIRED``), as a name longer than a deposit keeps
    (``VALUE_TOO_LONG``, ``max_length`` as every ``VALUE_TOO_LONG``, #4732) and a name that holds
    the NUL character, refused as every text that holds it (``VALIDATION_FAILED``; BEX-08, #4426).
    """
    if purpose != IMPORT:
        mismatch = FieldError("/purpose", UPLOAD_PURPOSE_MISMATCH)
        raise UnprocessableError(VALIDATION_FAILED, fields=(mismatch,))
    if size_bytes > LARGEST_FILE:
        raise PayloadTooLargeError(FILE_TOO_LARGE)
    if not filename or size_bytes == 0:
        raise UnprocessableError(VALIDATION_FAILED, fields=(FieldError("/file", VALUE_REQUIRED),))
    if len(filename) > LONGEST_NAME:
        too_long = FieldError("/file", VALUE_TOO_LONG, {"max_length": LONGEST_NAME})
        raise UnprocessableError(VALIDATION_FAILED, fields=(too_long,))
    if "\x00" in filename:
        nul = FieldError("/file", VALIDATION_FAILED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(nul,))


def judge_room(session: Session, act: Act) -> None:
    """Refuse a deposit to an account that keeps as many pending as it may (409), nothing written.

    A deposit is pending while no import used it and it has not expired: an import that opens on
    one, or the purge that deletes one at its term, frees a place. Counted without a lock, before
    the file is written (US-3240, #4423): the bound guards against a loop, and is no invariant.
    """
    if act.author is None:
        msg = "a file is deposited by an account"
        raise ValueError(msg)
    used = select(ImportReport.upload_id)
    if pending_imports(session, act.author, act.at, used) >= MOST_PENDING:
        conflict = {"missing_condition": PENDING_UPLOADS_BELOW_LIMIT, "maximum": MOST_PENDING}
        raise ConflictError(STATE_FORBIDS_OPERATION, conflict)


def deposit(
    session: Session, upload_id: UUID, filename: str, size_bytes: int, act: Act
) -> DepositedFile:
    """Keep a file deposited for an import, in one piece, for twenty-four hours (``uploadFile``).

    The file is on the storage already, under the key of the deposit (``uploads/<upload_id>``);
    its author alone may open an import of it.
    """
    if act.author is None:
        msg = "a file is deposited by an account"
        raise ValueError(msg)
    row = record_whole(session, upload_id, Whole(filename, size_bytes, act.author), act.at)
    return DepositedFile(row.id, row.filename, row.size_bytes, act.at, row.expires_at)


def _usable_deposit(session: Session, upload_id: UUID, act: Act) -> FileUpload | None:
    """Give a deposit an import may open now: completed, unexpired, unused, its author's own.

    A deposit another account made does not exist for the caller, as an unknown one. The row is
    read under a lock: the purge deletes a deposit expired with its object, and an import opened
    on the deposit just before its term would find its file gone — the purge waits for the
    import's transaction, or the import finds the row gone.
    """
    row = session.get(FileUpload, upload_id, with_for_update=True)
    if (
        row is None
        or row.completed_at is None
        or row.expires_at <= act.at
        or row.uploaded_by != act.author
    ):
        return None
    used = select(ImportReport.id).where(ImportReport.upload_id == upload_id)
    return None if session.scalar(used.limit(1)) is not None else row


def head_to_read(session: Session, upload_id: UUID, kind: str, act: Act) -> HeadToRead | None:
    """Say where the head of a deposited file lies, which the opening reads before its judgment.

    ``None`` for a deposit the opening will refuse, or a kind no format serves: the head is read
    out of the transaction that judges, the storage being slow beside a lock (python.md).
    """
    form = _format_named(kind)
    row = _usable_deposit(session, upload_id, act)
    if form is None or row is None or row.purpose != IMPORT:
        return None
    return HeadToRead(row.object_key, form.header_length)


def parse_head(kind: str, head: bytes) -> ParsedHead | None:
    """Parse the head of a deposited file by the format of its kind, out of any transaction.

    The slow part of the header — a workbook opened, its first rows read — holds no lock nor
    connection; ``open_import`` judges what it gives under the lock of the project (#4419).
    ``None`` for a kind no format serves, which the opening refuses before it looks at the head.
    """
    form = _format_named(kind)
    return None if form is None else ParsedHead(form.parse_header(head))


def kept_refusal(check: Callable[[bytes], None], head: bytes) -> UnprocessableError | None:
    """Give the refusal ``check`` raises on a head, kept for its judgment; ``None`` if it passes.

    What a format's ``parse_header`` gives when its reader refuses by raising (422).
    """
    try:
        check(head)
    except UnprocessableError as refusal:
        return kept(refusal)
    return None


def kept(refusal: UnprocessableError) -> UnprocessableError:
    """Give a refusal without its trace, to be kept until it is raised under the lock.

    The traceback of a refusal, and the exception it was raised in the midst of, hold the frames
    that held the bytes of the workbook: a refusal kept has none, and is raised afresh.
    """
    refusal.__traceback__ = None
    refusal.__context__ = None
    refusal.__cause__ = None
    return refusal


def _judge_period(opening: ImportOpening) -> None:
    """Refuse an extracted period whose end precedes its start (422 ``/period_to``)."""
    start, end = opening.period_from, opening.period_to
    if start is not None and end is not None and end < start:
        inverted = FieldError("/period_to", VALUE_OUT_OF_RANGE, {"minimum": start.isoformat()})
        raise UnprocessableError(VALIDATION_FAILED, fields=(inverted,))


def _aimed(session: Session, standing: Standing, named: UUID | None) -> ImportTarget:
    """Resolve what an import aims at: a structure of the current revision, or of the last marked.

    The main one by default; a structure named that the revision does not hold is refused (404).
    An import of the project aims at none.
    """
    project_id = standing.project_id
    if standing.scope != "structure":
        return ImportTarget(project_id, None, None)
    current = standing.facts.current_revision_id
    revision_id = current or last_marked_revision(session, project_id)
    structure_id = (
        None if revision_id is None else aimed_structure(session, project_id, revision_id, named)
    )
    if named is not None and structure_id is None:
        raise NotFoundError(NOT_FOUND)
    return ImportTarget(project_id, revision_id, structure_id)


def open_import(
    session: Session,
    queue: TaskQueue,
    opening: ImportOpening,
    head: ParsedHead | None,
    confirmer: Confirmer,
) -> ImportView:
    """Open an import of a file deposited, and deposit the task of its analysis (``openImport``).

    ``head`` is the head of the deposited file as the format of ``opening.kind`` parsed it, before
    this transaction (``parse_head``); ``None`` when there was none to read. Under the lock of the
    project, in the order of the contract: a kind no format serves (422), the reading of the kind
    (404, #2473), its permission and the quality of contributor (403), an inverted period (422), a
    terminal project (409 ``project_not_terminal``), a deposit unknown, expired, used already or
    another's (404), made for a restoration (422 ``/upload_id``), a structure the revision does not
    hold (404), the condition of a remaining to commit's phase (409 ``project_in_progress``,
    ``Format.judged_first``; #2796), a task writing in the project, the permission to create the
    revision the import would create (409), the conditions of the kind (409), then the head of the
    file, judged by the format on what it parsed: for the actual costs the mapping first (409
    ``actual_cost_mapping_complete``), then a head the format does not recognise (422
    ``FILE_FORMAT_UNREADABLE``). The import is written ``analysing``, the task of its analysis
    deposited in the transaction; it writes in the current revision, or in none yet
    (``revision_id`` null), the application creating it (WF-INTF-0090).
    """
    act = confirmer.act
    form = _format_of(opening.kind)
    project_id = opening.project_id
    _judge_acting(session, project_id, form, confirmer)
    _judge_period(opening)
    standing = Standing(project_id, lock_project(session, project_id), form.scope)
    if standing.facts.state in TERMINAL:
        raise refused(PROJECT_NOT_TERMINAL)
    upload = _usable_deposit(session, opening.upload_id, act)
    if upload is None:
        raise NotFoundError(NOT_FOUND)
    if upload.purpose != IMPORT:
        mismatch = FieldError("/upload_id", UPLOAD_PURPOSE_MISMATCH)
        raise UnprocessableError(VALIDATION_FAILED, fields=(mismatch,))
    target = _aimed(session, standing, opening.structure_id)
    judged = FormJudgment(partial(form.judge, session, target), form.judged_first)
    judge_import(session, standing, confirmer.viewer, judged)
    if head is None:
        # The storage lost the file of a deposit its row still names: it is no deposit any more.
        raise NotFoundError(NOT_FOUND)
    form.judge_header(session, head.parsed)
    row = _inserted(session, _opened(opening, upload, target, standing, act.at))
    payload = {IMPORT_KEY: str(row.id)}
    if target.revision_id is not None:
        payload[REVISION_KEY] = str(target.revision_id)
    # The analysis writes nothing of the project: its task names no project, and suspends nothing.
    row.task_id = submit(session, queue, "import_analysis", act.author, payload)
    session.flush()
    return _view(session, row, confirmer.viewer, _read(session, row, act.at))


def _opened(
    opening: ImportOpening,
    upload: FileUpload,
    target: ImportTarget,
    standing: Standing,
    at: datetime,
) -> ImportReport:
    """Give an import ``analysing`` opened at ``at``, of its deposit, aiming at its target.

    It writes in the current revision, none yet when its application creates it; an import of the
    project alone keeps the period it was given.
    """
    of_project = standing.scope == "project"
    return ImportReport(
        id=new_id(),
        project_id=opening.project_id,
        kind=opening.kind,
        filename=upload.filename,
        upload_id=upload.id,
        object_key=upload.object_key,
        structure_id=target.structure_id,
        revision_id=None if of_project else standing.facts.current_revision_id,
        period_from=opening.period_from if of_project else None,
        period_to=opening.period_to if of_project else None,
        status="analysing",
        requested_by=upload.uploaded_by,
        created_at=at,
    )


def _inserted(session: Session, row: ImportReport) -> ImportReport:
    """Write an import opened; a deposit serves one import (404 for a deposit used already).

    An opening of the same deposit on another project, which another lock held, is told by the
    index.
    """
    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError as error:
        if unique_violated(error) != UPLOAD_INDEX:
            raise
        raise NotFoundError(NOT_FOUND) from None
    return row


def _task_failed(session: Session, task_id: UUID | None) -> bool:
    """Tell whether the last task of an import failed."""
    if task_id is None:
        return False
    status = session.scalar(select(BackgroundTask.status).where(BackgroundTask.id == task_id))
    return status == "failed"


def _read(session: Session, row: ImportReport, now: datetime) -> str:
    """Give the state an import is read in at ``now``."""
    failed = _task_failed(session, row.task_id)
    return status_read(row.status, row.expires_at, now, task_failed=failed)


def _view(session: Session, row: ImportReport, viewer: Viewer | None, read: str) -> ImportView:
    """Describe an import as it is ``read``, with the commands of ``viewer`` if one is given.

    The commands are listed to the holder of the permission of the kind (WF-IHM-0090). Without a
    ``viewer``, as in a list, the report is not read — the row was loaded without it — and the view
    carries none (US-3250).
    """
    commands: tuple[CommandAvailability, ...] = ()
    form = _format_named(row.kind)
    if viewer is not None and form is not None and form.permission in viewer.permissions:
        contributor = contributor_kind(session, row.project_id, viewer.user_id) is not None
        commands = tuple(
            CommandAvailability(command, missing)
            for command, missing in commands_of(read, row.report, contributor=contributor)
        )
    return ImportView(
        import_id=row.id,
        kind=row.kind,
        filename=row.filename,
        structure_id=row.structure_id,
        revision_id=row.revision_id,
        period_from=row.period_from,
        period_to=row.period_to,
        status=read,
        created_at=row.created_at,
        expires_at=expiry_read(read, row.expires_at),
        report=None if viewer is None else row.report,
        task_id=row.task_id,
        commands=commands,
    )


def read_import(
    session: Session, project_id: UUID, import_id: UUID, viewer: Viewer, now: datetime
) -> ImportView:
    """Read an import of a project, its expiry judged at the reading (``getImport``); or 404.

    An import of a kind ``viewer`` does not consult is refused as an unknown one (404, #2473).
    """
    row = found_import(session, project_id, import_id, lock=False)
    if not _readable(row.kind, viewer):
        raise NotFoundError(NOT_FOUND)
    return _view(session, row, viewer, _read(session, row, now))


def list_imports(
    session: Session, project_id: UUID, viewer: Viewer, page: ImportPage, now: datetime
) -> ImportList:
    """List a page of the imports of a project, the latest opened first (``listImports``).

    Only the imports of the kinds ``viewer`` consults are listed, and counted (#2473). Each is read
    as ``getImport`` reads it, its expiry and the end of its task judged at ``now``; its report is
    not loaded, a list not saying it (US-3250).
    """
    limit, offset = page.limit, page.offset
    kinds = [kind for kind in formats() if _readable(kind, viewer)]
    kept = (ImportReport.project_id == project_id) & ImportReport.kind.in_(kinds)
    total = session.scalar(select(func.count()).select_from(ImportReport).where(kept)) or 0
    rows = session.execute(
        select(ImportReport, BackgroundTask.status)
        .options(defer(ImportReport.report))
        .outerjoin(BackgroundTask, BackgroundTask.id == ImportReport.task_id)
        .where(kept)
        .order_by(ImportReport.created_at.desc(), ImportReport.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    views = [
        _view(
            session,
            row,
            None,
            status_read(row.status, row.expires_at, now, task_failed=status == "failed"),
        )
        for row, status in rows
    ]
    return ImportList(views, total)


def abandon_import(
    session: Session, project_id: UUID, import_id: UUID, confirmer: Confirmer, files: Bucket
) -> None:
    """Abandon an import awaiting its decision, its file deleted (``abandonImport``).

    Under the lock of the import, read under it: unknown, or of a kind the caller does not consult
    (404), the permission of its kind and the quality of contributor (403), applied or being
    applied (409 ``import_not_applied``): what it
    wrote is not undone by abandoning it. An import that ended without writing is left as it is,
    its file gone already or left to the purge: abandoning it again changes nothing (204). One
    being analysed is abandoned as well, its analysis then writing nothing (WF-INTF-0080).
    """
    act = confirmer.act
    row = found_import(session, project_id, import_id, lock=True)
    _judge_acting(session, project_id, _format_of(row.kind), confirmer)
    read = _read(session, row, act.at)
    if abandon_lacks(read):
        raise refused(NOT_APPLIED)
    if read == "failed" and row.status in RUNNING:
        # Its task failed without a trace: the row still runs, the file is still there.
        end_unwritten(session, row, files)
        return
    if read in ENDED_WITHOUT_WRITING:
        return
    row.status = "abandoned"
    # An abandoned import keeps an expiry: that of its report, or the instant of its abandonment.
    row.expires_at = row.expires_at or act.at
    session.flush()
    remove_once_committed(session, files, row.object_key)


def _refuse(
    session: Session, row: ImportReport, refusal: ServiceError, files: Bucket
) -> ImportRefused:
    """Pass an import ``refused`` after its analysis: it applies no more, its file goes (I-01)."""
    row.status = "refused"
    row.expires_at = None
    session.flush()
    remove_once_committed(session, files, row.object_key)
    return ImportRefused(refusal)


def apply_import(
    session: Session, means: ImportMeans, project_id: UUID, import_id: UUID, confirmer: Confirmer
) -> UUID | ImportRefused:
    """Judge an import again and deposit the task of its application (``applyImport``).

    Under the lock of the import, read under it, then the lock of the project: unknown (404); the
    reading of its kind (404, #2473), its permission and the quality of contributor (403); an
    import no longer ``analysed`` — applied or being applied, abandoned, expired, failed, refused —
    (409 ``import_awaiting_decision``), the import unchanged; then a report that rejects the whole
    file (409 ``import_file_accepted``), a structure written since the analysis (409
    ``import_structure_unchanged``, US-3210, read under the lock of the project: the task judges it
    again under the lock of the structure), and the conditions of the opening judged again, those
    of the exchanges then those of the kind (409), and the structure aimed at, which the current
    revision may no longer hold (404). A condition that passes — a background task of the project,
    the permission to create the revision the import would create (``PASSING``) — refuses it and
    leaves it ``analysed``, its file kept: it is applied again once the condition holds, without a
    new deposit (WF-ARC-0100, #2475). Any other refuses it for good, as the permission or the
    quality its requester lost since the analysis does (403): another account's refusal leaves it
    as it is, which no one may spoil without the right to apply it. Refused for good, the import is
    ``refused`` and its file deleted once committed (``ImportRefused``); otherwise it passes
    ``applying``, its task deposited in the transaction, which suspends the writes of its revision
    until it ends (``no_background_task_running``, #360).
    """
    act = confirmer.act
    files = means.files
    row = found_import(session, project_id, import_id, lock=True)
    form = _format_of(row.kind)
    read = _read(session, row, act.at)
    try:
        _judge_acting(session, project_id, form, confirmer)
    except ServiceError as refusal:
        if read == "analysed" and row.requested_by == act.author:
            return _refuse(session, row, refusal, files)
        raise
    lacking = apply_lacks(read, row.report)
    if lacking == (AWAITING_DECISION,):
        raise refused(AWAITING_DECISION)
    try:
        if lacking:
            raise refused(lacking[0])
        standing = Standing(project_id, lock_project(session, project_id), form.scope)
        if form.scope == "structure":
            current = standing.facts.current_revision_id
            judge_unchanged(session, row, written_at_request(session, row, current))

        def judge_format() -> None:
            form.judge(session, _applied_target(session, row, standing))

        judge_import(
            session, standing, confirmer.viewer, FormJudgment(judge_format, form.judged_first)
        )
    except ServiceError as refusal:
        if refusal.params.get("missing_condition") in PASSING:
            raise
        return _refuse(session, row, refusal, files)
    payload = {IMPORT_KEY: str(row.id)}
    if form.scope == "structure":
        # The application writes in the current revision, or creates it: it suspends its writes.
        payload[PROJECT] = str(project_id)
    task_id = submit(session, means.queue, "import_apply", act.author, payload)
    row.task_id, row.status = task_id, "applying"
    session.flush()
    return task_id


def set_duration_rule(
    session: Session, queue: TaskQueue, change: RuleChange, confirmer: Confirmer
) -> ImportView:
    """Set the rule of the durations of an import in calendar gap (``setImportDurationRule``).

    Under the lock of the import, read under it: unknown, or of a kind the caller does not consult
    (404); the permission of its kind and the quality of contributor, as for applying it (403); an
    import no longer ``analysed`` (409 ``import_awaiting_decision``), then a report without a
    calendar gap (409 ``import_calendar_gap``), the import unchanged. The rule the report
    was computed under gives the import back as it stands; another sets the report aside and
    deposits a new analysis, under the rule, on what the last one read — the import ``analysing``
    again, without a report nor an expiry, its task the new one (WF-INTF-0080, US-2000). The
    conditions of the state of the project are not judged: the analysis writes nothing, and the
    application judges them again (#2977).
    """
    project_id, rule = change.project_id, change.rule
    act = confirmer.act
    row = found_import(session, project_id, change.import_id, lock=True)
    _judge_acting(session, project_id, _format_of(row.kind), confirmer)
    read = _read(session, row, act.at)
    lacking = rule_lacks(read, row.report)
    if lacking:
        raise refused(lacking[0])
    if rule_of(row.report) == rule:
        return _view(session, row, confirmer.viewer, read)
    payload = {IMPORT_KEY: str(row.id)}
    revision = _analysed_revision(session, row)
    if revision is not None:
        payload[REVISION_KEY] = revision
    row.duration_rule = rule
    row.report = None
    # The new analysis keeps the counter it reads; the one of the last is set aside (US-3210).
    row.structure_lock_version = None
    row.status = "analysing"
    row.analysed_at = None
    row.expires_at = None
    # The analysis writes nothing of the project: its task names no project, as at the opening.
    row.task_id = submit(session, queue, "import_analysis", act.author, payload)
    session.flush()
    return _view(session, row, confirmer.viewer, _read(session, row, act.at))


def _analysed_revision(session: Session, row: ImportReport) -> str | None:
    """Give the revision the last analysis of an import read: the one its opening aimed at."""
    task = None if row.task_id is None else session.get(BackgroundTask, row.task_id)
    if task is not None:
        return task.payload.get(REVISION_KEY)
    return None if row.revision_id is None else str(row.revision_id)


def _applied_target(session: Session, row: ImportReport, standing: Standing) -> ImportTarget:
    """Give what an application would write: the current revision and its structure.

    The structure is that of the current revision, the copy of the one aimed at when the opening
    aimed at the last marked revision, as the task resolves it; the one aimed at when there is no
    current revision yet, the task then creating it.
    """
    if standing.scope != "structure":
        return ImportTarget(row.project_id, None, None)
    current = standing.facts.current_revision_id
    if current is None:
        return ImportTarget(row.project_id, None, row.structure_id)
    return ImportTarget(row.project_id, current, aimed_by(session, row, current))


def run_analysis(session: Session, task: Task, files: Bucket) -> Mapping[str, Any] | None:
    """Analyse the file of an import, in the transaction of its task (``import_analysis``)."""
    return running.analyse(session, task, files, _format_named)


def run_apply(
    session: Session, task: Task, files: Bucket, viewer: Viewer, judge: Judge
) -> Mapping[str, Any] | None:
    """Apply the report of an import, in the transaction of its task (``import_apply``).

    ``viewer`` is its requester as it stands now, whose permissions ``judge`` judges again.
    """
    return running.apply(session, task, files, _format_named, running.Requester(viewer, judge))
