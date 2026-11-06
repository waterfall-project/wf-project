# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evaluation of each operation against the permissions of its caller (WF-ADM-0110).

The caller is read once per request — its account, then its effective permissions — and every
operation the contract guards declares the permissions it asks for, by a dependency of its route
that runs before the validation of its parameters and body, after the reading of the body: a body
that cannot be read is refused first (400); past it, a refusal never depends on what the request
carries, and nothing the front presented or hid lets a caller past it.
"""

from collections.abc import Mapping
from typing import Annotated, cast

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
    route after its ``Requires``: the dependencies of a route run in their order, and a caller who
    may not read the part of the reference at all must be refused by the ``Requires`` (404), not by
    this (403), which would tell him the list exists. ``test_access_evaluation.py`` checks the
    order of every route that declares it.
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


class RequiresByField:
    """The permission each field of a writing asks for, judged on the fields its body carries.

    The settings the installation shares are written field by field, each under the permission of
    its function (WF-ADM-0100): a field carried — present, whatever its value, a null too, which
    its validation refuses afterwards — whose permission the caller does not hold is refused by 403
    ``PERMISSION_MISSING``, naming the permission of the first such field in the order the route
    declares them, even if the body carries another one the caller may write; nothing is written.
    Like ``Requires``, it runs before the validation of the body, on the body as JSON reads it: a
    body that is no object carries no field, and its validation refuses it afterwards. A body that
    carries no field asks for no permission: its route writes nothing then. Declared on the route
    after its ``Requires``.
    """

    __slots__ = ("permissions",)

    def __init__(self, permissions: Mapping[str, str]) -> None:
        self.permissions = dict(permissions)

    async def __call__(self, request: Request, actor: Acting) -> None:
        """Refuse the writing for the first field carried whose permission the caller lacks."""
        try:
            body: object = await request.json()
        except ValueError:
            return
        if not isinstance(body, dict):
            return
        carried = cast("dict[str, object]", body)
        for name, permission in self.permissions.items():
            if name in carried and permission not in actor.permissions:
                raise ForbiddenError(PERMISSION_MISSING, {"missing_permission": permission})
