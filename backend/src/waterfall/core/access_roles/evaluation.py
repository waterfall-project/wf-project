# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The effective permissions of an account, and the evaluation of an action against them.

The effective permissions of an account are the union of those of its roles that are not deleted
(WF-ADM-0090), read at each request: a role changed applies to its holders at their next request,
without their signing in again. An action is evaluated when it is asked for, whatever the front
presented (WF-ADM-0110). A permission to consult that is missing makes the object absent for the
caller: the refusal is that of an unknown object, which does not reveal that it exists (404). Any
other permission that is missing is named by the refusal (403). The quality of contributor, the
second term of the evaluation, arrives with EP-04.
"""

from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from waterfall.core.access_roles.roles import NOT_FOUND
from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.platform.errors import ForbiddenError, NotFoundError

PERMISSION_MISSING = "PERMISSION_MISSING"
# The permission to consult a function ends so; that to change it, ``.write`` (``PermissionCode``).
CONSULTATION = ".read"


@dataclass(frozen=True, slots=True)
class Actor:
    """Who asks for an action: an account and its effective permissions, read once per request."""

    user_id: UUID
    # In the order of the catalogue, each once.
    permissions: tuple[str, ...]


def effective_permissions(session: Session, user_id: UUID) -> tuple[str, ...]:
    """Give the permissions the roles of an account grant, deleted roles apart, in catalogue order.

    An account without any role has none (WF-ADM-0180).
    """
    held = select(UserAccessRole.access_role_id).where(UserAccessRole.user_account_id == user_id)
    return _granted(session, AccessRole.id.in_(held))


def granted_permissions(session: Session, role_ids: Collection[UUID]) -> tuple[str, ...]:
    """Give the permissions these roles grant, deleted roles apart, in catalogue order.

    For a reader that has already read the roles an account holds, and describes both from the
    same reading.
    """
    return _granted(session, AccessRole.id.in_(role_ids))


def _granted(session: Session, roles: ColumnElement[bool]) -> tuple[str, ...]:
    return tuple(
        session.scalars(
            select(Permission.code)
            .join(AccessRolePermission, AccessRolePermission.permission_id == Permission.id)
            .join(AccessRole, AccessRole.id == AccessRolePermission.access_role_id)
            .where(roles, AccessRole.deleted_at.is_(None))
            .group_by(Permission.code, Permission.position)
            .order_by(Permission.position)
        )
    )


def actor_of(session: Session, user_id: UUID) -> Actor:
    """Read the actor an account is: the account and its effective permissions at this moment."""
    return Actor(user_id, effective_permissions(session, user_id))


def require(actor: Actor, permission: str) -> None:
    """Let the action pass if the actor holds ``permission``, or refuse it.

    A permission to consult that is missing is refused as an unknown object (404 ``NOT_FOUND``);
    any other, by 403 ``PERMISSION_MISSING``, ``params.missing_permission`` naming it.
    """
    if permission in actor.permissions:
        return
    if permission.endswith(CONSULTATION):
        raise NotFoundError(NOT_FOUND)
    raise ForbiddenError(PERMISSION_MISSING, {"missing_permission": permission})
