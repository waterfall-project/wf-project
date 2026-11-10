# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources and their capacity.

Read, listed, created, changed, deactivated and reactivated (WF-REF-0080, 0090, 0100); the
questions the categories of cost ask (``category_has_roles``, ``roles_of_categories``), the
minimal reference (``active_role_exists``) and the planning (``role_calendars``, EP-06).

A role hangs under a node fixed at its creation, is attached to a category of labour and to a
calendar, and carries one capacity, hours a month and a headcount, without a date. Its code is
unique among the roles, deactivated ones included. It is created active, under an active node,
and reactivated only under one: its creation and its activation run under the lock of the tree,
which the cascade of a node holds too (``org_nodes``), so that no role stays active under a node
closed meanwhile.

This module does not read the cost settings, which read it (``category_has_roles``): what a role
is told of its category — whether it is one of labour, whether it is active — is given by its
caller, who asks the cost settings (``CategoryAdmission``), and so is the label a list sorts the
categories by (``LabelOf``). The views name the category by its identifier; the API names it.
Nothing is deleted, and no write is inscribed in the journal of audit (EP-05, "Ce que le cadrage
décide").
"""

from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError

from waterfall.core.resource_settings.interface.org_nodes import lock_tree, within_node
from waterfall.core.resource_settings.interface.readiness import lock_reference
from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Generator, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy import Select
    from sqlalchemy.engine import Row
    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
ALREADY_EXISTS = "ALREADY_EXISTS"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
FIELD_READ_ONLY = "FIELD_READ_ONLY"
UNKNOWN_ORG_NODE = "UNKNOWN_ORG_NODE"
UNKNOWN_COST_CATEGORY = "UNKNOWN_COST_CATEGORY"
UNKNOWN_CALENDAR = "UNKNOWN_CALENDAR"
LABOUR_CATEGORY_REQUIRED = "LABOUR_CATEGORY_REQUIRED"
INACTIVE_REFERENCE_OBJECT = "INACTIVE_REFERENCE_OBJECT"
TASK_WITHOUT_WORKING_HOURS = "TASK_WITHOUT_WORKING_HOURS"
# What the reactivation of a role lacks while its node is deactivated (WF-REF-0080).
NODE_ACTIVE_CONDITION = "org_node_active"
# The least a capacity holds, hours a month as a headcount (WF-REF-0100).
LEAST_CAPACITY = Decimal(0)
# The unique index of the code, named as the naming convention names it.
CODE_INDEX = "uq_resource_role_code"
# The first version of a role, as the examples of the contract have it.
FIRST_VERSION = 1

type RoleColumn = Literal[
    "label",
    "code",
    "org_node",
    "cost_category",
    "calendar",
    "monthly_hours",
    "headcount",
    "is_active",
]
# Of a column that holds categories, the label of the category held: what the cost settings give.
type LabelOf = Callable[[SQLColumnExpression[UUID]], SQLColumnExpression[str | None]]


@dataclass(frozen=True, slots=True)
class Capacity:
    """The single capacity of a role, without a date: hours a month and a headcount."""

    monthly_hours: Decimal
    headcount: Decimal


@dataclass(frozen=True, slots=True)
class CategoryAdmission:
    """What a role is told of the category it is given, by the cost settings (WF-REF-0090).

    Whether the nature of the category is of labour, and whether the category is active; a
    category the reference does not have is told by none at all.
    """

    is_labour: bool
    is_active: bool


@dataclass(frozen=True, slots=True)
class RoleDraft:
    """What a role is created with: its three attachments and its capacity.

    ``category`` is what the cost settings tell of the category given (``CategoryAdmission``).
    """

    code: str
    label: str
    org_node_id: UUID
    cost_category_id: UUID
    category: CategoryAdmission | None
    calendar_id: UUID
    capacity: Capacity


@dataclass(frozen=True, slots=True)
class RoleChange:
    """What a role is changed with; the node, sent or not, never changes (WF-REF-0090).

    ``category`` is what the cost settings tell of the category given (``CategoryAdmission``).
    """

    code: str
    label: str
    org_node_id: UUID | None
    cost_category_id: UUID
    category: CategoryAdmission | None
    calendar_id: UUID
    capacity: Capacity


@dataclass(frozen=True, slots=True)
class RoleCommand:
    """The command that changes the state of a role, and what it lacks: nothing if available."""

    command: Literal["deactivate", "reactivate"]
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class RoleView:
    """A role as it is read: its node and its calendar named, its category by its identifier.

    The authors are the identifiers of accounts, or ``None`` for the platform: the API names them,
    and the category.
    """

    resource_role_id: UUID
    code: str
    label: str
    org_node_id: UUID
    org_node_label: str
    cost_category_id: UUID
    calendar_id: UUID
    calendar_label: str
    capacity: Capacity
    is_active: bool
    commands: tuple[RoleCommand, ...]
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class RoleFilters:
    """What the table of the roles keeps; a filter absent keeps everything (WF-IHM-0130).

    ``org_node_id`` keeps the roles of the node and of its descendants; ``states`` the values of
    ``is_active`` kept; the bounds of the capacity are inclusive.
    """

    search: str | None = None
    code: str | None = None
    org_node_id: UUID | None = None
    cost_category_id: UUID | None = None
    calendar_id: UUID | None = None
    states: frozenset[bool] = frozenset({True})
    monthly_hours_min: Decimal | None = None
    monthly_hours_max: Decimal | None = None
    headcount_min: Decimal | None = None
    headcount_max: Decimal | None = None


@dataclass(frozen=True, slots=True)
class RoleSort:
    """The column of the sort and its direction; the label unless said otherwise (WF-IHM-0060).

    The node, the category and the calendar sort by their labels — the category by
    ``category_label``, which the cost settings give —; the deactivated roles come after the active
    in the ascending order of ``is_active``. Equals come by label, then identifier.
    """

    category_label: LabelOf
    column: RoleColumn = "label"
    descending: bool = False


@dataclass(frozen=True, slots=True)
class RoleWindow:
    """Which roles of the order are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class RolePage:
    """A page of the roles the filters keep, and how many they keep."""

    roles: list[RoleView]
    total: int


def _command(*, is_active: bool, node_is_active: bool) -> RoleCommand:
    """Give the command of a role: its reactivation lacks an active node (WF-REF-0080)."""
    if is_active:
        return RoleCommand("deactivate")
    return RoleCommand("reactivate", () if node_is_active else (NODE_ACTIVE_CONDITION,))


def _view(row: Row[ResourceRole, str, bool, str], *, may_change: bool) -> RoleView:
    role, node_label, node_is_active, calendar_label = row
    commands = (
        (_command(is_active=role.is_active, node_is_active=node_is_active),) if may_change else ()
    )
    return RoleView(
        resource_role_id=role.id,
        code=role.code,
        label=role.label,
        org_node_id=role.org_node_id,
        org_node_label=node_label,
        cost_category_id=role.cost_category_id,
        calendar_id=role.calendar_id,
        calendar_label=calendar_label,
        capacity=Capacity(role.monthly_hours, role.headcount),
        is_active=role.is_active,
        commands=commands,
        created_at=role.created_at,
        created_by=role.created_by,
        updated_at=role.updated_at,
        updated_by=role.updated_by,
        lock_version=role.lock_version,
    )


def _described() -> Select[ResourceRole, str, bool, str]:
    """Select a role with the label and the state of its node and the label of its calendar."""
    return (
        select(ResourceRole, OrgNode.label, OrgNode.is_active, Calendar.label)
        .join(OrgNode, OrgNode.id == ResourceRole.org_node_id)
        .join(Calendar, Calendar.id == ResourceRole.calendar_id)
        .execution_options(populate_existing=True)
    )


def read_roles(session: Session, role_ids: Collection[UUID], *, may_change: bool) -> list[RoleView]:
    """Read the roles given, deactivated or not, by label then identifier; an unknown is left out.

    ``may_change`` gives each the command of its state, which a caller who may not change the
    resource settings is not offered.
    """
    if not role_ids:
        return []
    rows = session.execute(
        _described()
        .where(ResourceRole.id.in_(role_ids))
        .order_by(ResourceRole.label, ResourceRole.id)
    )
    return [_view(row, may_change=may_change) for row in rows]


def read_role(session: Session, role_id: UUID, *, may_change: bool) -> RoleView:
    """Read a role, deactivated or not, or refuse (404)."""
    found = read_roles(session, [role_id], may_change=may_change)
    if not found:
        raise NotFoundError(NOT_FOUND)
    return found[0]


def _criteria(filters: RoleFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [ResourceRole.is_active.in_(filters.states)]
    if filters.search is not None:
        criteria.append(
            or_(
                contains(ResourceRole.label, filters.search),
                contains(ResourceRole.code, filters.search),
            )
        )
    if filters.code is not None:
        criteria.append(contains(ResourceRole.code, filters.code))
    if filters.org_node_id is not None:
        criteria.append(within_node(filters.org_node_id, ResourceRole.org_node_id))
    if filters.cost_category_id is not None:
        criteria.append(ResourceRole.cost_category_id == filters.cost_category_id)
    if filters.calendar_id is not None:
        criteria.append(ResourceRole.calendar_id == filters.calendar_id)
    bounds = (
        (ResourceRole.monthly_hours, filters.monthly_hours_min, filters.monthly_hours_max),
        (ResourceRole.headcount, filters.headcount_min, filters.headcount_max),
    )
    for column, low, high in bounds:
        if low is not None:
            criteria.append(column >= low)
        if high is not None:
            criteria.append(column <= high)
    return criteria


def list_roles(
    session: Session,
    filters: RoleFilters,
    sort: RoleSort,
    window: RoleWindow,
    *,
    may_change: bool,
) -> RolePage:
    """Read a page of the roles the filters keep, in the order of the sort, and count them all."""
    keys: dict[RoleColumn, SQLColumnExpression[Any]] = {
        "label": ResourceRole.label,
        "code": ResourceRole.code,
        "org_node": OrgNode.label,
        "cost_category": sort.category_label(ResourceRole.cost_category_id),
        "calendar": Calendar.label,
        "monthly_hours": ResourceRole.monthly_hours,
        "headcount": ResourceRole.headcount,
        # False sorts first: the active, then the deactivated, in the ascending order.
        "is_active": ~ResourceRole.is_active,
    }
    key = keys[sort.column]
    order = (key.desc() if sort.descending else key, ResourceRole.label, ResourceRole.id)
    criteria = _criteria(filters)
    total = session.scalars(select(func.count()).select_from(ResourceRole).where(*criteria)).one()
    rows = session.execute(
        _described().where(*criteria).order_by(*order).limit(window.limit).offset(window.offset)
    )
    return RolePage([_view(row, may_change=may_change) for row in rows], total)


def _capacity_faults(capacity: Capacity) -> list[FieldError]:
    """Name each value of the capacity under the least admitted (WF-REF-0100)."""
    least = {"minimum": str(LEAST_CAPACITY)}
    return [
        FieldError(f"/capacity/{name}", VALUE_OUT_OF_RANGE, least)
        for name, value in (
            ("monthly_hours", capacity.monthly_hours),
            ("headcount", capacity.headcount),
        )
        if value < LEAST_CAPACITY
    ]


def _node_fault(session: Session, node_id: UUID) -> FieldError | None:
    """Name the fault of the node a role is created under: unknown, or deactivated (422).

    Read under the lock of the tree, which every write of the nodes takes.
    """
    is_active = session.scalars(select(OrgNode.is_active).where(OrgNode.id == node_id)).first()
    if is_active is None:
        return FieldError("/org_node_id", UNKNOWN_ORG_NODE)
    return None if is_active else FieldError("/org_node_id", INACTIVE_REFERENCE_OBJECT)


def _category_fault(category: CategoryAdmission | None) -> FieldError | None:
    """Name the one fault of a category: unknown, out of labour, then deactivated (422).

    Out of labour before deactivated: its reactivation would not lift that (contract).
    """
    if category is None:
        return FieldError("/cost_category_id", UNKNOWN_COST_CATEGORY)
    if not category.is_labour:
        return FieldError("/cost_category_id", LABOUR_CATEGORY_REQUIRED)
    if not category.is_active:
        return FieldError("/cost_category_id", INACTIVE_REFERENCE_OBJECT)
    return None


def _calendar_fault(session: Session, calendar_id: UUID) -> FieldError | None:
    """Name the fault of a calendar given a role: unknown, or deactivated (422).

    Read without a lock, which would hold nothing: a role attached to a calendar deactivated
    afterwards stays valid — it keeps it, and only a calendar given is judged —, so a deactivation
    that comes just after the role is attached leaves the state a deactivation that comes later
    would. The calendar is never deleted (WF-DAT-0080), and the key of the role holds it anyway.
    """
    is_active = session.scalars(
        select(Calendar.is_active).where(Calendar.id == calendar_id)
    ).first()
    if is_active is None:
        return FieldError("/calendar_id", UNKNOWN_CALENDAR)
    return None if is_active else FieldError("/calendar_id", INACTIVE_REFERENCE_OBJECT)


def _refuse(faults: Sequence[FieldError | None]) -> None:
    """Refuse a role at every field at fault, all named at once, in the order given (422)."""
    named = tuple(fault for fault in faults if fault is not None)
    if named:
        raise UnprocessableError(VALIDATION_FAILED, fields=named)


@contextmanager
def _unique_code(session: Session, code: str) -> Generator[None]:
    """Run a write that gives a role ``code``, refused if another role holds it (409).

    The unique index decides, whatever wrote first: a write that breaks it is undone alone, in a
    savepoint, and refused naming the role that holds the code, deactivated or not.
    """
    try:
        with session.begin_nested():
            yield
    except IntegrityError as error:
        if unique_violated(error) != CODE_INDEX:
            raise
        holder = session.execute(
            select(ResourceRole.id, ResourceRole.label).where(ResourceRole.code == code)
        ).first()
        params = (
            {}
            if holder is None
            else {"conflicting_object_id": str(holder.id), "conflicting_object_label": holder.label}
        )
        raise ConflictError(
            ALREADY_EXISTS, fields=(FieldError("/code", ALREADY_EXISTS, params),)
        ) from None


def create_role(
    session: Session, draft: RoleDraft, act: Act, *, identifier: UUID | None = None
) -> RoleView:
    """Create an active role, under the lock of the tree, and read it back.

    Refused at each attachment unknown, deactivated, or — the category — out of labour, and at a
    negative capacity (422, one reason a field); then if another role holds its code (409).
    ``identifier`` is imposed by the loader of the witness alone: the API never passes one.
    """
    lock_tree(session)
    _refuse(
        [
            _node_fault(session, draft.org_node_id),
            _category_fault(draft.category),
            _calendar_fault(session, draft.calendar_id),
            *_capacity_faults(draft.capacity),
        ]
    )
    role_id = new_id() if identifier is None else identifier
    with _unique_code(session, draft.code):
        session.execute(
            insert(ResourceRole).values(
                id=role_id,
                code=draft.code,
                label=draft.label,
                org_node_id=draft.org_node_id,
                cost_category_id=draft.cost_category_id,
                calendar_id=draft.calendar_id,
                monthly_hours=draft.capacity.monthly_hours,
                headcount=draft.capacity.headcount,
                is_active=True,
                lock_version=FIRST_VERSION,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
    return read_role(session, role_id, may_change=True)


def _lock_role(session: Session, role_id: UUID, lock_version: int) -> ResourceRole:
    """Lock a role, then read it under the lock, at the version read; or refuse (404, 412)."""
    role = session.scalars(
        select(ResourceRole)
        .where(ResourceRole.id == role_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if role is None:
        raise NotFoundError(NOT_FOUND)
    if role.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": role.lock_version}
        )
    return role


def _write(session: Session, role: ResourceRole, act: Act, **values: object) -> None:
    """Write a locked role, its version advanced and its author the actor's."""
    session.execute(
        update(ResourceRole)
        .where(ResourceRole.id == role.id, ResourceRole.lock_version == role.lock_version)
        .values(
            **values,
            lock_version=ResourceRole.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
    )


def role_calendar_change_is_admissible(session: Session, role_id: UUID, calendar_id: UUID) -> bool:
    """Tell whether the role may take this calendar without a task left without an hour.

    Provisional: the template the design of EP-05 lays for EP-06, whose form — the signature, the
    question asked, the parameters of the refusal ``TASK_WITHOUT_WORKING_HOURS`` that
    ``update_role`` raises when it answers no — EP-06 fixes (WF-PLA-0010). Always so for now: no
    task depends on a role before EP-06.
    """
    del session, role_id, calendar_id
    return True


def update_role(
    session: Session, role_id: UUID, change: RoleChange, lock_version: int, act: Act
) -> RoleView:
    """Change a role whose version is the one read; its node never changes (WF-REF-0090).

    Refused if unknown (404), at another version (412); at a node sent other than its own
    (``FIELD_READ_ONLY``), at a category or a calendar it is given that is unknown, out of labour
    or deactivated — those it keeps, deactivated since, are not judged —, at a negative capacity
    (422, one reason a field); at a calendar that would leave a task without an hour (422,
    EP-06); then if another role holds its code (409).
    """
    role = _lock_role(session, role_id, lock_version)
    moved = change.org_node_id is not None and change.org_node_id != role.org_node_id
    recalendared = change.calendar_id != role.calendar_id
    _refuse(
        [
            FieldError("/org_node_id", FIELD_READ_ONLY) if moved else None,
            (
                _category_fault(change.category)
                if change.cost_category_id != role.cost_category_id
                else None
            ),
            _calendar_fault(session, change.calendar_id) if recalendared else None,
            *_capacity_faults(change.capacity),
        ]
    )
    # Provisional, as its question: the form of this refusal is EP-06's to fix.
    if recalendared and not role_calendar_change_is_admissible(
        session, role_id, change.calendar_id
    ):
        raise UnprocessableError(TASK_WITHOUT_WORKING_HOURS, {"resource_roles": [], "projects": []})
    with _unique_code(session, change.code):
        _write(
            session,
            role,
            act,
            code=change.code,
            label=change.label,
            cost_category_id=change.cost_category_id,
            calendar_id=change.calendar_id,
            monthly_hours=change.capacity.monthly_hours,
            headcount=change.capacity.headcount,
        )
    return read_role(session, role_id, may_change=True)


def set_role_activation(
    session: Session, role_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> RoleView:
    """Deactivate or reactivate a role, under the lock of the tree, at the version read.

    Refused if unknown (404), at another version (412), or — to reactivate — while its node is
    deactivated (409, ``org_node_active``, the node named), as its command says in advance; its
    category and its calendar may stay deactivated. A role already in the state asked for is
    answered as it is, nothing written.
    """
    if not is_active:
        lock_reference(session)
    lock_tree(session)
    role = _lock_role(session, role_id, lock_version)
    if role.is_active != is_active:
        node = session.get_one(OrgNode, role.org_node_id, populate_existing=True)
        command = _command(is_active=False, node_is_active=node.is_active)
        if is_active and not command.is_available:
            raise ConflictError(
                STATE_FORBIDS_OPERATION,
                {
                    "missing_condition": command.missing_conditions[0],
                    "conflicting_object_id": str(node.id),
                },
            )
        _write(session, role, act, is_active=is_active)
    return read_role(session, role_id, may_change=True)


def roles_present(session: Session, role_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of these identifiers, those a role bears: what the loader of the witness asks."""
    found = session.scalars(select(ResourceRole.id).where(ResourceRole.id.in_(role_ids)))
    return frozenset(found)


def active_role_exists(session: Session) -> bool:
    """Tell whether an active role of resources exists: a question of the minimal reference."""
    active = select(ResourceRole.id).where(ResourceRole.is_active).exists()
    return bool(session.scalar(select(active)))


def role_calendars(session: Session, role_ids: Collection[UUID]) -> dict[UUID, UUID]:
    """Give the calendar of each role given, deactivated or not: what a task's hours follow (EP-06).

    An identifier no role bears is left out.
    """
    if not role_ids:
        return {}
    rows = session.execute(
        select(ResourceRole.id, ResourceRole.calendar_id).where(ResourceRole.id.in_(role_ids))
    )
    return dict(rows.all())


@dataclass(frozen=True, slots=True)
class RoleOfCategory:
    """A role attached to a category, as a refusal names it: active or not (WF-IHM-0090)."""

    resource_role_id: UUID
    code: str
    label: str


def category_has_roles(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those a role of resources is attached to, deactivated or not.

    What binds a category to labour, and its nature with it (WF-REF-0030, WF-REF-0040). A role
    created or moved to a category meanwhile shares the lock of the natures, which a change of the
    category or of its nature takes first, and waits for (``category_labels``).
    """
    if not category_ids:
        return frozenset()
    found = session.scalars(
        select(ResourceRole.cost_category_id)
        .where(ResourceRole.cost_category_id.in_(category_ids))
        .distinct()
    )
    return frozenset(found)


def roles_of_categories(session: Session, category_ids: Collection[UUID]) -> list[RoleOfCategory]:
    """Give the roles attached to the categories given, deactivated ones too, in the order of code.

    The roles a refusal to change the kind of a nature or of a category names (WF-REF-0030,
    WF-REF-0040).
    """
    if not category_ids:
        return []
    rows = session.execute(
        select(ResourceRole.id, ResourceRole.code, ResourceRole.label)
        .where(ResourceRole.cost_category_id.in_(category_ids))
        .order_by(ResourceRole.code, ResourceRole.id)
    )
    return [RoleOfCategory(role_id, code, label) for role_id, code, label in rows]
