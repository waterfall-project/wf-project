# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The project: read, listed, created, changed; its commands; what the journal names it by.

Created with its creator as project manager, its default work package and order item, the
transition to ``created`` and the partitions of its revised tables, in one transaction, once the
minimal reference holds (WF-CYC-0120, WF-PRJ-0010, WF-PRJ-0080, WF-DAT-0050); locked for any
transition, any creation of a revision, any designation, exit or write of the contributors (EP-04,
"Modules"); its code and its label of the day for the journal (#927); whether a background task
that writes in its current revision is queued or running, a condition of the commands that would
write in it or freeze it.

Declared by US-0910/L1; US-0920/L1 fills the project, its list, its commands and its names for
the journal, US-0960 what the revisions read of it and its current revision, which the module of
the revisions names (``set_current_revision``), US-0970 the background task. ``load_project``
writes with the identifier and the instant the witness imposes, by the very rules of the creation
(#1402).
"""

from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, case, func, or_, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.cost_settings.interface import (
    labour_categories_exist,
    provision_category_active,
)
from waterfall.core.projects.commands import (
    PROJECT_NOT_TERMINAL,
    TERMINAL,
    commands_of,
    state_conditions,
)
from waterfall.core.projects.interface.lifecycle import advance
from waterfall.core.projects.tables import (
    STATES,
    Contributor,
    OrderItem,
    Project,
    ProjectStateTransition,
    WorkPackage,
)
from waterfall.core.resource_settings.interface import (
    active_role_exists,
    default_calendar_has_hours,
)
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditObject, AuditProject, Inscription, record
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id
from waterfall.platform.tasks import project_task_pending

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Iterable, Mapping
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The six states of the cycle of life, as the contract says them (``ProjectState``).
type ProjectState = Literal["created", "pricing", "in_progress", "completed", "lost", "abandoned"]

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
ALREADY_EXISTS = "ALREADY_EXISTS"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
REFERENCE_INCOMPLETE = "REFERENCE_INCOMPLETE"
# The unique index of the code of a project (migration of the tables of the projects).
CODE_INDEX = "uq_project_code"
# The questions of the minimal reference, in the order of ``ReferenceReadiness.missing``
# (WF-CYC-0120): the modules of the settings answer, this one composes them as the route does.
PREREQUISITES = (
    ("default_calendar_with_hours", default_calendar_has_hours),
    ("active_cost_category", labour_categories_exist),
    ("active_provision_category", provision_category_active),
    ("active_resource_role", active_role_exists),
)
RATIOS = ("win_probability", "inflation_rate")
# The decimals the columns of the rates keep (``Numeric(5, 4)``): a value that has more would be
# rounded by the base, which WF-DAT-0100 forbids, so it is refused.
RATIO_DECIMALS = 4
# The columns a change may write: the attributes the creator or a manager enters, and no other
# (neither the state nor the counter, which only the module itself moves).
MODIFIABLE = (
    "label",
    "description",
    "client",
    "code",
    "inflation_rate",
    "win_probability",
    "order_received_on",
)


# The permission that opens to consultation the projects its holder does not contribute to.
ALL_PROJECTS_READ = "all_projects_read"
# The states a list keeps unless it names some: the projects in progress alone.
DEFAULT_STATES: frozenset[str] = frozenset({"in_progress"})

type ProjectColumn = Literal["label", "code", "state", "updated_at"]


@dataclass(frozen=True, slots=True)
class Viewer:
    """Who reads a project: an account and the permissions it holds (WF-ADM-0110).

    The module of the permissions gives them to the API, which hands them over; the commands a
    project lists and the projects a list keeps depend on them.
    """

    user_id: UUID
    permissions: Collection[str]

    @property
    def sees_all(self) -> bool:
        """Whether every project that exists is open to the reader (``all_projects_read``)."""
        return ALL_PROJECTS_READ in self.permissions


@dataclass(frozen=True, slots=True)
class CommandAvailability:
    """A command of a project and what it lacks: nothing if available."""

    command: str
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class ProjectFilters:
    """What the list keeps; a filter absent keeps everything of what the caller may open.

    ``states`` absent are the default ones. ``since`` is included, ``until`` excluded.
    """

    search: str | None = None
    states: frozenset[str] | None = None
    contributor_only: bool = False
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProjectSort:
    """The column of the sort and its direction; no column, the projects changed last first."""

    key: ProjectColumn | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class ProjectPage:
    """Which projects of the order are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ProjectView:
    """A project as it is read: its attributes, its commands for the reader, its audit columns.

    The authors are the identifiers of accounts, or ``None`` for the platform: the API names them.
    """

    project_id: UUID
    label: str
    description: str | None
    client: str | None
    code: str | None
    state: str
    inflation_rate: Decimal
    win_probability: Decimal
    order_received_on: date | None
    reference_revision_id: UUID | None
    current_revision_id: UUID | None
    commands: tuple[CommandAvailability, ...]
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class ProjectFacts:
    """What the revisions read of a project: its state, its current revision, its rates.

    The rates are those a current revision follows until its marking (``Revision.inflation_rate``,
    ``Revision.win_probability``).
    """

    state: str
    current_revision_id: UUID | None
    inflation_rate: Decimal
    win_probability: Decimal


def _facts(project: Project) -> ProjectFacts:
    return ProjectFacts(
        project.state,
        project.current_revision_id,
        project.inflation_rate,
        project.win_probability,
    )


@dataclass(frozen=True, slots=True)
class ProjectDraft:
    """What a project is created with: a label, and what the creator knows already."""

    label: str
    description: str | None = None
    client: str | None = None
    code: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectLoad:
    """A project of the witness: the identifier it imposes, and its draft."""

    project_id: UUID
    draft: ProjectDraft


@dataclass(frozen=True, slots=True)
class ProjectChange:
    """The columns a change carries by name, at the version read; a column absent keeps its value.

    ``client``, ``description``, ``code`` and ``order_received_on`` carried as ``None`` are
    emptied; the others are never null. A name outside ``MODIFIABLE`` is a programming error
    (``ValueError``): a change cannot write the state, the counter or a column that does not exist.
    """

    values: Mapping[str, object]
    lock_version: int

    def __post_init__(self) -> None:
        """Refuse a column no change may write."""
        unknown = sorted(set(self.values) - set(MODIFIABLE))
        if unknown:
            message = f"a change cannot write {', '.join(unknown)}"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ProjectList:
    """A page of the list, the number of projects kept, and the states it kept."""

    projects: list[ProjectView]
    total: int
    states: tuple[str, ...]


def missing_prerequisites(session: Session) -> tuple[str, ...]:
    """Name the prerequisites of the minimal reference that miss, in the order of the contract."""
    return tuple(name for name, held in PREREQUISITES if not held(session))


def retained_states(filters: ProjectFilters) -> tuple[str, ...]:
    """Name the states a list keeps, in the order of the cycle of life."""
    kept = DEFAULT_STATES if filters.states is None else filters.states
    return tuple(state for state in STATES if state in kept)


def _criteria(viewer: Viewer, filters: ProjectFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [Project.state.in_(retained_states(filters))]
    # Everything a caller that sees all may open is not restricted; any other opens its own.
    if filters.contributor_only or not viewer.sees_all:
        criteria.append(
            Project.id.in_(
                select(Contributor.project_id).where(Contributor.user_account_id == viewer.user_id)
            )
        )
    if filters.search is not None:
        criteria.append(
            or_(contains(Project.label, filters.search), contains(Project.code, filters.search))
        )
    if filters.since is not None:
        criteria.append(Project.updated_at >= filters.since)
    if filters.until is not None:
        criteria.append(Project.updated_at < filters.until)
    return criteria


def _key(column: ProjectColumn) -> SQLColumnExpression[object]:
    if column == "state":
        return case({state: rank for rank, state in enumerate(STATES)}, value=Project.state)
    return getattr(Project, column)


def _find_projects(
    session: Session, viewer: Viewer, filters: ProjectFilters, sort: ProjectSort, page: ProjectPage
) -> tuple[list[Project], int]:
    """Read a page of the projects the caller may open and the filters keep, and count them all.

    A page beyond the last one is empty, and counts the same.
    """
    criteria = _criteria(viewer, filters)
    total = session.scalars(select(func.count()).select_from(Project).where(*criteria)).one()
    order: list[SQLColumnExpression[object]] = []
    if sort.key is not None:
        key = _key(sort.key)
        order.append(key.desc() if sort.descending else key)
    order += [Project.updated_at.desc(), Project.id]
    rows = session.scalars(
        select(Project).where(*criteria).order_by(*order).limit(page.limit).offset(page.offset)
    ).all()
    return list(rows), total


def _kinds(session: Session, user_id: UUID, project_ids: Collection[UUID]) -> dict[UUID, str]:
    """Read the kind of the account on each of the projects it contributes to."""
    rows = session.execute(
        select(Contributor.project_id, Contributor.kind).where(
            Contributor.user_account_id == user_id, Contributor.project_id.in_(project_ids)
        )
    )
    return {row[0]: row[1] for row in rows}


def _views(session: Session, projects: Iterable[Project], viewer: Viewer) -> list[ProjectView]:
    rows = list(projects)
    kinds = _kinds(session, viewer.user_id, [row.id for row in rows])
    return [
        ProjectView(
            project_id=row.id,
            label=row.label,
            description=row.description,
            client=row.client,
            code=row.code,
            state=row.state,
            inflation_rate=row.inflation_rate,
            win_probability=row.win_probability,
            order_received_on=row.order_received_on,
            reference_revision_id=row.reference_revision_id,
            current_revision_id=row.current_revision_id,
            commands=tuple(
                CommandAvailability(command, missing)
                for command, missing in commands_of(
                    viewer.permissions,
                    kinds.get(row.id),
                    row.state,
                    row.current_revision_id,
                    no_task_running=no_background_task_running(session, row.id),
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


def _locked(session: Session, project_id: UUID) -> Project:
    """Lock the row of a project, then read it under the lock; or refuse (404)."""
    project = session.scalars(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if project is None:
        raise NotFoundError(NOT_FOUND)
    return project


def read_project(session: Session, project_id: UUID, viewer: Viewer) -> ProjectView:
    """Read a project and the commands it lists to the reader (``getProject``); or refuse (404)."""
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(NOT_FOUND)
    return _views(session, [project], viewer)[0]


def list_projects(
    session: Session, viewer: Viewer, filters: ProjectFilters, sort: ProjectSort, page: ProjectPage
) -> ProjectList:
    """List the projects the reader may open, filtered, sorted, by pages (``listProjects``)."""
    rows, total = _find_projects(session, viewer, filters, sort, page)
    return ProjectList(_views(session, rows, viewer), total, retained_states(filters))


def lock_project(session: Session, project_id: UUID) -> ProjectFacts:
    """Lock the row of a project for the transaction, then read it under the lock; or 404.

    ``FOR UPDATE``: the creation of a revision decides on the state and the current revision read
    here (EP-04, "Modules").
    """
    return _facts(_locked(session, project_id))


def project_facts(session: Session, project_id: UUID) -> ProjectFacts:
    """Read what the revisions read of a project, without a lock; or refuse (404)."""
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(NOT_FOUND)
    return _facts(project)


def set_current_revision(
    session: Session, project_id: UUID, revision_id: UUID | None, act: Act
) -> None:
    """Name the current revision of a project, ``None`` for none (WF-REV-0010); or 404.

    The project is locked first, if its caller has not done so: the abandonment of a revision
    and its marking hold the lock of the revision, then this one. The row of the project is
    written, its counter and its audit with it, so that a screen that read it reads it again.
    """
    project = _locked(session, project_id)
    if project.current_revision_id == revision_id:
        return
    project.current_revision_id = revision_id
    project.updated_at = act.at
    project.updated_by = act.author
    project.lock_version += 1


def project_commands(
    session: Session, project_id: UUID, viewer: Viewer
) -> tuple[CommandAvailability, ...]:
    """Give the commands of a project to its reader and the conditions each lacks (WF-IHM-0090)."""
    return read_project(session, project_id, viewer).commands


def project_label(session: Session, project_id: UUID) -> str | None:
    """Give the label of the day of a project, ``None`` if there is none (#927)."""
    return session.scalar(select(Project.label).where(Project.id == project_id))


def project_code(session: Session, project_id: UUID) -> str | None:
    """Give the code of the day of a project, ``None`` if it has none (#927)."""
    return session.scalar(select(Project.code).where(Project.id == project_id))


def projects_present(session: Session, project_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of the identifiers given, those of the projects that exist: the witness's question."""
    if not project_ids:
        return frozenset()
    return frozenset(session.scalars(select(Project.id).where(Project.id.in_(project_ids))))


def no_background_task_running(session: Session, project_id: UUID) -> bool:
    """Tell whether no background task that writes in the project is queued or running.

    The tasks that aim at a project — its marking (US-0970), and the merges, occurrences and
    imports of later epics — are read in ``waterfall.platform.tasks``.
    """
    return not project_task_pending(session, project_id)


def _code_taken(session: Session, code: str, own: UUID) -> ConflictError:
    """Refuse a code another project bears, naming that project (409, WF-PRJ-0010)."""
    holder = session.execute(
        select(Project.id, Project.label).where(Project.code == code, Project.id != own)
    ).first()
    params: dict[str, str] = {}
    if holder is not None:
        params = {"conflicting_object_id": str(holder[0]), "conflicting_object_label": holder[1]}
    return ConflictError(ALREADY_EXISTS, fields=(FieldError("/code", ALREADY_EXISTS, params),))


@contextmanager
def _unique_code(session: Session, project_id: UUID, code: str | None) -> Generator[None]:
    """Run a write that gives a project its code, refused if another project bears it (409).

    The unique index decides, whichever wrote first: a write that breaks it is undone alone, in a
    savepoint, and refused with the project that holds the code — by then committed, since the
    index made the write wait for it.
    """
    try:
        with session.begin_nested():
            yield
            session.flush()
    except IntegrityError as error:
        if unique_violated(error) != CODE_INDEX or code is None:
            raise
        raise _code_taken(session, code, project_id) from None


def _inscribe_creation(session: Session, project: Project, act: Act) -> None:
    """Inscribe the creation in the journal, the project named by its label and its code, if any."""
    audited = AuditObject("project", project.id, project.label)
    # The journal names a project by both its code and its label, or not at all: a project
    # without code is named by its object alone until it has one.
    named = None if project.code is None else AuditProject(project.id, project.code, project.label)
    actor = inscribed_actor(session, act.author)
    record(session, Inscription("project_create", actor, audited, act.at, project=named))


def _create(
    session: Session, draft: ProjectDraft, act: Act, project_id: UUID | None, *, ready: bool
) -> Project:
    """Create a project and what is born with it, once the minimal reference holds.

    ``ready`` says the reference was judged to hold: the witness alone says so (``load_project``).
    """
    missing = () if ready else missing_prerequisites(session)
    if missing:
        raise ConflictError(REFERENCE_INCOMPLETE, {"missing_prerequisites": list(missing)})
    stamp = {
        "created_at": act.at,
        "created_by": act.author,
        "updated_at": act.at,
        "updated_by": act.author,
    }
    identifier = new_id() if project_id is None else project_id
    project = Project(
        id=identifier,
        label=draft.label,
        description=draft.description,
        client=draft.client,
        code=draft.code,
        state="created",
        inflation_rate=Decimal(0),
        win_probability=Decimal(0),
        **stamp,
    )
    with _unique_code(session, identifier, draft.code):
        session.add(project)
    package = WorkPackage(
        id=new_id(), project_id=project.id, label=draft.label, position=0, **stamp
    )
    session.add_all(
        [
            ProjectStateTransition(
                id=new_id(),
                project_id=project.id,
                from_state=None,
                to_state="created",
                occurred_at=act.at,
                actor_user_id=act.author,
            ),
            package,
        ]
    )
    if act.author is not None:
        session.add(
            Contributor(project_id=project.id, user_account_id=act.author, kind="project_manager")
        )
    session.flush()
    session.add(
        OrderItem(
            id=new_id(),
            project_id=project.id,
            work_package_id=package.id,
            label=draft.label,
            position=0,
            **stamp,
        )
    )
    session.flush()
    session.execute(select(func.create_project_partitions(project.id)))
    _inscribe_creation(session, project, act)
    return project


def create_project(session: Session, draft: ProjectDraft, act: Act, viewer: Viewer) -> ProjectView:
    """Create a project, and what is born with it (``createProject``).

    Refused while the minimal reference misses a prerequisite, each named (409
    ``REFERENCE_INCOMPLETE``), and if the code is borne by another project (409
    ``ALREADY_EXISTS``). The creator is inscribed project manager; the default work package and
    order item bear the label of the project; the project is born ``created``, its transition
    written from no state; the creation is inscribed in the journal (WF-SEC-0030).

    The minimal reference is read without the lock the design asks for, the module of the
    revisions giving no interface to take it: a reference emptied between the reading and the
    commit is not caught (#2154).
    """
    return _views(session, [_create(session, draft, act, None, ready=False)], viewer)[0]


def load_project(session: Session, load: ProjectLoad, act: Act) -> None:
    """Write a project of the witness, with the identifier and the instant it imposes.

    By the rules of the creation but one: the minimal reference is not asked for. The witness
    describes roles of resources (``resource_roles.json``) that no slice loads before US-0850, so
    that the reference it loads stays short of an active role; the slice of the roles, once
    filled, lets the loader ask for it as the creation does (#1402). Until then, the projects
    would refuse the whole witness. The exemption goes with US-0990/L2 (#2155).
    """
    _create(session, load.draft, act, load.project_id, ready=True)


def _written_code(changed: Mapping[str, object]) -> str | None:
    """Give the code a change writes, ``None`` if it writes none."""
    code = changed.get("code")
    return code if isinstance(code, str) else None


def _ratio_faults(values: Mapping[str, object]) -> list[FieldError]:
    """Point at a rate or a probability out of the range 0 to 1, naming the bound crossed.

    A value in range that has more decimals than the column keeps is refused too (the base would
    round it), as a plain validation failure of its field.
    """
    faults: list[FieldError] = []
    for name in RATIOS:
        value = values.get(name)
        if not isinstance(value, Decimal):
            continue
        if not Decimal(0) <= value <= Decimal(1):
            bound = {"minimum": "0"} if value < 0 else {"maximum": "1"}
            faults.append(FieldError(f"/{name}", VALUE_OUT_OF_RANGE, bound))
        elif _decimals(value) > RATIO_DECIMALS:
            faults.append(FieldError(f"/{name}", VALIDATION_FAILED))
    return faults


def _decimals(value: Decimal) -> int:
    """Count the decimals a value needs, a useless zero not counted: ``0.0350`` needs three."""
    exponent = value.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def update_project(
    session: Session, project_id: UUID, change: ProjectChange, act: Act, viewer: Viewer
) -> ProjectView:
    """Change the attributes of a project at the version read (``updateProject``).

    The values are judged first: a rate or a probability out of 0 to 1, or that has more than four
    decimals, is refused field by field (422). Then the project is locked and read under the
    lock: refused if unknown (404), at another version (412), if the probability is sent to a
    project that has reached In progress (409, ``project_before_in_progress``, which its command
    says first), if it is terminal (409, ``project_not_terminal``), or if its new code is borne by
    another project (409). A change that changes nothing writes nothing. On a terminal project the
    probability is refused for ``project_before_in_progress``, not ``project_not_terminal``: a
    terminal project has reached In progress, and the condition of the probability is the one its
    own command names, where a terminal project lists no command at all. A code entered calls
    ``advance`` under the lock, which has no effect before US-0980 (WF-PRJ-0010, WF-CYC-0030).
    """
    values = change.values
    faults = _ratio_faults(values)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    project = _locked(session, project_id)
    if project.lock_version != change.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": project.lock_version}
        )
    if "win_probability" in values:
        lacking = state_conditions(
            "update_win_probability",
            project.state,
            project.current_revision_id,
            no_task_running=True,
        )
        if lacking:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": lacking[0]})
    if project.state in TERMINAL:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": PROJECT_NOT_TERMINAL})
    changed = {name: value for name, value in values.items() if getattr(project, name) != value}
    if changed:
        with _unique_code(session, project.id, _written_code(changed)):
            for name, value in changed.items():
                setattr(project, name, value)
            project.updated_at = act.at
            project.updated_by = act.author
            project.lock_version += 1
        if changed.get("code") is not None:
            advance(session, project.id, "reference_designated_and_code_set", act)
    return _views(session, [project], viewer)[0]
