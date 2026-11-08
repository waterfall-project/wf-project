# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of a project: the history, a revision read, opened, abandoned; the partitions.

A project bears at most one current revision (WF-REV-0010). It is opened under the lock of the
project, refused while another is current (409 ``no_current_revision``, #1797) — the unique
partial index on ``draft`` is the second rampart, which decides between two openings the lock
would not have kept apart —, and on a terminal project (``project_not_terminal``). It retains the
current year for its reference year, and is the copy of the last marked revision of the project
(``copy_revision(session, source, target)``), which each epic extends table by table by
``register_copy``: the structures here, EP-06 the tasks, EP-07 the lines and the images, EP-08 the
structures it adds; the first revision of a project copies nothing, and is born with its main
structure alone (WF-REV-0100). Its opening is the fact that moves the project from Created to
Pricing (``advance``, US-0980/L1).

A current revision is abandoned under its own lock, at the counter read (412), refused once marked
(409 ``revision_draft``): the project names no current revision any more, the revision and its
rows are deleted (WF-DAT-0010), and ``revision_abandon`` is inscribed in the journal
(WF-SEC-0030). A write in a revision is refused once it is marked (``revision_draft``). The locks
are taken in one order: the revision, then its project — never the project before the revision.

The partitions of the revised tables are created in the transaction of the creation of the
project, by the function of the owner of the tables (``create_project_partitions``, WF-DAT-0050):
the role of the service may execute it, and holds no other right of DDL.

Declared by US-0910/L1, which fills the partitions; US-0960 fills the rest. ``load_revision``
opens a revision of the witness under the identifier it imposes, by the very rules of the opening
(#1402), at the instant of the act it is given: the chronology's, for the witness.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.projects.interface import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    CommandAvailability,
    advance,
    contributor_kind,
    lock_project,
    no_background_task_running,
    project_facts,
    require_project_manager,
    set_current_revision,
)
from waterfall.core.resource_settings.interface import share_reference
from waterfall.core.revisions.commands import (
    NO_BACKGROUND_TASK_RUNNING,
    NO_CURRENT_REVISION,
    REVISION_DRAFT,
    revision_commands,
)
from waterfall.core.revisions.interface.closing import close_revision
from waterfall.core.revisions.interface.reference import reference_correctable
from waterfall.core.revisions.interface.shared import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    found_revision,
    inscribe_revision,
    refuse,
)
from waterfall.core.revisions.interface.structures import (
    copy_structures,
    create_main_structure,
    delete_structures,
)
from waterfall.core.revisions.registry import Registry
from waterfall.core.revisions.states import state_of
from waterfall.core.revisions.tables import Revision
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.errors import NotFoundError, PreconditionFailedError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import ProjectFacts, Viewer
    from waterfall.platform.audit import Act

# The two statuses of a revision, as the contract says them (``RevisionStatus``).
type RevisionStatus = Literal["draft", "marked"]

# The unique partial index of the current revision of a project (migration of its tables).
DRAFT_INDEX = "uq_revision_draft"


@dataclass(frozen=True, slots=True)
class RevisionView:
    """A revision as it is read: its attributes, its commands for the reader, its audit columns.

    The rates are those of the project, which a current revision follows until its marking; a
    marked one keeps those of its marking once EP-07 keeps them (WF-REV-0030). The authors are the
    identifiers of accounts, or ``None`` for the platform: the API names them.
    """

    revision_id: UUID
    project_id: UUID
    status: str
    version_name: str | None
    description: str | None
    marked_at: datetime | None
    reference_year: int
    is_reference: bool
    inflation_rate: Decimal
    win_probability: Decimal
    source_revision_id: UUID | None
    source_version_name: str | None
    commands: tuple[CommandAvailability, ...]
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class RevisionFilters:
    """What the history keeps: the statuses named, and a text its names or descriptions hold."""

    statuses: frozenset[str] | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class RevisionPage:
    """Which revisions of the history are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class RevisionList:
    """A page of the history, and the number of revisions the filters keep."""

    revisions: list[RevisionView]
    total: int


@dataclass(frozen=True, slots=True)
class RevisionToAbandon:
    """The revision an abandonment names, and the counter its caller read."""

    revision_id: UUID
    lock_version: int


@dataclass(frozen=True, slots=True)
class RevisionCopy:
    """A copy of a marked revision into the new current one, in the transaction of its creation.

    ``identifiers`` maps the identifier of each row copied to that of its copy, table after
    table: a table copied later finds there the copy of the row it names (a task, its structure).
    The copies bear the stamp of the creation of the revision, its author and its instant.
    """

    session: Session
    project_id: UUID
    source: UUID
    target: UUID
    at: datetime
    author: UUID | None
    identifiers: dict[UUID, UUID]


# The copies a revision opened from a marked one makes, table after table, in the order of their
# registration: a module registers its copy after those of the tables its rows name, whose copies it
# finds in ``RevisionCopy.identifiers`` (EP-04, "Modules").
_COPIES: Registry[Callable[[RevisionCopy], None]] = Registry("revisions.copy")


def register_copy(copier: Callable[[RevisionCopy], None]) -> Callable[[], None]:
    """Add the copy of a table after those registered, and give its withdrawal; refused if held.

    A module registers its copy at the import of its interface, which imports this one first: it
    comes after the structures', and after the copies of the modules it imports.
    """
    return _COPIES.register(copier)


register_copy(copy_structures)


def create_project_partitions(session: Session, project_id: UUID) -> None:
    """Create the partitions of a project in each revised table, in the transaction of ``session``.

    A project that has them already is refused by the database, which raises.
    """
    session.execute(select(func.create_project_partitions(project_id)))


def current_revision(session: Session, project_id: UUID) -> UUID | None:
    """Give the current revision of a project, ``None`` if it has none (WF-REV-0010)."""
    return session.scalar(
        select(Revision.id).where(Revision.project_id == project_id, Revision.status == "draft")
    )


def reference_year_of(session: Session, revision_id: UUID) -> int:
    """Give the year of reference a revision prices its lines at (WF-DEV-0030); or 404."""
    year = session.scalar(select(Revision.reference_year).where(Revision.id == revision_id))
    if year is None:
        raise NotFoundError(NOT_FOUND)
    return year


def revisions_present(session: Session, revision_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of the identifiers given, those of the revisions that exist: the witness's question."""
    if not revision_ids:
        return frozenset()
    return frozenset(session.scalars(select(Revision.id).where(Revision.id.in_(revision_ids))))


def _criteria(project_id: UUID, filters: RevisionFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [Revision.project_id == project_id]
    if filters.statuses is not None:
        criteria.append(Revision.status.in_(filters.statuses))
    if filters.search is not None:
        criteria.append(
            or_(
                contains(Revision.version_name, filters.search),
                contains(Revision.description, filters.search),
            )
        )
    return criteria


def _views(
    session: Session, rows: list[Revision], project_id: UUID, viewer: Viewer
) -> list[RevisionView]:
    """Describe revisions of a project, with their source's name and their commands.

    Whether a background task writes in the project is the project's: read once for them all.
    """
    project = project_facts(session, project_id)
    idle = no_background_task_running(session, project_id)
    correctable = reference_correctable(session, project_id)
    kind = contributor_kind(session, project_id, viewer.user_id)
    sources = {row.source_revision_id for row in rows if row.source_revision_id is not None}
    names: dict[UUID, str | None] = {
        row[0]: row[1]
        for row in session.execute(
            select(Revision.id, Revision.version_name).where(Revision.id.in_(sources))
        )
    }
    return [
        RevisionView(
            revision_id=row.id,
            project_id=row.project_id,
            status=row.status,
            version_name=row.version_name,
            description=row.description,
            marked_at=row.marked_at,
            reference_year=row.reference_year,
            is_reference=row.is_reference,
            inflation_rate=project.inflation_rate,
            win_probability=project.win_probability,
            source_revision_id=row.source_revision_id,
            source_version_name=(
                None if row.source_revision_id is None else names.get(row.source_revision_id)
            ),
            commands=tuple(
                CommandAvailability(command, missing)
                for command, missing in revision_commands(
                    viewer.permissions,
                    kind,
                    project.state,
                    state_of(
                        session, row.id, row.status, no_task_running=idle, correctable=correctable
                    ),
                )
            ),
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
            lock_version=row.lock_version,
        )
        for row in rows
    ]


def list_revisions(
    session: Session,
    project_id: UUID,
    viewer: Viewer,
    filters: RevisionFilters,
    page: RevisionPage,
) -> RevisionList:
    """List the revisions of a project, the latest first, filtered (``listRevisions``, WF-REV-0070).

    Each with the attributes of WF-REV-0090 and the marked revision it is the copy of.
    """
    criteria = _criteria(project_id, filters)
    total = session.scalars(select(func.count()).select_from(Revision).where(*criteria)).one()
    rows = session.scalars(
        select(Revision)
        .where(*criteria)
        .order_by(Revision.created_at.desc(), Revision.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return RevisionList(_views(session, list(rows), project_id, viewer), total)


def read_revision(
    session: Session, project_id: UUID, revision_id: UUID, viewer: Viewer
) -> RevisionView:
    """Read a revision of a project, with its commands for the reader (``getRevision``); or 404."""
    revision = found_revision(session, revision_id, project_id, lock=False)
    return _views(session, [revision], project_id, viewer)[0]


def _judge_opening(
    session: Session, project_id: UUID, project: ProjectFacts, running: UUID | None = None
) -> None:
    """Refuse the opening of a revision as the state of the project, read under its lock, does.

    In the order of the contract: a terminal project, then a current revision, then a background
    task that would create the current revision itself — but the task ``running``, which opens it.
    """
    if project.state in TERMINAL:
        raise refuse(PROJECT_NOT_TERMINAL)
    if project.current_revision_id is not None:
        raise refuse(NO_CURRENT_REVISION)
    if not no_background_task_running(session, project_id, running):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)


def last_marked_revision(session: Session, project_id: UUID) -> UUID | None:
    """Give the last marked revision of a project, which the next current one copies, if any."""
    return _last_marked(session, project_id)


def last_marked_revisions(session: Session, project_ids: Collection[UUID]) -> dict[UUID, UUID]:
    """Give the last marked revision of each of the projects that has one, in one statement."""
    rows = session.execute(
        select(Revision.project_id, Revision.id)
        .where(Revision.project_id.in_(project_ids), Revision.status == "marked")
        .order_by(Revision.marked_at.asc(), Revision.id.asc())
    )
    # Ascending: the last row of a project is its latest.
    return {row[0]: row[1] for row in rows}


def _last_marked(session: Session, project_id: UUID) -> UUID | None:
    """Give the last marked revision of a project, the source of the next one, if any."""
    return session.scalar(
        select(Revision.id)
        .where(Revision.project_id == project_id, Revision.status == "marked")
        .order_by(Revision.marked_at.desc(), Revision.id.desc())
        .limit(1)
    )


@dataclass(frozen=True, slots=True)
class _Opening:
    """A revision to open: its identifier, its description, and the task that opens it, if one."""

    revision_id: UUID
    description: str | None = None
    running: UUID | None = None


def _open(session: Session, project_id: UUID, act: Act, opening: _Opening) -> Revision:
    """Open the current revision of a project, under the lock of the project the caller takes.

    The lock of the reference is shared first, and held until the commit: a change of the units
    of duration or of a calendar, which redates the structures of the current revisions, waits for
    the opening, and sees the revision it opens, or is waited for, and the copy is dated with what
    it wrote (WF-PLA-0160). No holder of the reference waits for the lock of a project.
    """
    revision_id, description = opening.revision_id, opening.description
    share_reference(session)
    project = lock_project(session, project_id)
    _judge_opening(session, project_id, project, opening.running)
    source = _last_marked(session, project_id)
    revision = Revision(
        id=revision_id,
        project_id=project_id,
        status="draft",
        description=description,
        reference_year=act.at.year,
        is_reference=False,
        lineage_id=revision_id,
        source_revision_id=source,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
    )
    # The index decides when the lock did not: a draft written by a transaction that did not take
    # the lock of the project is the current revision this one would duplicate.
    try:
        with session.begin_nested():
            session.add(revision)
            session.flush()
    except IntegrityError as error:
        if unique_violated(error) != DRAFT_INDEX:
            raise
        raise refuse(NO_CURRENT_REVISION) from None
    if source is None:
        create_main_structure(session, project_id, revision_id, act)
    else:
        copy_revision(session, source, revision_id)
    set_current_revision(session, project_id, revision_id, act)
    advance(session, project_id, "first_revision_created", act)
    return revision


def create_revision(
    session: Session, project_id: UUID, act: Act, viewer: Viewer, description: str | None = None
) -> RevisionView:
    """Open the current revision of a project, a copy of its last marked (``createRevision``).

    The description given is kept on the current revision, which its marking takes up (#2171).
    Refused, nothing written, on a terminal project (409 ``project_not_terminal``), while a
    current revision exists (409 ``no_current_revision``), and while a background task would
    create it itself (409 ``no_background_task_running``).
    """
    revision = _open(session, project_id, act, _Opening(new_id(), description))
    return _views(session, [revision], project_id, viewer)[0]


def open_revision_by_task(session: Session, project_id: UUID, act: Act, running: UUID) -> UUID:
    """Open the current revision of a project for the task ``running``, which writes in it.

    By the rules of ``create_revision``, the task that asks apart: the application of an import on
    a project without a current revision creates it (WF-INTF-0090, EP-06), which no other task
    may then be writing in.
    """
    return _open(session, project_id, act, _Opening(new_id(), running=running)).id


def copy_revision(session: Session, source: UUID, target: UUID) -> None:
    """Copy what a marked revision holds into the new current one, table after table (WF-DAT-0010).

    The structures here, but the merged ones, each under an identifier of its own and the lineage
    of the one it copies (#1759); the copies bear the stamp of the creation of ``target``, which is
    written already. Each epic adds its tables by ``register_copy``.
    """
    revision = session.get_one(Revision, target)
    copy = RevisionCopy(
        session=session,
        project_id=revision.project_id,
        source=source,
        target=target,
        at=revision.created_at,
        author=revision.created_by,
        identifiers={},
    )
    for copier in _COPIES.entries():
        copier(copy)


def abandon_revision(
    session: Session, project_id: UUID, abandoned: RevisionToAbandon, act: Act, viewer: Viewer
) -> None:
    """Abandon the current revision of a project, its rows deleted (``abandonRevision``).

    Under the lock of the revision, read under it, then the lock of the project: refused if
    unknown (404), if the writer is no project manager of the project any more (403, 404), at
    another version (412), once marked (409 ``revision_draft``), or while a background task writes
    in it (409 ``no_background_task_running``). The modules registered close it
    (``register_closing``), the project names no current revision any more, then the structures and
    the revision are deleted, and the abandonment is inscribed in the journal. A terminal project's
    revisions are all marked: ``revision_draft`` refuses there too.
    """
    revision_id, lock_version = abandoned.revision_id, abandoned.lock_version
    revision = found_revision(session, revision_id, project_id, lock=True)
    # The revision is locked first, the project next, as everywhere; the writer is judged under the
    # lock of the project, before any other refusal: he may be no project manager any more.
    lock_project(session, project_id)
    require_project_manager(session, project_id, viewer)
    if revision.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": revision.lock_version}
        )
    if revision.status != "draft":
        raise refuse(REVISION_DRAFT)
    if not no_background_task_running(session, project_id):
        raise refuse(NO_BACKGROUND_TASK_RUNNING)
    close_revision(session, project_id, revision_id, "abandoned")
    set_current_revision(session, project_id, None, act)
    delete_structures(session, project_id, revision_id)
    inscribe_revision(session, revision, "revision_abandon", None, act)
    session.delete(revision)
    session.flush()


def revision_draft(session: Session, revision_id: UUID) -> None:
    """Refuse a write in a revision that is marked (409, ``revision_draft``); or 404.

    The revision is read under ``FOR SHARE``: its marking and its abandonment, which lock it,
    wait for the write that judged it current. The locks are taken in one order, the revision then
    its project, never the project before the revision: the marking and the abandonment lock the
    revision, then the project they write (``set_current_revision``), and a write that locks the
    project as well calls this first. The opening, which locks the project, locks no revision.
    """
    status = session.scalar(
        select(Revision.status).where(Revision.id == revision_id).with_for_update(read=True)
    )
    if status is None:
        raise NotFoundError(NOT_FOUND)
    if status != "draft":
        raise refuse(REVISION_DRAFT)


def load_revision(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> None:
    """Open a revision of the witness under the identifier it imposes, by the rules of opening."""
    _open(session, project_id, act, _Opening(revision_id))
