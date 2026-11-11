# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The purge of the exchanges: the imports expired, the deposits expired, the exports old.

``waterfall-worker purge`` calls ``purge`` in its transaction (EP-06, "La purge"): it moves to
``expired`` the imports ``analysed`` whose report expired, and to ``failed`` those whose task failed
without leaving its trace (the attempts spent, never abandoned) — the file of either goes —; it
deletes the rows of the deposits expired — those of EP-03 included, a deposit left in parts being
aborted —, sparing the object of a deposit an import still keeps; it marks consumed the results of
the exports of more than twenty-four hours, their file going; and it gives what the storage must
lose, to which it adds what no row designates any more: the old objects of ``uploads/`` past the
life of a deposit, those of ``exports/`` past the life of an export, and the deposits in parts of
``uploads/`` left open past the life of a deposit (WF-DAT-0120-A). The worker hands all that to
``remove_purged`` once the transaction is validated, as EP-03 deletes its deposits: an object is
never deleted for a row a failed transaction keeps.

A storage that cannot be cleaned leaves what it holds to the next pass: the sweep of the prefixes
finds again every object, and every deposit in parts, whose row is gone — the deposit in parts
not completed is no object, so it is listed apart. The sweep is bounded by ``SWEEP_LIMIT`` for
each kind, the rest going to the next pass. The bound counts only what no row designates: the
listing passes over the old objects a row still names — those of the imports that keep their file,
which may be older than a day (#2533) —, so that a great many of them, first in the order of the
keys, never hide the strays beyond them.

The storage tells the age of an object by its own clock, the purge judges by that of the
application: a drift of a few minutes between them moves the term of a sweep by as much, which no
object of a day needs to mind; an object younger than the term is never swept.
"""

from dataclasses import dataclass
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING, Any

from sqlalchemy import ARRAY, Text, Uuid, any_, bindparam, delete, select, update

from waterfall.core.exchanges.interface.exports import EXPORTS_PREFIX, has_file
from waterfall.core.exchanges.states import FILE_KEPT, RUNNING
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import LIFETIME, FileUpload
from waterfall.platform.uploads import PREFIX as UPLOADS_PREFIX

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from datetime import datetime

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session
    from sqlalchemy.sql.expression import SQLColumnExpression

    from waterfall.platform.storage import Bucket

# How long the file of an export waits to be downloaded (WF-DAT-0120-A).
EXPORT_LIFETIME = timedelta(hours=24)

# How many old objects, and how many deposits in parts, a pass lists at most from each prefix.
SWEEP_LIMIT = 10_000

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Purged:
    """What the storage loses once a purge is validated.

    ``objects`` the keys of the files of the imports and of the exports, and of the deposits
    completed; ``deposits`` the key and the deposit of each deposit left in parts, to abort.
    """

    objects: tuple[str, ...] = ()
    deposits: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Stored:
    """The old objects of the prefixes the purge sweeps, listed before its transaction.

    ``uploads`` those past the life of a deposit, ``exports`` those past the life of an export,
    ``parts`` the key and the deposit of the deposits in parts of ``uploads/`` open past the life
    of a deposit: candidates, which the purge keeps when a row designates them.
    """

    uploads: tuple[str, ...] = ()
    exports: tuple[str, ...] = ()
    parts: tuple[tuple[str, str], ...] = ()


def stored_before(bucket: Bucket, now: datetime, session: Session | None = None) -> Stored:
    """List the objects of ``uploads/`` and of ``exports/`` old enough to be swept at ``now``.

    Listed before the transaction of the purge, never under its lock: an object is written before
    its row, under an identifier that is new, so an object listed as more than a day old cannot be
    named by a row created between the listing and the transaction; and one a request writes
    later is younger than the term. With a ``session``, read without a lock, what a row names at
    the listing is left out of it, and ``SWEEP_LIMIT`` counts the rest alone (#2533). A deposit
    expired at ``now`` names nothing; an import or an export the pass ends gives its file itself,
    and what a row named and no longer does is swept by the next pass. A storage out of reach
    raises ``UnavailableError``.
    """
    if session is None:
        uploads = exports = parts = None
    else:
        uploads, exports = partial(_named_uploads, session, now), partial(_named_exports, session)
        parts = partial(_named_parts, session)
    upload_term, export_term = now - LIFETIME, now - EXPORT_LIFETIME
    return Stored(
        uploads=tuple(bucket.keys_before(UPLOADS_PREFIX, upload_term, SWEEP_LIMIT, uploads)),
        exports=tuple(bucket.keys_before(EXPORTS_PREFIX, export_term, SWEEP_LIMIT, exports)),
        parts=tuple(bucket.deposits_before(UPLOADS_PREFIX, upload_term, SWEEP_LIMIT, parts)),
    )


def purge(session: Session, now: datetime, stored: Stored | None = None) -> Purged:
    """Purge the rows that expired at ``now``, and give what the storage must lose.

    ``stored`` the old objects of the storage to sweep; none, none is swept. The imports go first,
    so that a deposit is judged by the state its import stands in once the pass is over.
    """
    swept = stored or Stored()
    objects = [*_imports_ended(session, now), *_exports_old(session, now)]
    deposited, parts = _deposits_expired(session, now)
    strays, stray_parts = _strays(session, now, swept)
    objects += [*deposited, *strays]
    parts += stray_parts
    return Purged(tuple(dict.fromkeys(objects)), tuple(dict.fromkeys(parts)))


def _imports_ended(session: Session, now: datetime) -> list[str]:
    """Pass ``expired`` the imports whose report expired, ``failed`` those whose task failed.

    A task that failed without a trace leaves its import running, the attempts spent: the import
    reads ``failed``, and the purge writes it so, its report expiring no more. Each statement locks
    the rows it writes, and re-reads them under the lock: an import applied in the meantime is not
    touched.
    """
    expired = session.scalars(
        update(ImportReport)
        .where(ImportReport.status == "analysed", ImportReport.expires_at <= now)
        .values(status="expired")
        .returning(ImportReport.object_key)
    ).all()
    failed_tasks = select(BackgroundTask.id).where(BackgroundTask.status == "failed")
    failed = session.scalars(
        update(ImportReport)
        .where(ImportReport.status.in_(RUNNING), ImportReport.task_id.in_(failed_tasks))
        .values(status="failed", expires_at=None)
        .returning(ImportReport.object_key)
    ).all()
    return [*expired, *failed]


def _exports_old(session: Session, now: datetime) -> list[str]:
    """Mark consumed the results of the exports that succeeded long ago, and give their files."""
    rows = session.scalars(
        select(BackgroundTask)
        .where(
            BackgroundTask.kind == "export",
            BackgroundTask.status == "succeeded",
            BackgroundTask.finished_at <= now - EXPORT_LIFETIME,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    keys: list[str] = []
    for row in rows:
        if row.result is not None and has_file(row.result):
            keys.append(row.result["object_key"])
            row.result = {**row.result, "consumed": True}
    session.flush()
    return keys


def _deposits_expired(session: Session, now: datetime) -> tuple[list[str], list[tuple[str, str]]]:
    """Delete the deposits expired; give their objects, and the deposits in parts to abort.

    The object of a deposit an import still keeps is spared: it is the import's, which deletes it
    at its end.
    """
    gone = session.execute(
        delete(FileUpload)
        .where(FileUpload.expires_at <= now)
        .returning(FileUpload.id, FileUpload.object_key, FileUpload.deposit)
    ).all()
    held = set(
        session.scalars(
            select(ImportReport.upload_id).where(
                _among(ImportReport.upload_id, [each.id for each in gone], Uuid()),
                ImportReport.status.in_(FILE_KEPT),
            )
        )
    )
    objects: list[str] = []
    parts: list[tuple[str, str]] = []
    for each in gone:
        if each.deposit is not None:
            parts.append((each.object_key, each.deposit))
        elif each.id not in held:
            objects.append(each.object_key)
    return objects, parts


def _among(
    column: SQLColumnExpression[Any], values: Iterable[Any], kind: Any
) -> ColumnElement[bool]:
    """Give the condition that a column is one of the values, as one array parameter."""
    return column == any_(bindparam("values", list(values), type_=ARRAY(kind)))


def _strays(
    session: Session, now: datetime, stored: Stored
) -> tuple[list[str], list[tuple[str, str]]]:
    """Give the old objects and the deposits in parts that no row designates (#2479, #2484).

    Left by a process that stopped mid-way, or by a storage out of reach at the last pass. Under
    ``uploads/``, an object that no deposit and no import keeping its file names, and a deposit in
    parts that no deposit names; under ``exports/``, an object that no task whose result is not
    consumed names.
    """
    left: list[tuple[str, str]] = []
    if stored.parts:
        kept = _named_parts(session, stored.parts)
        left = [each for each in stored.parts if each not in kept]
    strays: list[str] = []
    if stored.uploads:
        named = _named_uploads(session, now, stored.uploads)
        strays += [key for key in stored.uploads if key not in named]
    if stored.exports:
        named = _named_exports(session, stored.exports)
        strays += [each for each in stored.exports if each not in named]
    return strays, left


def _named_parts(session: Session, parts: Sequence[tuple[str, str]]) -> set[tuple[str, str]]:
    """Give, among deposits in parts of ``uploads/``, those a deposit names."""
    return {
        (each.object_key, each.deposit)
        for each in session.execute(
            select(FileUpload.object_key, FileUpload.deposit).where(
                _among(FileUpload.object_key, [key for key, _ in parts], Text())
            )
        )
    }


def _named_uploads(session: Session, now: datetime, keys: Sequence[str]) -> set[str]:
    """Give, among keys of ``uploads/``, those a deposit or an import keeping its file names.

    A deposit expired at ``now`` names nothing: the purge deletes it, and one left open gives no
    object of its own, but an object its storage may have completed all the same.
    """
    named = set(
        session.scalars(
            select(FileUpload.object_key).where(
                _among(FileUpload.object_key, keys, Text()), FileUpload.expires_at > now
            )
        )
    )
    return named | set(
        session.scalars(
            select(ImportReport.object_key).where(
                _among(ImportReport.object_key, keys, Text()),
                ImportReport.status.in_(FILE_KEPT),
            )
        )
    )


def _named_exports(session: Session, keys: Sequence[str]) -> set[str]:
    """Give, among keys of ``exports/``, those a task whose result is not consumed names."""
    key = BackgroundTask.result["object_key"].astext
    return set(
        session.scalars(
            select(key).where(
                BackgroundTask.kind == "export",
                _among(key, keys, Text()),
                BackgroundTask.result["consumed"].astext.is_distinct_from("true"),
            )
        )
    )


def remove_purged(bucket: Bucket, purged: Purged) -> None:
    """Delete from the storage what a purge validated gave, after its transaction.

    An object gone already is no fault, nor a deposit in parts closed already. A storage out of
    reach stops the deletion, said in the journal: the rows are gone, and the sweep of the prefixes
    finds the objects, and the deposits in parts, again at the next pass.
    """
    try:
        for key in purged.objects:
            bucket.remove(key)
        for key, deposit in purged.deposits:
            try:
                bucket.abort_parts(key, deposit)
            except MissingObjectError:
                logger.info("purge.deposit_closed", object_key=key)
    except UnavailableError:
        logger.warning("purge.storage_unavailable")
