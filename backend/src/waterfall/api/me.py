# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the family ``me``: the account of the caller, and closing its sessions."""

from fastapi import APIRouter, Response

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import UserSelf
from waterfall.core.access_roles.interface import HeldRole, granted_permissions, roles_held
from waterfall.core.users.interface import Account
from waterfall.platform.logs import get_logger

router = APIRouter(tags=["me"])

logger = get_logger(__name__)


def user_self(account: Account, roles: list[HeldRole], permissions: tuple[str, ...]) -> UserSelf:
    """Describe the account to the person who holds it, with its roles and their permissions.

    The permissions are the effective ones, those a request is evaluated against, so that the
    front presents nothing the API would refuse (WF-ADM-0110). The attachment to the organisation
    arrives with EP-05.
    """
    return UserSelf.model_validate(
        {
            "user_id": account.user_id,
            "last_name": account.last_name,
            "first_name": account.first_name,
            "email": account.email,
            "is_active": account.is_active,
            "origin": account.origin,
            "org_node_id": None,
            "org_node_label": None,
            "access_role_ids": [held.access_role_id for held in roles],
            "access_role_labels": [held.label for held in roles],
            "has_avatar": account.has_avatar,
            "audit": {
                "created_at": account.created_at,
                "created_by": actor_ref(account.created_by),
                "updated_at": account.updated_at,
                "updated_by": actor_ref(account.updated_by),
            },
            "lock_version": account.lock_version,
            "display_preferences": account.display_preferences,
            "permissions": list(permissions),
        }
    )


@router.get("/me", operation_id="getMe", response_model_exclude_unset=True)
def get_me(account: Caller, session: Transaction) -> UserSelf:
    """Give the account of the caller; a preference never chosen is absent, not null.

    Any account the API knows reads its own: the operation asks for no permission. The roles are
    read once, and the permissions are those of the roles read, so that both say the same.
    """
    roles = roles_held(session, account.user_id)
    permissions = granted_permissions(session, [held.access_role_id for held in roles])
    return user_self(account, roles, permissions)


@router.delete("/me/sessions", operation_id="closeMySessions", status_code=204)
def close_my_sessions(account: Caller, services: ServicesOf) -> Response:
    """Close every session of the caller, on every device: its tokens no longer serve.

    Any account the API knows closes its own: the operation asks for no permission.
    """
    services.keycloak_admin.close_sessions(account.subject)
    logger.info("sessions.closed")
    return Response(status_code=204)
