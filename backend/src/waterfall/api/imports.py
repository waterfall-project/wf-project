# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports in two steps (WF-ARC-0100, WF-INTF-0080, WF-INTF-0090).

``uploadFile``, ``openImport``, ``getImport``, ``listImports``, ``abandonImport`` and
``applyImport`` (US-1420/L1); ``setImportDurationRule``, the rule of the durations of a planning
of MS Project in calendar gap, which analyses the import again (US-2000/L2). A file is deposited
whole, written to the storage under ``uploads/<upload_id>`` before its row; an import opens on it,
is analysed by the worker, then applied or abandoned. The storage is asked out of any transaction:
the head of a file is read before the opening is judged, and a file is deleted once the transaction
that ends its import is committed (WF-DAT-0120).

Each operation of a project is guarded by ``RequiresProject`` on the reading of the planning, the
leaf the exchanges are of (FBS-4.3.4): the project, and its imports, exist only for who may
consult them (404). The permission an import of a kind asks — ``planning.write`` for a planning,
the format's — and the quality of contributor are judged by the exchanges with the import itself,
under its lock: an application whose requester lost them since the analysis refuses the import
for good, ``refused``, its file deleted, which a guard ahead of the route could not write
(WF-ARC-0100, #1789). An answer is built before its transaction is committed; a refusal that
leaves the import refused is answered once it is committed.
"""

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import (
    BackgroundTaskRef,
    FileUpload,
    Import,
    ImportApply,
    ImportDetail,
    ImportDurationRule,
    ImportDurationRuleWrite,
    ImportRequest,
    PaginationMeta,
)
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.queries import Offset
from waterfall.api.tasks import task_ref
from waterfall.core.access_roles.interface import Actor, require_project
from waterfall.core.exchanges.interface import (
    KEEP_DATES,
    KEEP_DURATIONS,
    LARGEST_FILE,
    Confirmer,
    ImportMeans,
    ImportOpening,
    ImportRefused,
    ImportView,
    RuleChange,
    abandon_import,
    apply_import,
    deposit,
    head_to_read,
    judge_deposit,
    list_imports,
    open_import,
    read_import,
    set_duration_rule,
)
from waterfall.core.projects.interface import Viewer
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import BadRequestError, PayloadTooLargeError, UnavailableError
from waterfall.platform.identifiers import new_id
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import object_key_of

if TYPE_CHECKING:
    from starlette.types import Message

router = APIRouter(tags=["exchanges"])

CONSULT = "planning.read"
FILE_TOO_LARGE = "FILE_TOO_LARGE"
MALFORMED_REQUEST = "MALFORMED_REQUEST"
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
# What a request that carries a file of an import may weigh besides it: its boundaries and the
# field of its use. Beyond, the file is too large, said before the body is read.
ENVELOPE = 64 * 1024
IMPORTS = "/projects/{project_id}/imports"
IMPORT_PATH = f"{IMPORTS}/{{import_id}}"
READING = [Depends(RequiresProject(CONSULT))]


@dataclass(frozen=True, slots=True)
class Sent:
    """What a deposit carries: the file, its name as the user chose it, and its use."""

    content: bytes
    filename: str | None
    purpose: str


def _bounded(request: Request) -> Request:
    """Give the request whose body is counted as it is read: beyond the bound, 413.

    A body sent in chunks has no length to judge ahead; it is stopped as it overruns what a
    deposit may weigh, before it is all written to disk.
    """
    received = 0

    async def receive() -> Message:
        nonlocal received
        message = await request.receive()
        received += len(message.get("body", b""))
        if received > LARGEST_FILE + ENVELOPE:
            raise PayloadTooLargeError(FILE_TOO_LARGE)
        return message

    return Request(request.scope, receive)


async def sent_file(request: Request) -> Sent:
    """Read the file a deposit carries, and its use; one too large is refused unread (413).

    A body that is no form, or a form without the file or its use, is refused by the deposit
    itself (422); a form that cannot be read, as a request that cannot be (400). The body is
    bounded as it is read, with or without a length announced.
    """
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > LARGEST_FILE + ENVELOPE:
        raise PayloadTooLargeError(FILE_TOO_LARGE)
    try:
        async with _bounded(request).form(max_files=1, max_fields=1) as form:
            purpose = form.get("purpose")
            sent = form.get("file")
            if not isinstance(sent, UploadFile):
                return Sent(b"", None, purpose if isinstance(purpose, str) else "")
            # One byte beyond the bound says the file is too large, without reading it whole.
            content = await sent.read(LARGEST_FILE + 1)
            return Sent(content, sent.filename, purpose if isinstance(purpose, str) else "")
    except MultiPartException:
        raise BadRequestError(MALFORMED_REQUEST) from None


@router.post("/file-uploads", operation_id="uploadFile", status_code=201)
def post_file_upload(
    account: Caller, sent: Annotated[Sent, Depends(sent_file)], services: ServicesOf
) -> FileUpload:
    """Deposit a file for an import, in one piece, for twenty-four hours (WF-DAT-0120).

    Refused before anything is written: a backup, deposited by parts (422 ``/purpose``), a file
    beyond 10 MiB (413), an empty one or one without a name (422 ``/file``). The file is written to
    the storage, then its deposit recorded: a deposit is recorded once its file is there.
    """
    judge_deposit(sent.purpose, sent.filename, len(sent.content))
    filename = sent.filename or ""
    upload_id = new_id()
    key = object_key_of(upload_id)
    services.backups.put(key, sent.content)
    try:
        with services.database.transaction() as session:
            kept = deposit(
                session, upload_id, filename, len(sent.content), Act(account.user_id, utc_now())
            )
            return FileUpload.model_validate(
                {
                    "upload_id": kept.upload_id,
                    "purpose": "import",
                    "filename": kept.filename,
                    "size_bytes": kept.size_bytes,
                    "uploaded_at": kept.uploaded_at,
                    "expires_at": kept.expires_at,
                    "backup_taken_at": None,
                }
            )
    except BaseException:
        # No row keeps the object: it goes (a process that dies between the two leaves it to the
        # purge, US-1420/L2).
        with suppress(UnavailableError, MissingObjectError):
            services.backups.remove(key)
        raise


def confirmer_of(actor: Actor) -> Confirmer:
    """Give the caller as the exchanges judge it: now, its permissions, and its evaluation."""

    def judge(session: Session, project_id: UUID, permission: str) -> None:
        require_project(session, actor, project_id, permission)

    return Confirmer(Act(actor.user_id, utc_now()), Viewer(actor.user_id, actor.permissions), judge)


def _commands(view: ImportView) -> list[dict[str, Any]]:
    return [
        {
            "command": command.command,
            "is_available": command.is_available,
            "missing_conditions": list(command.missing_conditions),
        }
        for command in view.commands
    ]


def _listed(view: ImportView) -> dict[str, Any]:
    """Give what the list says of an import: its opening and where it stands."""
    return {
        "import_id": view.import_id,
        "kind": view.kind,
        "filename": view.filename,
        "structure_id": view.structure_id,
        "revision_id": view.revision_id,
        "period_from": view.period_from,
        "period_to": view.period_to,
        "status": view.status,
        "created_at": view.created_at,
        "expires_at": view.expires_at,
    }


def _report(view: ImportView) -> dict[str, Any] | None:
    """Give the report of an import, its unit constants and its calendar gap nil without them.

    The analysis of a planning of MS Project writes both (US-2000/L2). A report analysed before
    ``unit_constants`` (#2580) or ``calendar_gap`` (#2977), or by the code that precedes them during
    an update (WF-DAT-0140), lacks a key the contract requires, as the reports of the other kinds
    do: it is read as the constants and the calendars of the file not differing.
    """
    if view.report is None:
        return None
    return {"unit_constants": None, "calendar_gap": None, **view.report}


def detailed(session: Session, view: ImportView) -> ImportDetail:
    """Describe an import as reading it does: with its report, its last task and its commands."""
    task = session.get_one(BackgroundTask, view.task_id)
    return ImportDetail.model_validate(
        {
            **_listed(view),
            "report": _report(view),
            "task": task_ref(task),
            "available_commands": _commands(view),
        }
    )


@router.get(IMPORTS, operation_id="listImports", dependencies=READING, response_model=None)
def get_imports(
    project_id: UUID,
    session: Transaction,
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> dict[str, Any]:
    """Give a page of the imports of a project, the latest opened first (WF-INTF-0080)."""
    read = list_imports(session, project_id, limit, offset, utc_now())
    meta = PaginationMeta(limit=limit, offset=offset, total=read.total)
    return {
        "items": [
            Import.model_validate(_listed(view)).model_dump(mode="json", exclude_unset=True)
            for view in read.views
        ],
        "meta": meta.model_dump(),
    }


@router.post(
    IMPORTS,
    operation_id="openImport",
    dependencies=READING,
    status_code=202,
    response_model_exclude_unset=True,
)
def post_import(
    project_id: UUID, body: ImportRequest, actor: Acting, services: ServicesOf
) -> ImportDetail:
    """Open an import of a deposited file, and deposit its analysis for the worker (202).

    The head of the file is read from the storage before the transaction that judges the opening
    under the lock of the project, which does not wait for the storage; it judges the deposit again.
    """
    confirmer = confirmer_of(actor)
    opening = ImportOpening(
        project_id,
        body.kind.value,
        body.upload_id.root,
        None if body.structure_id is None else body.structure_id.root,
        None if body.period_from is None else body.period_from.root,
        None if body.period_to is None else body.period_to.root,
    )
    with services.database.transaction() as session:
        where = head_to_read(session, opening.upload_id, opening.kind, confirmer.act)
    head = None
    if where is not None:
        try:
            head = services.backups.head(where.object_key, where.length)
        except MissingObjectError:
            head = None
    with services.database.transaction() as session:
        view = open_import(session, services.queue, opening, head, confirmer)
        return detailed(session, view)


@router.get(
    IMPORT_PATH,
    operation_id="getImport",
    dependencies=READING,
    response_model_exclude_unset=True,
)
def get_import(
    project_id: UUID, import_id: UUID, actor: Acting, session: Transaction
) -> ImportDetail:
    """Give an import, its report in codes, its last task and the commands of its reader."""
    viewer = Viewer(actor.user_id, actor.permissions)
    return detailed(session, read_import(session, project_id, import_id, viewer, utc_now()))


@router.delete(IMPORT_PATH, operation_id="abandonImport", dependencies=READING, status_code=204)
def delete_import(
    project_id: UUID, import_id: UUID, actor: Acting, session: Transaction, services: ServicesOf
) -> Response:
    """Abandon an import: the project unchanged, its file deleted once committed (204)."""
    abandon_import(session, project_id, import_id, confirmer_of(actor), services.backups)
    return Response(status_code=204)


@router.post(
    f"{IMPORT_PATH}/apply",
    operation_id="applyImport",
    dependencies=READING,
    status_code=202,
    response_model_exclude_unset=True,
)
def post_application(
    project_id: UUID,
    import_id: UUID,
    body: ImportApply,
    actor: Acting,
    services: ServicesOf,
) -> BackgroundTaskRef:
    """Deposit the application of an import for the worker, judged again (202).

    Refused for good — the report rejects the file, a condition of the opening lacks, the requester
    lost the right to apply it —, the import is written ``refused`` and committed, then the refusal
    is answered (WF-ARC-0100).
    """
    del body
    means = ImportMeans(services.queue, services.backups)
    with services.database.transaction() as session:
        outcome = apply_import(session, means, project_id, import_id, confirmer_of(actor))
        answer = (
            outcome
            if isinstance(outcome, ImportRefused)
            else task_ref(session.get_one(BackgroundTask, outcome))
        )
    if isinstance(answer, ImportRefused):
        raise answer.refusal
    return answer


@router.put(
    f"{IMPORT_PATH}/duration-rule",
    operation_id="setImportDurationRule",
    dependencies=READING,
    response_model=None,
)
def put_duration_rule(
    project_id: UUID,
    import_id: UUID,
    body: ImportDurationRuleWrite,
    actor: Acting,
    services: ServicesOf,
) -> JSONResponse:
    """Set the rule of the durations of an import in calendar gap (WF-INTF-0080).

    Another rule than the report's analyses the import again, its task deposited for the worker
    (202); the same one gives the import back as it stands (200). The answer is built before the
    transaction is committed.
    """
    rule = KEEP_DATES if body.duration_rule is ImportDurationRule.keep_dates else KEEP_DURATIONS
    change = RuleChange(project_id, import_id, rule)
    with services.database.transaction() as session:
        view = set_duration_rule(session, services.queue, change, confirmer_of(actor))
        answer = detailed(session, view).model_dump(mode="json", by_alias=True, exclude_unset=True)
    return JSONResponse(answer, status_code=202 if view.status == "analysing" else 200)
