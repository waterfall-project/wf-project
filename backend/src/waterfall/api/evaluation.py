# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evaluation of each operation against the permissions of its caller (WF-ADM-0110).

The caller is read once per request — its account, then its effective permissions — and every
operation the contract guards declares the permissions it asks for, by a dependency of its route
that runs before the validation of its parameters and body, after the reading of the body: a body
that cannot be read is refused first (400); past it, a refusal never depends on what the request
carries, and nothing the front presented or hid lets a caller past it.
"""

from typing import Annotated

from fastapi import Depends, Request
from pydantic import TypeAdapter, ValidationError

from waterfall.api.authentication import Caller, ServicesOf
from waterfall.core.access_roles.interface import PERMISSION_MISSING, Actor, actor_of, require
from waterfall.platform.errors import ForbiddenError

# How a parameter of the query is read as a boolean, as the validation of the route reads it.
BOOLEAN = TypeAdapter(bool)


def acting(account: Caller, services: ServicesOf) -> Actor:
    """Give the caller as an action is evaluated: its account and its effective permissions.

    They are read in a transaction of their own, as the caller is: a route that calls Keycloak
    holds no connection meanwhile (#669).
    """
    with services.database.transaction() as session:
        return actor_of(session, account.user_id)


Acting = Annotated[Actor, Depends(acting)]


class Requires:
    """The permissions an operation asks for, evaluated in their order before it runs.

    A permission to consult comes first: without it, the object of the operation does not exist
    for the caller (404), whatever else it may hold.
    """

    __slots__ = ("permissions",)

    def __init__(self, *permissions: str) -> None:
        self.permissions = permissions

    def __call__(self, actor: Acting) -> None:
        """Refuse the operation for the first permission the caller does not hold."""
        for permission in self.permissions:
            require(actor, permission)


def _flag(value: str | None) -> bool | None:
    """Read a boolean of the query; ``None`` when it is absent or is none."""
    if value is None:
        return None
    try:
        return BOOLEAN.validate_python(value)
    except ValidationError:
        return None


class RequiresForInactive:
    """The permission a list of the reference asks for besides when it asks for deactivated objects.

    ``include_inactive`` true, or ``is_active`` false, ask for them (WF-REF-0150), under the
    permission of the part of the reference the route names; without it, 403 ``PERMISSION_MISSING``
    names it, the refusal the contract declares, a permission to consult included. It is judged on
    the request, not on what it would give: ``include_inactive`` is refused without it even when
    ``is_active`` true makes it vain (contract, ``IsActive``). A value that is no boolean asks for
    nothing here: the validation of the parameters refuses it afterwards (400). Declared on the
    route after its ``Requires``, which comes first.
    """

    __slots__ = ("permission",)

    def __init__(self, permission: str) -> None:
        self.permission = permission

    def __call__(self, request: Request, actor: Acting) -> None:
        """Refuse a request for deactivated objects whose caller lacks the permission."""
        query = request.query_params
        asked = (
            _flag(query.get("include_inactive")) is True or _flag(query.get("is_active")) is False
        )
        if asked and self.permission not in actor.permissions:
            raise ForbiddenError(PERMISSION_MISSING, {"missing_permission": self.permission})
