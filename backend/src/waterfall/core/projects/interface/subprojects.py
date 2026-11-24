# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of a project (WF-PRJ-0050).

Listed, created, changed and deleted for good while nothing cites them, each with its commands;
their code free — the element of the ERP whole, ``A.ABC.26001/10001`` —, unique in the project and
never the code of the project, compared whole, without its blanks at the ends, as the WBS element
of a line of cost is compared to it (``compared_code``; WF-PRJ-0050, WF-CRE-0020; #3966).

A subproject is written like the project is changed (the command ``update`` of the project): by
a project manager, while the project is not terminal, under the lock of the project, which the
state is read under. The code is unique in its project: the codes of the project are read under
that lock, which every writer of a subproject holds, and a code equal to another once both are
without their blanks at the ends is refused, the writer told the subproject that holds it — the
unique index of the table, on the code as stored, is only a backstop. The code of the project is
read under the same lock, which a recoding of the project holds too: a subproject never takes it,
as the project never takes the code of one of its subprojects (``SUBPROJECT_CODE_INVALID``). The
code stored is the one sent.

The three conditions of the deletion — no marked revision that cites it, no actual cost, no line
of the current revision that bears it — are asked of the later modules: the estimate answers the
first and the last by its lines (``estimate_facts``, US-1490/L4), the actual costs the second, by
the registry declared here (``register_cost_facts``, US-1610/L3), which also says
``has_actual_costs`` of the list, its filter and its sort; none is ever lacking before
``project_not_terminal``. The risks answer the first too, by the evaluations of the marked
revisions that designate the subproject for their provision (``risk_designations``, #4208). A
deletion refused for the lines of the current revision names them (WF-DAT-0080). A deletion admitted
sets to null the designation of the risks of the current revision that designated it, none of them
identified — the provision line of one would bear it —, each risk's counter advanced and its audit
naming the author of the deletion (#732). ``load_subprojects`` writes those of the witness, by the
very rules of the creation.

A subproject created imputes nothing: a line of cost whose WBS element was its code was rejected
at its import, and only the reimport of the extraction imputes it (WF-CRE-0020; #3966). A change of
its code imputes nothing either, and leaves every line where it is (EP-09, D-10).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, select

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
from waterfall.core.projects.interface.estimate_facts import (
    forget_subproject,
    subproject_estimate_lines,
    subprojects_cited,
    subprojects_estimated,
)
from waterfall.core.projects.interface.projects import (
    ALREADY_EXISTS,
    Viewer,
    code_of_project_refused,
    compared_code,
    lock_project,
)
from waterfall.core.projects.interface.risk_designations import (
    subprojects_designated,
    undesignate_subproject,
)
from waterfall.core.projects.tables import Project, Subproject
from waterfall.platform.database import contains
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
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface.estimate_facts import EstimatedLine
    from waterfall.platform.audit import Act

VALUE_REQUIRED = "VALUE_REQUIRED"
# The conditions of the deletion, in the order of the contract: the citation, by a line or by the
# designation of a risk, which no write lifts (a marked revision is immutable), the actual costs,
# then the lines of the current revision.
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
class SubprojectDeletion:
    """A deletion of a subproject: the subproject and its version as read."""

    subproject_id: UUID
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


def code_faults(code: str) -> list[FieldError]:
    """Name what makes a code refused before its project is read: blank, and nothing else.

    Its bound is the contract's, 100 characters (``SUBPROJECT_CODE_LENGTH``); any character, a
    slash, a dot or a name Waterfall gives a tab of its own included, is admitted (#3966).
    """
    return [FieldError("/code", VALUE_REQUIRED)] if not code.strip() else []


def _refuse_code(write: SubprojectWrite) -> None:
    """Refuse a blank code (422), judged again for the witness, no body's."""
    faults = code_faults(write.code)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))


def _refuse_code_of_project(project: Project, code: str) -> None:
    """Refuse the code of the project to one of its subprojects, the project read under its lock.

    Compared without their blanks at the ends (``compared_code``).
    """
    if project.code is not None and compared_code(project.code) == compared_code(code):
        raise code_of_project_refused()


@dataclass(frozen=True, slots=True)
class CostFacts:
    """What the actual costs answer the projects of their lines.

    ``subproject_has_actual_costs`` gives, of the subprojects named, those a line of cost is
    imputed to, tracked or excluded. A creation imputes nothing (WF-CRE-0020; #3966).
    """

    subproject_has_actual_costs: Callable[[Session, Collection[UUID]], frozenset[UUID]]


# What the actual costs answer of their lines, registered at the import of their interface.
_COSTS: Registry[CostFacts] = Registry("projects.cost_facts")


def register_cost_facts(facts: CostFacts) -> Callable[[], None]:
    """Add what the actual costs answer the projects of their lines; give its withdrawal."""
    return _COSTS.register(facts)


def subprojects_with_actual_costs(
    session: Session, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects named, those an actual cost is imputed to; none if unregistered."""
    found: set[UUID] = set()
    if subproject_ids:
        for facts in _COSTS.entries():
            found |= facts.subproject_has_actual_costs(session, subproject_ids)
    return frozenset(found)


def subproject_has_actual_costs(session: Session, subproject_id: UUID) -> bool:
    """Tell whether an actual cost is imputed to the subproject, tracked or excluded."""
    return subproject_id in subprojects_with_actual_costs(session, [subproject_id])


@dataclass(frozen=True, slots=True)
class _Deletion:
    """What the deletion of a subproject lacks, in the order of the contract, and the lines."""

    missing: tuple[str, ...] = ()
    lines: tuple[EstimatedLine, ...] = ()


def _deletions(
    session: Session,
    project_id: UUID,
    subproject_ids: Collection[UUID],
    *,
    naming: bool = False,
    costs: frozenset[UUID] | None = None,
) -> dict[UUID, _Deletion]:
    """Name what the deletion of each subproject of a project lacks.

    The estimate and the actual costs are asked once for them all whether a line bears each, the
    risks whether the evaluation of a marked revision designates each (#4208); the lines of the
    estimate themselves, which only the refusal of a deletion shows, are read when ``naming``;
    ``costs``, the subprojects an actual cost is imputed to, if its caller read them.
    """
    cited = subprojects_cited(session, project_id, subproject_ids) | subprojects_designated(
        session, project_id, subproject_ids
    )
    if costs is None:
        costs = subprojects_with_actual_costs(session, subproject_ids)
    estimated = subprojects_estimated(session, project_id, subproject_ids)
    named = subproject_estimate_lines(session, project_id, subproject_ids) if naming else {}
    found: dict[UUID, _Deletion] = {}
    for each in subproject_ids:
        missing = (
            (NOT_CITED, each in cited),
            (WITHOUT_ACTUAL_COSTS, each in costs),
            (WITHOUT_ESTIMATE_LINES, each in estimated),
        )
        found[each] = _Deletion(
            tuple(name for name, lacks in missing if lacks), named.get(each, ())
        )
    return found


def _commands(
    held: dict[str, tuple[str, ...]], quality: tuple[str, ...], deletion: _Deletion
) -> tuple[SubprojectCommandAvailability, ...]:
    """List the commands of a subproject as the command ``update`` of its project does.

    ``held`` and ``quality`` are those of the reader on the project, computed once per list. None
    for a caller that does not hold ``update``, and none on a terminal project, which lists no
    command; the quality on the project comes first among the conditions each lacks. ``delete``
    lacks those of the deletion (``_deletions``): ``subproject_not_cited`` for a marked revision
    that cites it by a line or by the risk that designates it for its provision (#4208); the
    designation of a risk of the current revision lacks nothing, the deletion sets it to null.
    """
    if "update" not in held:
        return ()
    return (
        SubprojectCommandAvailability("update", held["update"]),
        SubprojectCommandAvailability("delete", (*quality, *deletion.missing)),
    )


def _views(
    session: Session,
    project: Project,
    rows: Collection[Subproject],
    viewer: Viewer,
    costs: frozenset[UUID] | None = None,
) -> list[SubprojectView]:
    """Give the view of each subproject; ``costs`` those an actual cost is imputed to, if read."""
    kind = contributor_kind(session, project.id, viewer.user_id)
    held = dict(
        commands_of(
            viewer.permissions,
            kind,
            project.state,
            project.current_revision_id,
            running=Running(no_task_running=True, mapping_complete=True),
        )
    )
    quality = tuple(quality_conditions(kind, manager=True))
    if costs is None:
        costs = subprojects_with_actual_costs(session, [row.id for row in rows])
    asked = [row.id for row in rows] if "update" in held else []
    deletions = _deletions(session, project.id, asked, costs=costs)
    return [
        SubprojectView(
            subproject_id=row.id,
            code=row.code,
            label=row.label,
            has_actual_costs=row.id in costs,
            commands=_commands(held, quality, deletions.get(row.id, _Deletion())),
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
    return criteria


def list_subprojects(
    session: Session,
    project_id: UUID,
    viewer: Viewer,
    filters: SubprojectFilters,
    sort: SubprojectSort,
) -> list[SubprojectView]:
    """List the subprojects of a project, with their commands, whole (``listSubprojects``).

    By the code unless a column is asked, then by the code and the identifier on a tie. Whether an
    actual cost is imputed is asked of the actual costs once for the subprojects searched: the
    filter keeps those it answers as asked, the sort puts those without any first ascending.
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
    costs = subprojects_with_actual_costs(session, [row.id for row in rows])
    kept = [
        row
        for row in rows
        if filters.has_actual_costs is None or (row.id in costs) == filters.has_actual_costs
    ]
    if sort.key == "has_actual_costs":
        # A stable sort: the code and the identifier order the ties, ascending in either direction.
        kept.sort(key=lambda row: row.id in costs, reverse=sort.descending)
    return _views(session, project, kept, viewer, costs)


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


def _refuse_code_taken(session: Session, project_id: UUID, code: str, own: UUID) -> None:
    """Refuse a code another subproject of the project bears, naming it (409, WF-PRJ-0050).

    Compared without their blanks at the ends (``compared_code``): ``X`` and ``X `` would name one
    WBS element. Read under the lock of the project, which every writer of a subproject holds.
    """
    held = session.execute(
        select(Subproject.id, Subproject.label, Subproject.code)
        .where(Subproject.project_id == project_id, Subproject.id != own)
        .order_by(Subproject.code, Subproject.id)
    )
    compared = compared_code(code)
    for holder_id, label, held_code in held:
        if compared_code(held_code) == compared:
            params = {"conflicting_object_id": str(holder_id), "conflicting_object_label": label}
            raise ConflictError(
                ALREADY_EXISTS, fields=(FieldError("/code", ALREADY_EXISTS, params),)
            )


def create_subproject(
    session: Session, project_id: UUID, write: SubprojectWrite, act: Act, viewer: Viewer
) -> SubprojectView:
    """Create a subproject of a project (``createSubproject``).

    The code is judged first (422); then the project is locked and read under the lock: refused if
    unknown (404), if the writer is no project manager of it any more (403), if terminal (409
    ``project_not_terminal``), or if the code is borne by another subproject of the project (409
    ``ALREADY_EXISTS`` on ``/code``) — or if it is the code of the project (422
    ``SUBPROJECT_CODE_INVALID`` on ``/code``), read under that lock — both compared without their
    blanks at the ends. Created, it imputes no line of cost (WF-CRE-0020; #3966).
    """
    _refuse_code(write)
    project = _writable(session, project_id, viewer)
    _refuse_code_of_project(project, write.code)
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
    _refuse_code_taken(session, project_id, write.code, subproject_id)
    session.add(row)
    session.flush()
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
    lock: refused if unknown (404), at another version (412), if the project is terminal (409), if
    the new code is the code of the project (422 ``SUBPROJECT_CODE_INVALID``), or if it is borne by
    another subproject (409), both compared without their blanks at the ends; a code unchanged is
    not judged again. A change that changes nothing writes nothing. A new code imputes no line of
    cost, and takes none from the subproject: a line moves at its next import alone (EP-09, D-10;
    WF-DAT-0060).
    """
    write = change.write
    _refuse_code(write)
    project, row = _locked(session, project_id, change.subproject_id, change.lock_version, viewer)
    _refuse_code_of_project(project, write.code)
    if row.code != write.code:
        _refuse_code_taken(session, project_id, write.code, row.id)
    if (row.code, row.label) != (write.code, write.label):
        row.code = write.code
        row.label = write.label
        row.updated_at = act.at
        row.updated_by = act.author
        row.lock_version += 1
        session.flush()
    return _views(session, project, [row], viewer)[0]


def delete_subproject(
    session: Session,
    project_id: UUID,
    deletion: SubprojectDeletion,
    act: Act,
    viewer: Viewer,
) -> None:
    """Delete for good a subproject that nothing cites (``deleteSubproject``).

    ``deletion`` names the subproject and its version as read. Refused if unknown (404), at another
    version (412), and by the first condition of its command that is lacking (409
    ``STATE_FORBIDS_OPERATION``, ``missing_condition``): ``subproject_not_cited`` for a marked
    revision whose line bears it or whose risk designates it for its provision (#4208), the lines
    of the current revision that bear it named for ``subproject_without_estimate_lines``
    (``estimate_lines``, WF-DAT-0080). The lines of the bases of the differentials, which no
    operation serves, neither refuse it nor keep it (``forget_subproject``, US-3050). The risks of
    the current revision that designate it, none identified, keep their place, their designation
    set to null by the act (``undesignate_subproject``, #732, #4208).
    """
    _, row = _locked(session, project_id, deletion.subproject_id, deletion.lock_version, viewer)
    # ``_locked`` has judged the project writable (``_writable``): the manager under the lock, and
    # not terminal. The subproject is locked: a line that names it meanwhile waits on its key.
    judged = _deletions(session, project_id, [row.id], naming=True)[row.id]
    if judged.missing:
        params: dict[str, object] = {"missing_condition": judged.missing[0]}
        if judged.missing[0] == WITHOUT_ESTIMATE_LINES:
            params["estimate_lines"] = [
                {
                    "structure_id": str(line.structure_id),
                    "structure_label": line.structure_label,
                    "node_id": str(line.node_id),
                    "row_number": line.row_number,
                    "label": line.label,
                }
                for line in judged.lines
            ]
        raise ConflictError(STATE_FORBIDS_OPERATION, params)
    forget_subproject(session, project_id, row.id)
    undesignate_subproject(session, project_id, row.id, act)
    session.delete(row)
    session.flush()


def subproject_labels(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID], *, held: bool = False
) -> dict[UUID, str]:
    """Give the label of each subproject of a project named; one of another project is left out.

    What a line of estimate shows of its subproject, and what it may name (EP-07). ``held`` reads
    them ``FOR KEY SHARE``, for a write that names them: a deletion under way is waited for, and a
    subproject it took away is left out, as one that never was, instead of failing the key of the
    line the write inserts (#2616); a deletion that comes after waits for the write, and sees the
    line it then refuses (``subproject_without_estimate_lines``).
    """
    if not subproject_ids:
        return {}
    query = select(Subproject.id, Subproject.label).where(
        Subproject.project_id == project_id, Subproject.id.in_(subproject_ids)
    )
    if held:
        query = query.with_for_update(key_share=True, of=Subproject)
    return dict(session.execute(query).all())


def subproject_ids(session: Session, project_id: UUID) -> tuple[UUID, ...]:
    """Give the subprojects of a project, by their code: what the indicators of the day draw.

    Without their commands, which ``list_subprojects`` reads: the key of the cache of the
    indicators reads them at each reading (EP-10, "Le cache").
    """
    return tuple(
        session.scalars(
            select(Subproject.id)
            .where(Subproject.project_id == project_id)
            .order_by(Subproject.code, Subproject.id)
        )
    )


def project_subproject_labels(session: Session, project_id: UUID) -> dict[UUID, str]:
    """Give the label of each subproject of a project, all of them.

    What a line of estimate shows of its subproject, read whole: what a reading kept of a marked
    revision depends on outside it (EP-26, US-2270), a label changed making it stale.
    """
    return dict(
        session.execute(
            select(Subproject.id, Subproject.label).where(Subproject.project_id == project_id)
        ).all()
    )


def subprojects_named(
    session: Session, project_id: UUID, labels: Collection[str]
) -> dict[str, list[UUID]]:
    """Give the subprojects of a project each label names; a label with none is absent.

    What a cell pasted into the estimate names its subproject by (EP-07, US-1560); the label is not
    unique, and the caller refuses a label of several as unknown.
    """
    found: dict[str, list[UUID]] = {}
    if not labels:
        return found
    rows = session.execute(
        select(Subproject.label, Subproject.id)
        .where(Subproject.project_id == project_id, Subproject.label.in_(list(labels)))
        .order_by(Subproject.code)
    )
    for label, subproject_id in rows:
        found.setdefault(label, []).append(subproject_id)
    return found


def subprojects_coded(
    session: Session, project_id: UUID, codes: Collection[str]
) -> dict[str, UUID]:
    """Give the subproject of a project each code names, as stored; a code of none is absent.

    What a line of cost is imputed by, its code read in its WBS element (WF-CRE-0020, EP-09).
    """
    if not codes:
        return {}
    rows = session.execute(
        select(Subproject.code, Subproject.id).where(
            Subproject.project_id == project_id, Subproject.code.in_(list(codes))
        )
    )
    return dict(rows.all())


def subprojects_by_code(session: Session, project_id: UUID) -> dict[str, UUID]:
    """Give every subproject of a project by its code, as stored.

    What the WBS element of a line of cost is compared to, whole (WF-CRE-0020; #3966).
    """
    rows = session.execute(
        select(Subproject.code, Subproject.id).where(Subproject.project_id == project_id)
    )
    return dict(rows.all())


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

    By the rules of the creation: the code is judged, never the code of the project and unique in
    it, the project not terminal.
    """
    project = _unterminated(session, project_id)
    for load in loads:
        _refuse_code(load.write)
        _refuse_code_of_project(project, load.write.code)
        _insert(session, project.id, load.write, act, load.subproject_id)
