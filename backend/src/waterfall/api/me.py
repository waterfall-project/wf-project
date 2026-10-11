# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the family ``me``: the account of the caller, its preferences, its sessions.

Each acts on the caller's own account, and asks for no permission: nobody reads or changes through
them the account of another (WF-ADM-0040). The avatar, the other personal setting, is in
``avatars``.
"""

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, Response

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import DisplayPreferences, GridPreferences, UserSelf
from waterfall.api.users import account_fields
from waterfall.core.access_roles.interface import HeldRole, holding
from waterfall.core.users.interface import (
    Account,
    change_preferences,
    note_sessions_closed,
    refuse,
)
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError, json_pointer
from waterfall.platform.logs import get_logger

router = APIRouter(tags=["me"])

logger = get_logger(__name__)

VALIDATION_FAILED = "VALIDATION_FAILED"
LANGUAGE = "language"
# The origin of an account read from a directory the realm federates.
DIRECTORY = "directory"
# The language that follows the browser, then the installation: the realm's own by default.
FOLLOWED = "default"
# The fields of the preferences, and of the settings of a grid, that the contract never lets null.
NEVER_NULL = (LANGUAGE, "theme", "highlight_tasks_added_after_reference", "grids")
NEVER_NULL_IN_A_GRID = ("hidden_columns", "column_widths", "filters")


def user_self(
    account: Account, roles: Sequence[HeldRole], permissions: tuple[str, ...]
) -> UserSelf:
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

    Any account the API knows reads its own: the operation asks for no permission. The roles and
    the permissions they grant are read in one query, so that both say the same (#756).
    """
    held = holding(session, account.user_id)
    return user_self(account, held.roles, held.permissions)


def null_fields(sent: DisplayPreferences | GridPreferences, names: Sequence[str]) -> list[str]:
    """Name the fields sent null among ``names``: a null, which is not an absence."""
    return [name for name in names if name in sent.model_fields_set and getattr(sent, name) is None]


def preference_change(body: DisplayPreferences) -> dict[str, Any]:
    """Read a change of the preferences: what it carries, each field sent null refused (422).

    A grid sent null is no fault: it finds its settings by default again.
    """
    faults = [
        FieldError(json_pointer(name), VALIDATION_FAILED) for name in null_fields(body, NEVER_NULL)
    ]
    for grid_name, grid in (body.grids or {}).items():
        if grid is not None:
            faults.extend(
                FieldError(json_pointer("grids", grid_name, name), VALIDATION_FAILED)
                for name in null_fields(grid, NEVER_NULL_IN_A_GRID)
            )
    refuse(tuple(faults))
    return body.model_dump(mode="json", exclude_unset=True)


@router.patch(
    "/me/preferences", operation_id="updateMyPreferences", response_model_exclude_unset=True
)
def patch_my_preferences(
    body: DisplayPreferences, account: Caller, services: ServicesOf
) -> DisplayPreferences:
    """Change the preferences of the caller, and give them as they now are (WF-ADM-0040).

    A language chosen is also the account's in the identity provider, which mails in it
    (WF-INTF-0160): the provider is told first, outside of any transaction (#669), and while it
    does not answer nothing is written — the change is never presented as done. The preferences
    are written next. A change that keeps the language — a grid, a theme — does not call it; nor
    does that of an account of a directory, whose attributes are the directory's, which the realm
    federates read only, and which the provider mails nothing (WF-ADM-0140).
    """
    sent = preference_change(body)
    language = sent.get(LANGUAGE)
    chosen = language is not None and language != account.display_preferences.get(
        LANGUAGE, FOLLOWED
    )
    if chosen and account.origin != DIRECTORY:
        locale = None if language == FOLLOWED else language
        services.keycloak_admin.set_locale(account.subject, locale)
    with services.database.transaction() as session:
        # Described before the transaction is committed, as it leaves the block.
        return DisplayPreferences.model_validate(change_preferences(session, account.user_id, sent))


@router.delete("/me/sessions", operation_id="closeMySessions", status_code=204)
def close_my_sessions(account: Caller, services: ServicesOf) -> Response:
    """Close every session of the caller, on every device: its tokens no longer serve.

    Any account the API knows closes its own: the operation asks for no permission. The moment is
    noted first, in a transaction of its own: from then on the API refuses every access token of a
    sign-in before it, whichever client holds it, without waiting for its expiry (#668), and
    refreshed or not (#835). Keycloak then closes the sessions, outside of any transaction (#669),
    so that no refresh token gets a new one; while it does not answer, the sign-out is refused as
    a component unavailable, the tokens of the sessions begun until then refused all the same.
    """
    with services.database.transaction() as session:
        note_sessions_closed(session, account.user_id, utc_now())
    services.keycloak_admin.close_sessions(account.subject)
    logger.info("sessions.closed")
    return Response(status_code=204)
