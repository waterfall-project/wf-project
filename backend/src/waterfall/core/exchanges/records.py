# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rows of the imports, as the requests and the tasks read and end them, private to the module.

An import is found in its project, or not at all (404): an import of another project does not
exist for the caller. It is locked before it is read when a write depends on its state. Its file
is deleted from the storage once the transaction that ends it is committed, never before: an
object is never deleted for a row a failed transaction keeps (WF-DAT-0120, as EP-03 deletes its
deposits); a storage out of reach then leaves the file to the purge (US-1420/L2).
"""

from typing import TYPE_CHECKING

from sqlalchemy import event, select, update

from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.revisions.interface import aimed_structure, structure_in_revision
from waterfall.platform.errors import NotFoundError, UnavailableError
from waterfall.platform.logs import get_logger
from waterfall.platform.storage import MissingObjectError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.storage import Bucket

NOT_FOUND = "NOT_FOUND"

logger = get_logger(__name__)


def found_import(
    session: Session, project_id: UUID, import_id: UUID, *, lock: bool
) -> ImportReport:
    """Give an import of a project, locked if asked, read under the lock; or refuse (404)."""
    query = select(ImportReport).where(
        ImportReport.id == import_id, ImportReport.project_id == project_id
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = session.scalars(query).one_or_none()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    return row


def aimed_by(session: Session, row: ImportReport, revision_id: UUID) -> UUID:
    """Give the structure of a revision an import writes: the one its opening aimed at.

    Or its copy, when the opening aimed at the last marked revision; the main one when the
    project had no revision then. A structure the revision no longer holds is not found (404).
    """
    if row.structure_id is None:
        found = aimed_structure(session, row.project_id, revision_id, None)
    else:
        found = structure_in_revision(session, row.project_id, row.structure_id, revision_id)
    if found is None:
        raise NotFoundError(NOT_FOUND)
    return found


def locked_import(session: Session, import_id: UUID) -> ImportReport | None:
    """Lock an import a task names, then read it under the lock; ``None`` if it is gone."""
    return session.scalars(
        select(ImportReport)
        .where(ImportReport.id == import_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()


def remove_once_committed(session: Session, files: Bucket, key: str) -> None:
    """Delete the file of an import from the storage once the transaction of ``session`` commits.

    Not if it is rolled back. A storage out of reach then, or a file gone already, is said in the
    journal of the service and leaves nothing to undo: the transaction is committed.
    """

    def remove(_session: Session) -> None:
        try:
            files.remove(key)
        except UnavailableError, MissingObjectError:
            logger.warning("import.file_kept", object_key=key)

    event.listen(session, "after_commit", remove, once=True)


def end_unwritten(session: Session, row: ImportReport, files: Bucket) -> None:
    """Write ``failed`` an import whose task failed without a trace, its file deleted at the commit.

    The caller holds the lock of the row: its report expires no more, and its file goes.
    """
    row.status = "failed"
    row.expires_at = None
    session.flush()
    remove_once_committed(session, files, row.object_key)


def end_without_writing(
    session: Session, import_id: UUID, status: str, ended: str, files: Bucket
) -> None:
    """Write that an import ``status`` ended ``ended`` — failed or refused —, its file deleted.

    Written after the work of its task is undone: the import is passed on only if it still stands
    where the task found it; its report expires no more, and its file goes once committed.
    """
    key = session.scalar(
        update(ImportReport)
        .where(ImportReport.id == import_id, ImportReport.status == status)
        .values(status=ended, expires_at=None)
        .returning(ImportReport.object_key)
    )
    if key is not None:
        remove_once_committed(session, files, key)
