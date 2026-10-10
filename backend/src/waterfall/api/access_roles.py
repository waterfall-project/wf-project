# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The catalogue of permissions and the roles: the operations of the family ``access`` on them.

The evaluation of the permission each operation asks for arrives with US-0390: until then, any
account the API knows may call them. A write is inscribed in the journal of audit by its caller.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from waterfall.api.actors import actor_ref, audit_actor
from waterfall.api.authentication import Caller, Transaction, caller
from waterfall.api.contract.models import (
    AccessRole,
    AccessRoleUpdate,
    AccessRoleWrite,
    Permission,
    SortOrder,
)
from waterfall.api.queries import Search
from waterfall.core.access_roles.interface import (
    Act,
    RoleFilters,
    RoleSort,
    RoleView,
    RoleWrite,
    SortColumn,
    create_role,
    delete_role,
    list_permissions,
    list_roles,
    read_role,
    update_role,
)
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError, UnprocessableError

router = APIRouter(tags=["access"])

VALIDATION_FAILED = "VALIDATION_FAILED"
NUMBER_INVALID = "NUMBER_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# The greatest integer PostgreSQL represents (``bigint``).
GREATEST_COUNT = 2**63 - 1

# The reads need the caller known and active, but nothing of it; a write names it its author.
AUTHENTICATED = [Depends(caller)]


def access_role(view: RoleView) -> AccessRole:
    """Describe a role as the contract does."""
    return AccessRole.model_validate(
        {
            "access_role_id": view.access_role_id,
            "label": view.label,
            "permissions": list(view.permissions),
            "is_predefined": view.is_predefined,
            "holder_count": view.holder_count,
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(view.created_by),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(view.updated_by),
            },
            "lock_version": view.lock_version,
        }
    )


@router.get("/permissions", operation_id="listPermissions", dependencies=AUTHENTICATED)
def get_permissions(session: Transaction) -> list[Permission]:
    """Give the catalogue, in its order: it is delivered, and nothing creates a permission."""
    return [
        Permission.model_validate(
            {"code": entry.code, "kind": entry.kind, "fbs_code": entry.fbs_code}
        )
        for entry in list_permissions(session)
    ]


def role_filters(
    *,
    search: Search = None,
    is_predefined: bool | None = None,
    holder_count_min: int | None = None,
    holder_count_max: int | None = None,
) -> RoleFilters:
    """Read the filters of the table; a bound that is negative, or inverted, is refused (422).

    The contract calls a negative bound a malformed number (``NUMBER_INVALID``), and an upper
    bound under the lower one out of its range, the lower one as its minimum. It sets no maximum:
    a bound beyond the integers of PostgreSQL, which no count reaches, is brought back to the
    greatest of them, and keeps what it would have kept.
    """
    faults = [
        FieldError(f"/query/{name}", NUMBER_INVALID)
        for name, bound in (
            ("holder_count_min", holder_count_min),
            ("holder_count_max", holder_count_max),
        )
        if bound is not None and bound < 0
    ]
    if (
        not faults
        and holder_count_min is not None
        and holder_count_max is not None
        and holder_count_max < holder_count_min
    ):
        faults.append(
            FieldError("/query/holder_count_max", VALUE_OUT_OF_RANGE, {"minimum": holder_count_min})
        )
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return RoleFilters(
        search,
        is_predefined,
        None if holder_count_min is None else min(holder_count_min, GREATEST_COUNT),
        None if holder_count_max is None else min(holder_count_max, GREATEST_COUNT),
    )


# The platform as an author has no account: its absent fields stay absent, not null.
@router.get(
    "/access-roles",
    operation_id="listAccessRoles",
    dependencies=AUTHENTICATED,
    response_model_exclude_unset=True,
)
def get_access_roles(
    session: Transaction,
    filters: Annotated[RoleFilters, Depends(role_filters)],
    sort_by: SortColumn = "label",
    sort_order: SortOrder = SortOrder.asc,
) -> list[AccessRole]:
    """Give the whole table of the roles not deleted, filtered and sorted by the server."""
    sort = RoleSort(sort_by, descending=sort_order is SortOrder.desc)
    return [access_role(view) for view in list_roles(session, filters, sort)]


@router.get(
    "/access-roles/{access_role_id}",
    operation_id="getAccessRole",
    dependencies=AUTHENTICATED,
    response_model_exclude_unset=True,
)
def get_access_role(access_role_id: UUID, session: Transaction) -> AccessRole:
    """Give a role that is not deleted."""
    return access_role(read_role(session, access_role_id))


def _write(body: AccessRoleWrite) -> RoleWrite:
    return RoleWrite(body.label, [code.value for code in body.permissions])


@router.post(
    "/access-roles",
    operation_id="createAccessRole",
    status_code=201,
    response_model_exclude_unset=True,
)
def post_access_role(body: AccessRoleWrite, account: Caller, session: Transaction) -> AccessRole:
    """Compose a role of any set of permissions (WF-ADM-0020)."""
    return access_role(create_role(session, _write(body), Act(audit_actor(account), utc_now())))


@router.patch(
    "/access-roles/{access_role_id}",
    operation_id="updateAccessRole",
    response_model_exclude_unset=True,
)
def patch_access_role(
    access_role_id: UUID, body: AccessRoleUpdate, account: Caller, session: Transaction
) -> AccessRole:
    """Rename a role and set its permissions, for all its holders at once (WF-ADM-0090)."""
    act = Act(audit_actor(account), utc_now())
    changed = update_role(session, access_role_id, _write(body), body.lock_version.root, act)
    return access_role(changed)


@router.delete("/access-roles/{access_role_id}", operation_id="deleteAccessRole", status_code=204)
def remove_access_role(access_role_id: UUID, account: Caller, session: Transaction) -> Response:
    """Mark a role deleted, unless an account holds it (WF-ADM-0090)."""
    delete_role(session, access_role_id, Act(audit_actor(account), utc_now()))
    return Response(status_code=204)
