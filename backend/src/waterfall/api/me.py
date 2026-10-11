# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the family ``me``: the account of the caller, and closing its sessions."""

from fastapi import APIRouter, Response

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import UserSelf
from waterfall.api.users import account_fields
from waterfall.core.access_roles.interface import HeldRole, granted_permissions, roles_held
from waterfall.core.users.interface import Account, note_sessions_closed
from waterfall.platform.database import utc_now
from waterfall.platform.logs import get_logger

router = APIRouter(tags=["me"])

logger = get_logger(__name__)


def user_self(account: Account, roles: list[HeldRole], permissions: tuple[str, ...]) -> UserSelf:
    """Describe the account to the person who holds it, with its roles and their permissions.

    The permissions are the effective ones, those a request is evaluated against, so that the
    front presents nothing the API would refuse (WF-ADM-0110).
    """
    return UserSelf.model_validate(
        {
            **account_fields(account, roles),
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

    Any account the API knows closes its own: the operation asks for no permission. The moment is
    noted first, in a transaction of its own: from then on the API refuses every access token
    issued before it, whichever client holds it, without waiting for its expiry (#668). Keycloak
    then closes the sessions, outside of any transaction (#669), so that no refresh token gets a
    new one; while it does not answer, the sign-out is refused as a component unavailable, the
    tokens issued until then refused all the same.
    """
    with services.database.transaction() as session:
        note_sessions_closed(session, account.user_id, utc_now())
    services.keycloak_admin.close_sessions(account.subject)
    logger.info("sessions.closed")
    return Response(status_code=204)
