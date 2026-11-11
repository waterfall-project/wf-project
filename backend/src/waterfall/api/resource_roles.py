# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources (FBS-3.2).

``listResourceRoles``, ``createResourceRole``, ``updateResourceRole`` and
``setResourceRoleActivation``.

The active roles are read by any open session: whoever reads a project names and chooses the role
of a line of a quote (WF-DEV-0020, #1745). The deactivated ones, and every write, ask for the
permission to change the resource settings (``resource_settings.write``, WF-ADM-0100; the decision
of the author, #2084). A role is described with the commands its caller may exercise.

The resource settings do not read the cost settings, which read them: the route asks the cost
settings what a role is told of its category (``waterfall.api.resource_role_admission``), the label
of each category it names, and the label a list sorts the categories by (``category_label_of``).
"""

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, BeforeValidator, StringConstraints

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel, Text
from waterfall.api.contract.models import (
    LockVersion,
    PaginationMeta,
    ResourceRole,
    ResourceRoleUpdate,
    ResourceRoleWrite,
    RoleCapacity,
    SortOrder,
)
from waterfall.api.evaluation import Acting, Requires, RequiresForInactive
from waterfall.api.queries import refuse_query
from waterfall.api.resource_role_admission import (
    category_admission,
    category_admission_for_change,
)
from waterfall.core.cost_settings.interface import category_label_of, category_labels
from waterfall.core.resource_settings.interface import (
    Capacity,
    RoleChange,
    RoleColumn,
    RoleDraft,
    RoleFilters,
    RoleSort,
    RoleView,
    RoleWindow,
    create_role,
    list_roles,
    set_role_activation,
    update_role,
)
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from sqlalchemy.orm import Session

router = APIRouter(tags=["reference"])

CHANGE = "resource_settings.write"
NUMBER_INVALID = "NUMBER_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# Any open session reads the active roles; ``Requires()`` asks nothing but the session, and comes
# before the guard of the deactivated ones, which a caller who may not read would otherwise be told.
READ = [Depends(Requires()), Depends(RequiresForInactive(CHANGE))]
WRITE = [Depends(Requires(CHANGE))]
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
# A decimal as the contract writes it (``Decimal``), in digits of 0 to 9: a bound of the capacity.
DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
# The attachments a body may send null, read as absent: lacking (``VALUE_REQUIRED``, WF-REF-0090).
# A change has no node to lack: its ``org_node_id`` is optional, never null (``node_sent_null``).
CREATION_ATTACHMENTS = frozenset({"org_node_id", "cost_category_id", "calendar_id"})
CHANGE_ATTACHMENTS = CREATION_ATTACHMENTS - {"org_node_id"}


class ActivationBody(ContractModel):
    """The body of ``setResourceRoleActivation``: the state asked for, at the version read."""

    is_active: bool
    lock_version: LockVersion


def _lacking(attachments: frozenset[str]) -> Callable[[object], object]:
    """Give the reading of a body that takes those attachments sent null as absent."""

    def read(body: object) -> object:
        if not isinstance(body, dict):
            return body
        sent = cast("dict[str, object]", body)
        return {
            name: value
            for name, value in sent.items()
            if name not in attachments or value is not None
        }

    return read


type CreationBody = Annotated[
    ResourceRoleWrite, BeforeValidator(_lacking(CREATION_ATTACHMENTS)), Body()
]
type ChangeBody = Annotated[
    ResourceRoleUpdate, BeforeValidator(_lacking(CHANGE_ATTACHMENTS)), Body()
]


def node_sent_null(body: ResourceRoleUpdate) -> None:
    """Refuse a change that sends the node null (422): optional, it is never null (contract)."""
    if "org_node_id" in body.model_fields_set and body.org_node_id is None:
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError("/org_node_id", VALIDATION_FAILED),)
        )


def _plain(value: Decimal) -> str:
    """Write a decimal as it was given, with its decimals and without an exponent: ``520.00``."""
    return format(value, "f")


def capacity_of(capacity: RoleCapacity) -> Capacity:
    """Read the capacity a body sends, two decimals as the contract writes them."""
    return Capacity(Decimal(capacity.monthly_hours.root.root), Decimal(capacity.headcount.root))


def described(session: Session, views: Sequence[RoleView]) -> list[ResourceRole]:
    """Describe roles as the contract does: their category and their authors named as they are."""
    categories = category_labels(session, {view.cost_category_id for view in views})
    authors = read_authors(
        session,
        {
            author
            for view in views
            for author in (view.created_by, view.updated_by)
            if author is not None
        },
    )
    return [
        ResourceRole.model_validate(
            {
                "resource_role_id": view.resource_role_id,
                "code": view.code,
                "label": view.label,
                "org_node_id": view.org_node_id,
                "org_node_label": view.org_node_label,
                "cost_category_id": view.cost_category_id,
                "cost_category_label": categories[view.cost_category_id].label,
                "calendar_id": view.calendar_id,
                "calendar_label": view.calendar_label,
                "capacity": {
                    "monthly_hours": _plain(view.capacity.monthly_hours),
                    "headcount": _plain(view.capacity.headcount),
                },
                "is_active": view.is_active,
                "available_commands": [
                    {
                        "command": command.command,
                        "is_available": command.is_available,
                        "missing_conditions": list(command.missing_conditions),
                    }
                    for command in view.commands
                ],
                "audit": {
                    "created_at": view.created_at,
                    "created_by": actor_ref(
                        None if view.created_by is None else authors.get(view.created_by)
                    ),
                    "updated_at": view.updated_at,
                    "updated_by": actor_ref(
                        None if view.updated_by is None else authors.get(view.updated_by)
                    ),
                },
                "lock_version": view.lock_version,
            }
        )
        for view in views
    ]


def _bound(name: str, text: str | None) -> tuple[Decimal | None, FieldError | None]:
    """Read a bound of the capacity as a decimal (``NUMBER_INVALID`` at the parameter if none)."""
    if text is None:
        return None, None
    if DECIMAL.fullmatch(text) is None:
        return None, FieldError(f"/query/{name}", NUMBER_INVALID)
    return Decimal(text), None


def _bounds(
    column: str, low_text: str | None, high_text: str | None
) -> tuple[Decimal | None, Decimal | None, list[FieldError]]:
    """Read the two bounds of a column of the capacity, and their faults.

    An upper bound under the lower one is a fault at the upper bound, the lower one its minimum.
    """
    low, low_fault = _bound(f"{column}_min", low_text)
    high, high_fault = _bound(f"{column}_max", high_text)
    faults = [fault for fault in (low_fault, high_fault) if fault is not None]
    if low is not None and high is not None and high < low:
        faults.append(FieldError(f"/query/{column}_max", VALUE_OUT_OF_RANGE, {"minimum": low_text}))
    return low, high, faults


class RolesQuery(BaseModel):
    """The filters of the query of the roles, as the contract names them.

    The bounds of the capacity are read as texts, and judged as decimals by ``role_filters``.
    """

    search: Annotated[Text | None, StringConstraints(min_length=1, max_length=200)] = None
    code: Annotated[Text | None, StringConstraints(min_length=1, max_length=20)] = None
    org_node_id: UUID | None = None
    cost_category_id: UUID | None = None
    calendar_id: UUID | None = None
    include_inactive: bool = False
    is_active: bool | None = None
    monthly_hours_min: str | None = None
    monthly_hours_max: str | None = None
    headcount_min: str | None = None
    headcount_max: str | None = None


def role_filters(query: Annotated[RolesQuery, Query()]) -> RoleFilters:
    """Read the filters of the table of the roles; a bound malformed or inverted is refused (422).

    ``is_active`` keeps one state and prevails over ``include_inactive``, which only adds the
    deactivated roles to the active ones (WF-IHM-0130, WF-REF-0150). All the faults of the bounds
    are named at once.
    """
    hours_low, hours_high, hours_faults = _bounds(
        "monthly_hours", query.monthly_hours_min, query.monthly_hours_max
    )
    heads_low, heads_high, heads_faults = _bounds(
        "headcount", query.headcount_min, query.headcount_max
    )
    refuse_query([*hours_faults, *heads_faults])
    if query.is_active is None:
        states = frozenset({True, False}) if query.include_inactive else frozenset({True})
    else:
        states = frozenset({query.is_active})
    return RoleFilters(
        query.search,
        query.code,
        query.org_node_id,
        query.cost_category_id,
        query.calendar_id,
        states,
        hours_low,
        hours_high,
        heads_low,
        heads_high,
    )


def role_sort(sort_by: RoleColumn = "label", sort_order: SortOrder = SortOrder.asc) -> RoleSort:
    """Read the sort the table of the roles asks for: the label unless said otherwise."""
    return RoleSort(category_label_of, sort_by, descending=sort_order is SortOrder.desc)


def role_window(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RoleWindow:
    """Read the page asked for: fifty roles from the first one, unless said otherwise."""
    return RoleWindow(limit, offset)


@router.get(
    "/reference/resource-roles",
    operation_id="listResourceRoles",
    dependencies=READ,
    response_model=None,
)
def get_resource_roles(
    actor: Acting,
    session: Transaction,
    filters: Annotated[RoleFilters, Depends(role_filters)],
    sort: Annotated[RoleSort, Depends(role_sort)],
    window: Annotated[RoleWindow, Depends(role_window)],
) -> dict[str, object]:
    """Give a page of the roles, filtered, sorted and counted by the server (WF-REF-0090, 0100)."""
    page = list_roles(
        session,
        filters,
        sort,
        window,
        may_change=CHANGE in actor.permissions,
    )
    meta = PaginationMeta(limit=window.limit, offset=window.offset, total=page.total)
    return {
        "items": [
            role.model_dump(mode="json", exclude_unset=True)
            for role in described(session, page.roles)
        ],
        "meta": meta.model_dump(),
    }


@router.post(
    "/reference/resource-roles",
    operation_id="createResourceRole",
    dependencies=WRITE,
    status_code=201,
    response_model_exclude_unset=True,
)
def post_resource_role(body: CreationBody, account: Caller, session: Transaction) -> ResourceRole:
    """Create an active role under an active node, a category of labour and a calendar."""
    category_id = body.cost_category_id.root
    draft = RoleDraft(
        body.code,
        body.label,
        body.org_node_id.root,
        category_id,
        category_admission(session, category_id),
        body.calendar_id.root,
        capacity_of(body.capacity),
    )
    created = create_role(session, draft, Act(account.user_id, utc_now()))
    return described(session, [created])[0]


@router.patch(
    "/reference/resource-roles/{resource_role_id}",
    operation_id="updateResourceRole",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def patch_resource_role(
    resource_role_id: UUID, body: ChangeBody, account: Caller, session: Transaction
) -> ResourceRole:
    """Change a role, never its node: its category and its calendar towards active ones."""
    node_sent_null(body)
    category_id = body.cost_category_id.root
    change = RoleChange(
        body.code,
        body.label,
        None if body.org_node_id is None else body.org_node_id.root,
        category_id,
        category_admission_for_change(
            session, resource_role_id, category_id, body.lock_version.root
        ),
        body.calendar_id.root,
        capacity_of(body.capacity),
    )
    act = Act(account.user_id, utc_now())
    changed = update_role(session, resource_role_id, change, body.lock_version.root, act)
    return described(session, [changed])[0]


@router.put(
    "/reference/resource-roles/{resource_role_id}/activation",
    operation_id="setResourceRoleActivation",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_resource_role_activation(
    resource_role_id: UUID, body: ActivationBody, account: Caller, session: Transaction
) -> ResourceRole:
    """Deactivate a role, or reactivate it under an active node (WF-REF-0080)."""
    act = Act(account.user_id, utc_now())
    changed = set_role_activation(
        session,
        resource_role_id,
        is_active=body.is_active,
        lock_version=body.lock_version.root,
        act=act,
    )
    return described(session, [changed])[0]
