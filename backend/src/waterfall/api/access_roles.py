# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The catalogue of permissions and the roles: the operations of the family ``access`` on them.

Their writes arrive with the next lot of US-0380, the evaluation of the permission each operation
asks for with US-0390: until then, any account the API knows may read them.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction, caller
from waterfall.api.contract.models import AccessRole, Permission, SortOrder
from waterfall.core.access_roles.interface import (
    RoleFilters,
    RoleSort,
    RoleView,
    SortColumn,
    list_permissions,
    list_roles,
    read_role,
)
from waterfall.platform.errors import FieldError, UnprocessableError

router = APIRouter(tags=["access"])

VALIDATION_FAILED = "VALIDATION_FAILED"
NUMBER_INVALID = "NUMBER_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"

# The reads need the caller known and active, but nothing of it.
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
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    is_predefined: bool | None = None,
    holder_count_min: int | None = None,
    holder_count_max: int | None = None,
) -> RoleFilters:
    """Read the filters of the table; a bound that is negative, or inverted, is refused (422).

    The contract calls a negative bound a malformed number (``NUMBER_INVALID``), and an upper
    bound under the lower one out of its range, the lower one as its minimum.
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
    return RoleFilters(search, is_predefined, holder_count_min, holder_count_max)


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
