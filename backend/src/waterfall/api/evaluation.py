# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evaluation of each operation against the permissions of its caller (WF-ADM-0110).

The caller is read once per request — its account, then its effective permissions — and every
operation the contract guards declares the permissions it asks for, by a dependency of its route
that runs before anything else of it: a refusal never depends on what the request carries, and
nothing the front presented or hid lets a caller past it.
"""

from typing import Annotated

from fastapi import Depends

from waterfall.api.authentication import Caller, Transaction
from waterfall.core.access_roles.interface import Actor, actor_of, require


def acting(account: Caller, session: Transaction) -> Actor:
    """Give the caller as an action is evaluated: its account and its effective permissions."""
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
