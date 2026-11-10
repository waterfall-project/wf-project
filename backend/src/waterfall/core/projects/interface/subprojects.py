# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of a project (WF-PRJ-0050).

Listed, created, changed and deleted for good while nothing cites them, each with its commands;
their code unique in the project, never one of the two names Waterfall gives its own tabs (#1502).

A subproject is written like the project is changed (the command ``update`` of the project): by
a project manager, while the project is not terminal, under the lock of the project, which the
state is read under. The code is unique in its project, whichever of two writers came first: the
unique index decides, and the writer it refuses is told the subproject that holds the code. The
reserved names are compared after the code is normalised (NFC, the runs of blanks of any kind
folded into one space and trimmed, the case ignored): "Synthèse " and the decomposed form of
"Synthèse" are the name (#1502); the code stored is the one sent.

The three conditions of the deletion — no marked revision that cites it, no actual cost, no line
of the current revision that bears it — are questions of this file that EP-07 and EP-09 fill; they
hold here, so that none is ever lacking before ``project_not_terminal``. ``load_subprojects``
writes those of the witness, by the very rules of the creation.
"""

import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, false, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.projects.commands import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    Running,
    commands_of,
    quality_conditions,
)
from waterfall.core.projects.interface.contributors import (
    contributor_kind,
    require_project_manager,
)
from waterfall.core.projects.interface.projects import ALREADY_EXISTS, Viewer, lock_project
from waterfall.core.projects.tables import Project, Subproject
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Generator
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

SUBPROJECT_CODE_INVALID = "SUBPROJECT_CODE_INVALID"
VALUE_REQUIRED = "VALUE_REQUIRED"
# The unique index of the code of a subproject in its project (the tables of the projects).
CODE_INDEX = "uq_subproject_project_id"
# The characters the name of a tab of a workbook refuses, in the order of the contract.
FORBIDDEN_CHARACTERS = ":\\/?*[]"
# The two names Waterfall gives its own tabs, as it writes them.
RESERVED_NAMES = ("Synthèse", "Hors sous-projet")
# The conditions of the deletion, in the order of the contract: the citation, which no write
# lifts (a marked revision is immutable), the actual costs, then the lines of the current revision.
NOT_CITED = "subproject_not_cited"
WITHOUT_ACTUAL_COSTS = "subproject_without_actual_costs"
WITHOUT_ESTIMATE_LINES = "subproject_without_estimate_lines"

type SubprojectColumn = Literal["code", "label", "has_actual_costs"]


@dataclass(frozen=True, slots=True)
class SubprojectFilters:
    """What the list keeps: the subprojects whose code or label holds the search, by costs."""

    search: str | None = None
    has_actual_costs: bool | None = None


@dataclass(frozen=True, slots=True)
class SubprojectSort:
    """The column of the sort and its direction; no column, the code."""

    key: SubprojectColumn | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class SubprojectWrite:
    """What a subproject is written with: its code and its label."""

    code: str
    label: str


@dataclass(frozen=True, slots=True)
class SubprojectChange:
    """A change of a subproject: what it is written with, at the version read."""

    subproject_id: UUID
    write: SubprojectWrite
    lock_version: int


@dataclass(frozen=True, slots=True)
class SubprojectLoad:
    """A subproject of the witness: the identifier it imposes, and what it is written with."""

    subproject_id: UUID
    write: SubprojectWrite


@dataclass(frozen=True, slots=True)
class SubprojectCommandAvailability:
    """A command of a subproject and the conditions it lacks: none if available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class SubprojectView:
    """A subproject as it is read, with its commands for the reader and its audit columns."""

    subproject_id: UUID
    code: str
    label: str
    has_actual_costs: bool
    commands: tuple[SubprojectCommandAvailability, ...]
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


def normalised_name(code: str) -> str:
    """Fold a code to what the reserved names are compared with: NFC, one blank, no case."""
    return " ".join(unicodedata.normalize("NFC", code).split()).casefold()


def code_faults(code: str) -> list[FieldError]:
    """Name what makes a code refused for a tab: blank, the characters it holds, or its name."""
    if not code.strip():
        return [FieldError("/code", VALUE_REQUIRED)]
    if any(character in code for character in FORBIDDEN_CHARACTERS):
        # Each once, in the order the code bears them.
        held = dict.fromkeys(character for character in code if character in FORBIDDEN_CHARACTERS)
        return [FieldError("/code", SUBPROJECT_CODE_INVALID, {"forbidden_characters": list(held)})]
    folded = normalised_name(code)
    for name in RESERVED_NAMES:
        if folded == normalised_name(name):
            return [FieldError("/code", SUBPROJECT_CODE_INVALID, {"reserved_name": name})]
    return []


def _refuse_code(write: SubprojectWrite) -> None:
    """Refuse a code that cannot name a tab (422), judged again for the witness, no body's."""
    faults = code_faults(write.code)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))


def subproject_is_cited(session: Session, subproject_id: UUID) -> bool:
    """Tell whether a marked revision cites the subproject by its lines; none does before EP-07."""
    del session, subproject_id
    return False


def subproject_has_actual_costs(session: Session, subproject_id: UUID) -> bool:
    """Tell whether an actual cost is imputed to the subproject; none is before EP-09."""
    del session, subproject_id
    return False


def subproject_is_estimated(session: Session, subproject_id: UUID) -> bool:
    """Tell whether a line of the current revision bears the subproject; none does before EP-07."""
    del session, subproject_id
    return False


def _deletion_lacks(session: Session, subproject_id: UUID) -> list[str]:
    """Name the conditions of the deletion that are lacking, in the order of the contract."""
    missing: list[str] = []
    if subproject_is_cited(session, subproject_id):
        missing.append(NOT_CITED)
    if subproject_has_actual_costs(session, subproject_id):
        missing.append(WITHOUT_ACTUAL_COSTS)
    if subproject_is_estimated(session, subproject_id):
        missing.append(WITHOUT_ESTIMATE_LINES)
    return missing


def _commands(
    held: dict[str, tuple[str, ...]],
    quality: tuple[str, ...],
    session: Session,
    subproject_id: UUID,
) -> tuple[SubprojectCommandAvailability, ...]:
    """List the commands of a subproject as the command ``update`` of its project does.

    ``held`` and ``quality`` are those of the reader on the project, computed once per list. None
    for a caller that does not hold ``update``, and none on a terminal project, which lists no
    command; the quality on the project comes first among the conditions each lacks.
    """
    if "update" not in held:
        return ()
    lacking = _deletion_lacks(session, subproject_id)
    return (
        SubprojectCommandAvailability("update", held["update"]),
        SubprojectCommandAvailability("delete", (*quality, *lacking)),
    )


def _views(
    session: Session, project: Project, rows: Collection[Subproject], viewer: Viewer
) -> list[SubprojectView]:
    kind = contributor_kind(session, project.id, viewer.user_id)
    held = dict(
        commands_of(
            viewer.permissions,
            kind,
            project.state,
            project.current_revision_id,
            running=Running(no_task_running=True),
        )
    )
    quality = tuple(quality_conditions(kind, manager=True))
    return [
        SubprojectView(
            subproject_id=row.id,
            code=row.code,
            label=row.label,
            has_actual_costs=subproject_has_actual_costs(session, row.id),
            commands=_commands(held, quality, session, row.id),
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
            lock_version=row.lock_version,
        )
        for row in rows
    ]


def _criteria(project_id: UUID, filters: SubprojectFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [Subproject.project_id == project_id]
    if filters.search is not None:
        criteria.append(
            contains(Subproject.code, filters.search) | contains(Subproject.label, filters.search)
        )
    # No actual cost is imputed before EP-09: a filter on those that bear some keeps none.
    if filters.has_actual_costs:
        criteria.append(false())
    return criteria


def list_subprojects(
    session: Session,
    project_id: UUID,
    viewer: Viewer,
    filters: SubprojectFilters,
    sort: SubprojectSort,
) -> list[SubprojectView]:
    """List the subprojects of a project, with their commands, whole (``listSubprojects``).

    By the code unless a column is asked, then by the code and the identifier on a tie; the column
    of the actual costs is the same for all of them before EP-09, so it orders nothing.
    """
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(NOT_FOUND)
    order: list[SQLColumnExpression[object]] = []
    if sort.key in {"code", "label"}:
        key: SQLColumnExpression[object] = getattr(Subproject, sort.key)
        order.append(key.desc() if sort.descending else key)
    order += [Subproject.code, Subproject.id]
    rows = session.scalars(
        select(Subproject).where(*_criteria(project_id, filters)).order_by(*order)
    ).all()
    return _views(session, project, rows, viewer)


def _unterminated(session: Session, project_id: UUID) -> Project:
    """Lock a project, then read it under the lock, refused if it is terminal (409)."""
    lock_project(session, project_id)
    project = session.get(Project, project_id, populate_existing=True)
    if project is None:
        raise NotFoundError(NOT_FOUND)
    if project.state in TERMINAL:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": PROJECT_NOT_TERMINAL})
    return project


def _writable(session: Session, project_id: UUID, viewer: Viewer) -> Project:
    """Lock a project for a write of the API, the writer judged first under that lock.

    Refused if the writer is no project manager of the project (403, 404;
    ``require_project_manager``), then if the project is terminal (409).
    """
    lock_project(session, project_id)
    require_project_manager(session, project_id, viewer)
    return _unterminated(session, project_id)


def _code_taken(session: Session, project_id: UUID, code: str, own: UUID) -> ConflictError:
    """Refuse a code another subproject of the project bears, naming it (409, WF-PRJ-0050)."""
    holder = session.execute(
        select(Subproject.id, Subproject.label).where(
            Subproject.project_id == project_id, Subproject.code == code, Subproject.id != own
        )
    ).first()
    params: dict[str, str] = {}
    if holder is not None:
        params = {"conflicting_object_id": str(holder[0]), "conflicting_object_label": holder[1]}
    return ConflictError(ALREADY_EXISTS, fields=(FieldError("/code", ALREADY_EXISTS, params),))


@contextmanager
def _unique_code(session: Session, project_id: UUID, code: str, own: UUID) -> Generator[None]:
    """Run a write that gives a subproject its code, refused if another bears it (409).

    The unique index decides: a write that breaks it is undone alone, in a savepoint, and refused
    with the subproject that holds the code.
    """
    try:
        with session.begin_nested():
            yield
            session.flush()
    except IntegrityError as error:
        if unique_violated(error) != CODE_INDEX:
            raise
        raise _code_taken(session, project_id, code, own) from None


def create_subproject(
    session: Session, project_id: UUID, write: SubprojectWrite, act: Act, viewer: Viewer
) -> SubprojectView:
    """Create a subproject of a project (``createSubproject``).

    The code is judged first (422); then the project is locked and read under the lock: refused if
    unknown (404), if the writer is no project manager of it any more (403), if terminal (409
    ``project_not_terminal``), or if the code is borne by another subproject of the project (409
    ``ALREADY_EXISTS`` on ``/code``).
    """
    _refuse_code(write)
    project = _writable(session, project_id, viewer)
    row = _insert(session, project.id, write, act, new_id())
    return _views(session, project, [row], viewer)[0]


def _insert(
    session: Session, project_id: UUID, write: SubprojectWrite, act: Act, subproject_id: UUID
) -> Subproject:
    row = Subproject(
        id=subproject_id,
        project_id=project_id,
        code=write.code,
        label=write.label,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
        lock_version=0,
    )
    with _unique_code(session, project_id, write.code, subproject_id):
        session.add(row)
    return row


def _locked(
    session: Session, project_id: UUID, subproject_id: UUID, lock_version: int, viewer: Viewer
) -> tuple[Project, Subproject]:
    """Lock the project, then read the subproject under the lock at the version read; or refuse."""
    project = _writable(session, project_id, viewer)
    row = session.scalars(
        select(Subproject)
        .where(Subproject.id == subproject_id, Subproject.project_id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    if row.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": row.lock_version}
        )
    return project, row


def update_subproject(
    session: Session, project_id: UUID, change: SubprojectChange, act: Act, viewer: Viewer
) -> SubprojectView:
    """Change a subproject at the version read (``updateSubproject``).

    The code is judged first (422). Then the project is locked and the subproject read under the
    lock: refused if unknown (404), at another version (412), if the project is terminal (409), or
    if the new code is borne by another subproject (409). A change that changes nothing writes
    nothing.
    """
    write = change.write
    _refuse_code(write)
    project, row = _locked(session, project_id, change.subproject_id, change.lock_version, viewer)
    if (row.code, row.label) != (write.code, write.label):
        with _unique_code(session, project_id, write.code, row.id):
            row.code = write.code
            row.label = write.label
            row.updated_at = act.at
            row.updated_by = act.author
            row.lock_version += 1
    return _views(session, project, [row], viewer)[0]


def delete_subproject(
    session: Session, project_id: UUID, subproject_id: UUID, lock_version: int, viewer: Viewer
) -> None:
    """Delete for good a subproject that nothing cites (``deleteSubproject``).

    Refused if unknown (404), at another version (412), and by the first condition of its command
    that is lacking (409 ``STATE_FORBIDS_OPERATION``, ``missing_condition``). The place of the
    risks that designate it for their provision is kept: EP-08 nulls the designation.
    """
    _, row = _locked(session, project_id, subproject_id, lock_version, viewer)
    # ``_locked`` has judged the project writable (``_writable``): the manager under the lock, and
    # not terminal.
    lacking = _deletion_lacks(session, row.id)
    if lacking:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": lacking[0]})
    session.delete(row)
    session.flush()


def subprojects_present(session: Session, subproject_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of the identifiers given, those of the subprojects that exist (the witness's)."""
    if not subproject_ids:
        return frozenset()
    found = select(Subproject.id).where(Subproject.id.in_(subproject_ids))
    return frozenset(session.scalars(found))


def load_subprojects(
    session: Session, project_id: UUID, loads: Collection[SubprojectLoad], act: Act
) -> None:
    """Write the subprojects of a project of the witness, under the identifiers it imposes.

    By the rules of the creation: the code is judged, unique in the project, the project not
    terminal.
    """
    project = _unterminated(session, project_id)
    for load in loads:
        _refuse_code(load.write)
        _insert(session, project.id, load.write, act, load.subproject_id)
