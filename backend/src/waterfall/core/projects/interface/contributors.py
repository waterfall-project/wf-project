# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of a project and their kind (WF-PRJ-0060).

The kind of an account on a project, which the evaluation of an action reads (``contributor_kind``,
WF-ADM-0110); the list read, written whole under its own counter — a project keeps a project
manager —, and the suggestions of the screen, empty while no line of estimate employs a role
(WF-PRJ-0070, EP-07). Whether a project exists, which the evaluation reads of a caller that is no
contributor of it (``project_exists``): a project it may consult and one that does not exist are
refused alike, but for ``all_projects_read``, which opens every project that exists.

The list is read whole, its accounts by the interface of the accounts, and filtered, searched and
sorted here: a project holds fifty contributors at most (§4.6.2), and the names are the accounts'.
It is written under the lock of the project, which the quality of the writer is read under, since
the evaluation read it in a transaction of its own: a writer withdrawn from the list meanwhile is
refused as the evaluation would have refused it (WF-ADM-0090). One caller who is no contributor
may write: the rescue of a project whose project managers are all deactivated, to inscribe one
(WF-PRJ-0060, ``manage_contributors``). Every other write reserved to the project managers judges
its caller the same way, under the lock of the project (``require_project_manager``, #2207).

Declared by US-0910/L1, without effect: US-0910/L2 filled ``contributor_kind`` and
``project_exists``, US-0930 fills the rest; ``load_contributors`` writes those of the witness.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import Text, Uuid, column, exists, select, values

from waterfall.core.projects.commands import (
    IS_CONTRIBUTOR,
    IS_PROJECT_MANAGER,
    PROJECT_NOT_TERMINAL,
    TERMINAL,
)
from waterfall.core.projects.interface.estimate_facts import roles_employed
from waterfall.core.projects.tables import Contributor, Project
from waterfall.core.resource_settings.interface import read_roles
from waterfall.core.users.interface import (
    AccountLabel,
    active_accounts,
    active_accounts_in_nodes,
    read_account_labels,
)
from waterfall.platform.database import contains
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    ForbiddenError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface.projects import Viewer

# The two kinds of contributor, as the contract says them (``ContributorKind``).
type ContributorKind = Literal["project_manager", "contributor"]
type ContributorColumn = Literal["display_name", "kind", "is_active"]

NOT_FOUND = "NOT_FOUND"
NOT_CONTRIBUTOR = "NOT_CONTRIBUTOR"
NOT_PROJECT_MANAGER = "NOT_PROJECT_MANAGER"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
LAST_PROJECT_MANAGER = "LAST_PROJECT_MANAGER"
VALIDATION_FAILED = "VALIDATION_FAILED"
UNKNOWN_USER = "UNKNOWN_USER"
USER_INACTIVE = "USER_INACTIVE"
# The permission of the settings of a project, which the rescue asks for besides.
SETTINGS_WRITE = "project_settings.write"
MANAGER: ContributorKind = "project_manager"
# The kinds in the order of the contract (``ContributorKind``): the project managers first.
KIND_ORDER = {"project_manager": 0, "contributor": 1}


@dataclass(frozen=True, slots=True)
class ContributorView:
    """A contributor as the list shows it: the name of its account, null once it is anonymised."""

    user_id: UUID
    display_name: str | None
    kind: ContributorKind
    is_active: bool


@dataclass(frozen=True, slots=True)
class ContributorsRead:
    """The contributors of a project and the counter of the list, null for a filtered reading."""

    items: tuple[ContributorView, ...]
    lock_version: int | None


@dataclass(frozen=True, slots=True)
class ContributorFilters:
    """What a reading keeps: a search on the displayed name, kinds, the state of the account."""

    search: str | None = None
    kinds: frozenset[str] | None = None
    is_active: bool | None = None

    @property
    def is_filtered(self) -> bool:
        """Whether the reading omits contributors: the counter it gives would not do to write."""
        return self.search is not None or self.kinds is not None or self.is_active is not None


@dataclass(frozen=True, slots=True)
class ContributorSort:
    """The column of the sort and its direction; none, the project managers first, then by name."""

    column: ContributorColumn | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class ContributorEntry:
    """A line of the list written: an account and its kind."""

    user_id: UUID
    kind: ContributorKind


@dataclass(frozen=True, slots=True)
class ContributorsToWrite:
    """The whole list written, at the counter of the list read."""

    entries: tuple[ContributorEntry, ...]
    lock_version: int


@dataclass(frozen=True, slots=True)
class ContributorsLoad:
    """The list the witness imposes on a project, with the counter it imposes."""

    project_id: UUID
    entries: tuple[ContributorEntry, ...]
    lock_version: int


@dataclass(frozen=True, slots=True)
class ContributorSuggestion:
    """An account a line of the estimate proposes, with its node and the roles that propose it."""

    user_id: UUID
    display_name: str | None
    org_node_id: UUID
    org_node_label: str
    resource_role_ids: tuple[UUID, ...]
    resource_role_labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Row:
    """A contributor with the names its account sorts by."""

    view: ContributorView
    last_name: str | None
    first_name: str | None


def contributor_kind(session: Session, project_id: UUID, user_id: UUID) -> ContributorKind | None:
    """Give the kind of an account on a project, ``None`` if it is no contributor.

    Read as committed when the request asks: a list of contributors written meanwhile applies at
    the next request, as a role changed does (WF-ADM-0090).
    """
    kind = session.scalar(
        select(Contributor.kind).where(
            Contributor.project_id == project_id, Contributor.user_account_id == user_id
        )
    )
    # The table holds the two kinds alone (``kind_known``).
    return cast("ContributorKind | None", kind)


def refusal_to_non_manager(
    kind: ContributorKind | None, viewer: Viewer
) -> ForbiddenError | NotFoundError:
    """Give the refusal of a write reserved to the project managers to who is not one.

    A participant is told so (403 ``NOT_PROJECT_MANAGER``). One who is no contributor is refused
    as the evaluation does: 404 if it cannot consult the project (no ``all_projects_read``), 403
    ``NOT_CONTRIBUTOR`` otherwise.
    """
    if kind is not None:
        return ForbiddenError(NOT_PROJECT_MANAGER, {"missing_condition": IS_PROJECT_MANAGER})
    if not viewer.sees_all:
        return NotFoundError(NOT_FOUND)
    return ForbiddenError(NOT_CONTRIBUTOR, {"missing_condition": IS_CONTRIBUTOR})


def require_project_manager(session: Session, project_id: UUID, viewer: Viewer) -> None:
    """Refuse a write reserved to the project managers to who no longer is one of the project.

    To be called under the lock of the project, once taken: the list of the contributors changes
    under that same lock, so the quality read here is the one the write commits with. The kind is
    read afresh by a statement of its own; nothing is cached in the session.
    """
    kind = contributor_kind(session, project_id, viewer.user_id)
    if kind != MANAGER:
        raise refusal_to_non_manager(kind, viewer)


def project_exists(session: Session, project_id: UUID) -> bool:
    """Tell whether a project exists, whatever its state: a project is never deleted."""
    return bool(session.scalar(select(exists().where(Project.id == project_id))))


def _stored(session: Session, project_id: UUID) -> tuple[int, dict[UUID, ContributorKind]]:
    """Read the counter of the list and its lines in one statement; or refuse (404)."""
    rows = session.execute(
        select(Project.contributors_lock_version, Contributor.user_account_id, Contributor.kind)
        .select_from(Project)
        .outerjoin(Contributor, Contributor.project_id == Project.id)
        .where(Project.id == project_id)
    ).all()
    if not rows:
        raise NotFoundError(NOT_FOUND)
    # The outer join gives a project without contributor one row, its line null.
    lines = cast("list[tuple[int, UUID | None, ContributorKind | None]]", [tuple(r) for r in rows])
    kinds: dict[UUID, ContributorKind] = {
        user_id: kind for _, user_id, kind in lines if user_id is not None and kind is not None
    }
    return lines[0][0], kinds


def _rows(
    accounts: Mapping[UUID, AccountLabel], kinds: Mapping[UUID, ContributorKind]
) -> list[_Row]:
    """Name the accounts of the lines, each as it is shown today."""
    rows: list[_Row] = []
    for user_id, kind in kinds.items():
        label = accounts.get(user_id)
        # An account is never deleted (``RESTRICT``): a line always has its account.
        if label is None:
            continue
        shown = (
            None
            if label.first_name is None or label.last_name is None
            else f"{label.first_name} {label.last_name}"
        )
        view = ContributorView(user_id, shown, kind, label.is_active)
        rows.append(_Row(view, label.last_name, label.first_name))
    return rows


def _found(session: Session, rows: Iterable[_Row], search: str) -> frozenset[UUID]:
    """Name the contributors whose displayed name holds the text searched, by the database.

    Compared as the contract says — transliterated by ``unaccent``, whatever the case — in one
    request on the names of the lines.
    """
    named = [(row.view.user_id, row.view.display_name) for row in rows if row.view.display_name]
    if not named:
        return frozenset()
    names = values(column("id", Uuid), column("name", Text), name="names").data(named)
    return frozenset(session.scalars(select(names.c.id).where(contains(names.c.name, search))))


def _by_name(row: _Row) -> tuple[int, bool, str, str, str]:
    """Sort a line as the accounts are: its kind, its name, its first name; anonymised last."""
    return (
        KIND_ORDER[row.view.kind],
        row.last_name is None,
        row.last_name or "",
        row.first_name or "",
        str(row.view.user_id),
    )


def _kept(row: _Row, filters: ContributorFilters, found: frozenset[UUID] | None) -> bool:
    view = row.view
    if found is not None and view.user_id not in found:
        return False
    if filters.kinds is not None and view.kind not in filters.kinds:
        return False
    return filters.is_active is None or view.is_active == filters.is_active


def _column(column: ContributorColumn, row: _Row) -> tuple[bool, str] | int:
    """Give what a sort on a column compares; a name null after the names in the ascending order."""
    view = row.view
    if column == "display_name":
        return (view.display_name is None, view.display_name or "")
    if column == "kind":
        return KIND_ORDER[view.kind]
    # False before true: the active accounts first in the ascending order.
    return int(not view.is_active)


def _read(
    session: Session,
    kinds: Mapping[UUID, ContributorKind],
    filters: ContributorFilters,
    sort: ContributorSort,
) -> tuple[ContributorView, ...]:
    """Filter and sort the lines; equals keep the order of the list unsorted (WF-IHM-0060)."""
    rows = _rows(read_account_labels(session, kinds), kinds)
    found = None if filters.search is None else _found(session, rows, filters.search)
    ordered = sorted(rows, key=_by_name)
    if sort.column is not None:
        column = sort.column
        # Stable, also reversed: equals keep the order of the list unsorted, ascending.
        ordered.sort(key=lambda row: _column(column, row), reverse=sort.descending)
    return tuple(row.view for row in ordered if _kept(row, filters, found))


def list_contributors(
    session: Session, project_id: UUID, filters: ContributorFilters, sort: ContributorSort
) -> ContributorsRead:
    """List the contributors of a project, with the counter of the list (``listContributors``).

    Searched on the displayed name, filtered by kind and by the state of the account, a deactivated
    account being listed all the same and signalled (WF-ADM-0060); sorted as the sort says, the
    project managers first and then the accounts by name unsorted, an anonymised account — no name
    to show — after the names. The counter is null for a filtered reading, which omits
    contributors: written as it is, the list would remove them. Refused if the project does not
    exist (404).
    """
    counter, kinds = _stored(session, project_id)
    items = _read(session, kinds, filters, sort)
    return ContributorsRead(items, None if filters.is_filtered else counter)


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


def _check_writer(session: Session, kinds: Mapping[UUID, ContributorKind], viewer: Viewer) -> bool:
    """Judge the writer under the lock; tell whether it writes as the rescue of the project.

    A project manager writes. Who is not one is refused as the evaluation does
    (``refusal_to_non_manager``) — unless it is no contributor, holds the permission of the
    settings and ``all_projects_read``, and every project manager of the project is deactivated: it
    rescues the project, and its list must hold a project manager that is active.
    """
    kind = kinds.get(viewer.user_id)
    if kind == MANAGER:
        return False
    if kind is None and viewer.sees_all and SETTINGS_WRITE in viewer.permissions:
        managers = [user_id for user_id, held in kinds.items() if held == MANAGER]
        if not active_accounts(session, managers):
            return True
    raise refusal_to_non_manager(kind, viewer)


def _faults(
    accounts: Mapping[UUID, AccountLabel],
    entries: Iterable[ContributorEntry],
    kinds: Mapping[UUID, ContributorKind],
) -> list[FieldError]:
    """Point at each line whose account the list may not hold: unknown, deactivated, or doubled.

    A deactivated account stays in the list as it was read; it is refused when inscribed or
    changed of kind (WF-ADM-0060).
    """
    faults: list[FieldError] = []
    seen: set[UUID] = set()
    for position, entry in enumerate(entries):
        pointer = f"/contributors/{position}/user_id"
        label = accounts.get(entry.user_id)
        if entry.user_id in seen:
            faults.append(FieldError(pointer, VALIDATION_FAILED))
        elif label is None:
            faults.append(FieldError(pointer, UNKNOWN_USER))
        elif not label.is_active and kinds.get(entry.user_id) != entry.kind:
            faults.append(FieldError(pointer, USER_INACTIVE))
        seen.add(entry.user_id)
    return faults


def _replace(session: Session, project: Project, entries: Iterable[ContributorEntry]) -> None:
    """Write the lines of the list: those withdrawn removed, those changed and those added."""
    wanted = {entry.user_id: entry.kind for entry in entries}
    held = {
        row.user_account_id: row
        for row in session.scalars(select(Contributor).where(Contributor.project_id == project.id))
    }
    for user_id, row in held.items():
        if user_id not in wanted:
            session.delete(row)
        elif row.kind != wanted[user_id]:
            row.kind = wanted[user_id]
    session.add_all(
        Contributor(project_id=project.id, user_account_id=user_id, kind=kind)
        for user_id, kind in wanted.items()
        if user_id not in held
    )
    session.flush()


def set_contributors(
    session: Session, project_id: UUID, write: ContributorsToWrite, viewer: Viewer
) -> ContributorsRead:
    """Write the whole list of the contributors at the counter read (``setContributors``).

    Under the lock of the project, the writer judged on the list as it stands (403, 404), then a
    terminal project refused (409, ``project_not_terminal``), a counter that is not the list's
    (412), each line whose account is unknown, deactivated or written twice (422,
    ``UNKNOWN_USER``, ``USER_INACTIVE``, ``VALIDATION_FAILED`` at the repeated line), and a list
    that keeps no project manager (409, ``LAST_PROJECT_MANAGER``) — an active one when the writer
    rescues the project. Nothing is written then. The list is answered whole with its next
    counter, built before the commit.
    """
    # The accounts of the lines, read in one request before the lock is taken. Reading them under
    # it would close no race: a deactivation locks the row of the account, never the project's,
    # so ``USER_INACTIVE`` judges the same either way; the active project managers of a rescue are
    # read again under the lock (``active_accounts``).
    accounts = read_account_labels(session, [entry.user_id for entry in write.entries])
    project = _locked(session, project_id)
    _, kinds = _stored(session, project_id)
    rescuing = _check_writer(session, kinds, viewer)
    if project.state in TERMINAL:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": PROJECT_NOT_TERMINAL})
    if project.contributors_lock_version != write.lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": project.contributors_lock_version}
        )
    faults = _faults(accounts, write.entries, kinds)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    managers = [entry.user_id for entry in write.entries if entry.kind == MANAGER]
    if not (active_accounts(session, managers) if rescuing else managers):
        raise ConflictError(LAST_PROJECT_MANAGER)
    _replace(session, project, write.entries)
    project.contributors_lock_version += 1
    session.flush()
    counter, written = _stored(session, project_id)
    items = _read(session, written, ContributorFilters(), ContributorSort())
    return ContributorsRead(items, counter)


def list_contributor_suggestions(
    session: Session, project_id: UUID
) -> tuple[ContributorSuggestion, ...]:
    """Suggest the accounts the lines of the project employ (``listContributorSuggestions``).

    The active accounts attached to the node of a role the labour lines of the project employ
    (``roles_employed``: the current revision, or the last marked), that the list does not count,
    each with its node and the roles of that node the lines employ, by name. Empty while no line
    employs a role (WF-PRJ-0070). The list is not written. Refused if the project does not exist
    (404).
    """
    if not project_exists(session, project_id):
        raise NotFoundError(NOT_FOUND)
    employed = roles_employed(session, project_id)
    if not employed:
        return ()
    roles = read_roles(session, employed, may_change=False)
    by_node: dict[UUID, list[tuple[UUID, str]]] = {}
    labels: dict[UUID, str] = {}
    for role in roles:
        by_node.setdefault(role.org_node_id, []).append((role.resource_role_id, role.label))
        labels[role.org_node_id] = role.org_node_label
    counted = _stored(session, project_id)[1]
    return tuple(
        ContributorSuggestion(
            account.user_id,
            account.display_name,
            account.org_node_id,
            labels[account.org_node_id],
            tuple(role_id for role_id, _ in by_node[account.org_node_id]),
            tuple(label for _, label in by_node[account.org_node_id]),
        )
        for account in active_accounts_in_nodes(session, by_node)
        if account.user_id not in counted
    )


def contributors_present(
    session: Session, project_id: UUID, user_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Name, of the accounts given, those that are contributors of the project."""
    return frozenset(
        session.scalars(
            select(Contributor.user_account_id).where(
                Contributor.project_id == project_id, Contributor.user_account_id.in_(user_ids)
            )
        )
    )


def load_contributors(session: Session, load: ContributorsLoad) -> None:
    """Write the contributors of a project of the witness, as it imposes them, with its counter.

    By the rules of the list but those of a writer: the accounts are known and the list keeps a
    project manager; the account deactivated since its inscription is listed all the same.
    """
    accounts = read_account_labels(session, [entry.user_id for entry in load.entries])
    project = _locked(session, load.project_id)
    faults = [
        FieldError(f"/contributors/{position}/user_id", UNKNOWN_USER)
        for position, entry in enumerate(load.entries)
        if entry.user_id not in accounts
    ]
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    if not any(entry.kind == MANAGER for entry in load.entries):
        raise ConflictError(LAST_PROJECT_MANAGER)
    _replace(session, project, load.entries)
    project.contributors_lock_version = load.lock_version
    session.flush()
