# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the family ``me``: the account of the caller, and closing its sessions."""

from fastapi import APIRouter, Response

from waterfall.api.authentication import Caller, ServicesOf
from waterfall.api.contract.models import ActorRef, UserSelf
from waterfall.core.users.interface import Account, Author
from waterfall.platform.logs import get_logger

router = APIRouter(tags=["me"])

logger = get_logger(__name__)


def _actor(author: Author | None) -> ActorRef:
    if author is None:
        return ActorRef.model_validate({"kind": "platform"})
    return ActorRef.model_validate(
        {"kind": "user", "user_id": author.user_id, "display_name": author.display_name}
    )


def user_self(account: Account) -> UserSelf:
    """Describe the account to the person who holds it.

    The roles of accounts arrive with US-0380: until then an account holds none, and so no
    permission (WF-ADM-0180). The attachment to the organisation arrives with EP-05.
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
            "access_role_ids": [],
            "access_role_labels": [],
            "has_avatar": account.has_avatar,
            "audit": {
                "created_at": account.created_at,
                "created_by": _actor(account.created_by),
                "updated_at": account.updated_at,
                "updated_by": _actor(account.updated_by),
            },
            "lock_version": account.lock_version,
            "display_preferences": account.display_preferences,
            "permissions": [],
        }
    )


@router.get("/me", operation_id="getMe", response_model_exclude_unset=True)
def get_me(account: Caller) -> UserSelf:
    """Give the account of the caller; a preference never chosen is absent, not null."""
    return user_self(account)


@router.delete("/me/sessions", operation_id="closeMySessions", status_code=204)
def close_my_sessions(account: Caller, services: ServicesOf) -> Response:
    """Close every session of the caller, on every device: its tokens no longer serve."""
    services.keycloak.close_sessions(account.subject)
    logger.info("sessions.closed")
    return Response(status_code=204)
