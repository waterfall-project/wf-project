# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The accounts: the operations of the family ``users`` that read them.

Each asks for the permission to consult the accounts (WF-ADM-0110): without it, an account does
not exist for the caller (404). An account is read with the roles it holds, named by the server
in the order it holds them, and with the commands its reader may exercise, each available or not
(WF-IHM-0090).
"""

from collections.abc import Sequence
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import PaginationMeta, SortOrder, User, UserOrigin
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import Search, listed
from waterfall.core.access_roles.interface import (
    Actor,
    HeldRole,
    holding_one_of,
    labels_held,
    roles_held_by,
    sole_administrator,
)
from waterfall.core.users.interface import (
    Account,
    AccountColumn,
    AccountFilters,
    AccountSort,
    Page,
    account_commands,
    list_accounts,
    read_account,
)

router = APIRouter(tags=["users"])

CONSULTATION = "users.read"
CHANGE = "users.write"
READ = [Depends(Requires(CONSULTATION))]
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500

type UserColumn = Literal[
    "last_name", "first_name", "email", "origin", "access_roles", "org_node", "is_active"
]


def account_fields(account: Account, roles: Sequence[HeldRole]) -> dict[str, object]:
    """Describe an account as the contract does, without what only one reading adds to it.

    The roles are named by the server, in the order the account holds them (WF-ARC-0020). The
    attachment to the organisation arrives with EP-05.
    """
    return {
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
    }


def users(session: Session, actor: Actor, accounts: Sequence[Account]) -> list[User]:
    """Describe accounts for the table, each with its roles and the commands its reader may use."""
    held = roles_held_by(session, [account.user_id for account in accounts])
    may_change = CHANGE in actor.permissions
    last = sole_administrator(session) if may_change else None
    described: list[User] = []
    for account in accounts:
        commands = account_commands(
            is_active=account.is_active,
            is_last_administrator=account.user_id == last,
            may_change=may_change,
        )
        fields = account_fields(account, held[account.user_id])
        fields["available_commands"] = [
            {
                "command": command.command,
                "is_available": command.is_available,
                "missing_conditions": list(command.missing_conditions),
            }
            for command in commands
        ]
        described.append(User.model_validate(fields))
    return described


def account_states(
    *, include_inactive: bool = False, is_active: bool | None = None
) -> frozenset[str]:
    """Read the states the table keeps.

    ``is_active`` keeps one state and prevails over ``include_inactive``, which only adds the
    deactivated accounts to the active ones (WF-IHM-0130, WF-ADM-0060).
    """
    if is_active is None:
        return frozenset({"active", "deactivated"} if include_inactive else {"active"})
    return frozenset({"active" if is_active else "deactivated"})


def account_filters(
    states: Annotated[frozenset[str], Depends(account_states)],
    search: Search = None,
    origins: Text | None = None,
    org_node_id: UUID | None = None,
    access_role_ids: Text | None = None,
) -> AccountFilters:
    """Read the filters of the table; a list holds its values separated by commas."""
    kept_origins = listed("origins", origins, UserOrigin)
    roles = listed("access_role_ids", access_role_ids, UUID)
    return AccountFilters(
        search=search,
        origins=None if kept_origins is None else frozenset(kept_origins),
        states=states,
        org_node_id=org_node_id,
        held=None if roles is None else holding_one_of(roles),
    )


def account_sort(
    sort_by: UserColumn | None = None, sort_order: SortOrder = SortOrder.asc
) -> AccountSort:
    """Read the sort the table asks for; the roles by their labels, which their module computes."""
    descending = sort_order is SortOrder.desc
    if sort_by == "access_roles":
        return AccountSort(labels_held, descending=descending)
    column: AccountColumn | None = sort_by
    return AccountSort(column, descending=descending)


def page_of(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page:
    """Read the page asked for: fifty accounts from the first one, unless said otherwise."""
    return Page(limit, offset)


# The platform as an author has no account: its absent fields stay absent, not null.
@router.get("/users", operation_id="listUsers", dependencies=READ, response_model=None)
def get_users(
    actor: Acting,
    session: Transaction,
    filters: Annotated[AccountFilters, Depends(account_filters)],
    sort: Annotated[AccountSort, Depends(account_sort)],
    page: Annotated[Page, Depends(page_of)],
) -> dict[str, object]:
    """Give a page of the table of the accounts, filtered and sorted by the server (WF-ADM-0050)."""
    read = list_accounts(session, filters, sort, page)
    meta = PaginationMeta(limit=page.limit, offset=page.offset, total=read.total)
    return {
        "items": [
            user.model_dump(mode="json", exclude_unset=True)
            for user in users(session, actor, read.accounts)
        ],
        "meta": meta.model_dump(),
    }


@router.get(
    "/users/{user_id}",
    operation_id="getUser",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_user(user_id: UUID, actor: Acting, session: Transaction) -> User:
    """Give an account, with its roles and its commands (WF-ADM-0050)."""
    return users(session, actor, [read_account(session, user_id)])[0]
