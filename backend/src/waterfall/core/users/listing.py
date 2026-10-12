# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the accounts, filtered, sorted and read by pages by the server (private).

Every account of the installation, active or deactivated (WF-ADM-0050, WF-ADM-0060), filtered on
each column (WF-IHM-0130) and sorted on each in both directions (WF-IHM-0060): the texts in the
order of the code points, their collation; the origins in the order of their enumeration —
``local``, ``directory``, ``identity_provider`` —, as the journal of audit orders its own, the API
giving no label that a language would order (``docs/api/DECISIONS.md``, #550); the active accounts
before the deactivated in the ascending order; an account without a role after the others in the
ascending order, before in the descending, where the contract puts a cell without a value — an
account without attachment, a project without a code, a line of the actual costs without one.
Equals keep the order of the table unsorted, the name then the first name, then come by identifier,
ascending whatever the direction: no account is read twice nor skipped from one page to the next
(contract, ``listUsers``, #741).

The columns of audit are filtered and sorted as the others (#936): the dates by their instant, the
authors as the journal of audit sorts its own — an account by its displayed name, the first name
then the name, in the order of the code points; in the ascending order, an account anonymised,
which has no name any more, after the names, and the platform, which has none, after the accounts.
The author of a row of another module is sorted so too (``author_order``): an expression on the
table of the accounts, given the column of its author.

The roles an account holds are those of the module of the roles, which reads the accounts: what the
table filters and sorts of them is an expression that module writes on its own tables, given the
column of the identifier of an account (``AccountExpression``), and no table of it is named here
(sql.md, "Le SQL en texte ne nomme pas la table d'un autre module").
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import ColumnElement, SQLColumnExpression, case, false, func, or_, select
from sqlalchemy.orm import Session, aliased

from waterfall.core.users.tables import ORIGINS, UserAccount
from waterfall.platform.audit_columns import AuditColumnFilters, AuditColumns, audit_criteria
from waterfall.platform.database import contains

# What another module says of an account in a query of the accounts: an expression on its own
# tables, given the column of the identifier of the account.
type AccountExpression[T] = Callable[[SQLColumnExpression[UUID]], ColumnElement[T]]

# The columns of the table the accounts hold themselves; the roles are another module's.
type AccountColumn = Literal[
    "last_name",
    "first_name",
    "email",
    "origin",
    "org_node",
    "is_active",
    "created_at",
    "created_by",
    "updated_at",
    "updated_by",
]

ACTIVE = "active"
AUDIT = AuditColumns(
    UserAccount.created_at, UserAccount.created_by, UserAccount.updated_at, UserAccount.updated_by
)


@dataclass(frozen=True, slots=True)
class AccountFilters:
    """What the table keeps; a filter absent keeps everything (WF-IHM-0130).

    ``states`` keeps the active accounts alone unless asked for more. ``held`` is the criterion of
    another module, the roles an account holds. ``audit``, the filters of the columns of audit.
    """

    search: str | None = None
    origins: frozenset[str] | None = None
    states: frozenset[str] = frozenset({ACTIVE})
    org_node_id: UUID | None = None
    held: AccountExpression[bool] | None = None
    audit: AuditColumnFilters = field(default_factory=AuditColumnFilters)


@dataclass(frozen=True, slots=True)
class AccountSort:
    """The key of the sort and its direction (WF-IHM-0060).

    A column of the account, or the key another module computes of it — the labels of the roles
    it holds; ``None``, the order of the table unsorted.
    """

    key: AccountColumn | AccountExpression[Any] | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class Page:
    """Which accounts of the order are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


def _criteria(filters: AccountFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [UserAccount.state.in_(filters.states)]
    if filters.search is not None:
        # The displayed name, the first name then the name, which no column holds whole.
        shown = UserAccount.first_name + " " + UserAccount.last_name
        texts = (UserAccount.last_name, UserAccount.first_name, UserAccount.email, shown)
        criteria.append(or_(*(contains(text, filters.search) for text in texts)))
    if filters.origins is not None:
        criteria.append(UserAccount.origin.in_(filters.origins))
    if filters.org_node_id is not None:
        # No account is attached to a node before EP-05, which adds the column.
        criteria.append(false())
    if filters.held is not None:
        criteria.append(filters.held(UserAccount.id))
    criteria += audit_criteria(AUDIT, filters.audit)
    return criteria


def author_order(author: SQLColumnExpression[UUID | None]) -> tuple[SQLColumnExpression[Any], ...]:
    """Give what a sort on an author compares, in turn, given the column of the author.

    The platform, ``None``, after the accounts, and an account by its displayed name. PostgreSQL
    puts a null last in the ascending order and first in the descending one, as the contract does:
    the name of an account anonymised, null, after the names.
    """
    writer = aliased(UserAccount)
    name = (
        select(writer.first_name + " " + writer.last_name)
        .where(writer.id == author)
        .scalar_subquery()
    )
    return (author.is_(None), name)


def _keys(key: AccountColumn | AccountExpression[Any]) -> tuple[SQLColumnExpression[Any], ...]:
    """Give what a sort compares, in turn; nothing when every account is equal on it."""
    if callable(key):
        return (key(UserAccount.id),)
    keys: dict[AccountColumn, tuple[SQLColumnExpression[Any], ...]] = {
        "last_name": (UserAccount.last_name,),
        "first_name": (UserAccount.first_name,),
        "email": (UserAccount.email,),
        "origin": (
            case({name: rank for rank, name in enumerate(ORIGINS)}, value=UserAccount.origin),
        ),
        # False before true: the active accounts first in the ascending order.
        "is_active": (UserAccount.state != ACTIVE,),
        # No account is attached to a node before EP-05: they are all equal.
        "org_node": (),
        "created_at": (UserAccount.created_at,),
        "created_by": author_order(UserAccount.created_by),
        "updated_at": (UserAccount.updated_at,),
        "updated_by": author_order(UserAccount.updated_by),
    }
    return keys[key]


def find_accounts(
    session: Session, filters: AccountFilters, sort: AccountSort, page: Page
) -> tuple[list[UserAccount], int]:
    """Read a page of the accounts the filters keep, in the order of the sort, and count them all.

    A page beyond the last one is empty, and counts the same.
    """
    criteria = _criteria(filters)
    total = session.scalars(select(func.count()).select_from(UserAccount).where(*criteria)).one()
    keys = () if sort.key is None else _keys(sort.key)
    order: list[SQLColumnExpression[Any]] = [key.desc() if sort.descending else key for key in keys]
    order += [UserAccount.last_name, UserAccount.first_name, UserAccount.id]
    rows = session.scalars(
        select(UserAccount).where(*criteria).order_by(*order).limit(page.limit).offset(page.offset)
    ).all()
    return list(rows), total
