# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The natures of cost.

Read, listed, created, changed, deactivated and reactivated (WF-REF-0030).

A nature has one of three kinds, labour, non labour or provision for risks; its code is unique
among the natures, deactivated ones included. No category exists yet to bind its kind: the change
of its kind is offered and accepted (the categories come with US-0820b).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, func, insert, not_, or_, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.cost_settings.commands import CommandAvailability, cost_type_commands
from waterfall.core.cost_settings.records import (
    Audit,
    Page,
    already_exists,
    audits_of,
    change_row,
    identifier_taken,
    lock_row,
    value_taken,
)
from waterfall.core.cost_settings.tables import CostType
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy import SQLColumnExpression
    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

CODE_INDEX = "uq_cost_type_code"
IDENTIFIER_INDEX = "pk_cost_type"

type TypeColumn = Literal["code", "label", "kind", "is_active"]


@dataclass(frozen=True, slots=True)
class CostTypeView:
    """A nature as it is read: its kind, its commands, its audit."""

    cost_type_id: UUID
    code: str
    label: str
    kind: str
    is_active: bool
    commands: tuple[CommandAvailability, ...]
    audit: Audit


@dataclass(frozen=True, slots=True)
class CostTypeFilters:
    """What the table keeps; a filter absent keeps everything (WF-IHM-0130).

    ``states`` are the values of ``is_active`` kept: the active natures alone unless asked.
    """

    search: str | None = None
    kinds: frozenset[str] | None = None
    states: frozenset[bool] = frozenset({True})


@dataclass(frozen=True, slots=True)
class CostTypeSort:
    """The column of the sort and its direction; the code unless said otherwise (WF-IHM-0060)."""

    column: TypeColumn = "code"
    descending: bool = False


@dataclass(frozen=True, slots=True)
class CostTypePage:
    """A page of the natures the filters keep, and how many they keep in all."""

    types: list[CostTypeView]
    total: int


@dataclass(frozen=True, slots=True)
class CostTypeDraft:
    """What a nature is created or changed with."""

    code: str
    label: str
    kind: str


def _views(
    session: Session, natures: Sequence[CostType], *, may_change: bool
) -> list[CostTypeView]:
    audits = audits_of(session, natures)
    return [
        CostTypeView(
            cost_type_id=nature.id,
            code=nature.code,
            label=nature.label,
            kind=nature.kind,
            is_active=nature.is_active,
            commands=cost_type_commands(is_active=nature.is_active, may_change=may_change),
            audit=audit,
        )
        for nature, audit in zip(natures, audits, strict=True)
    ]


def _criteria(filters: CostTypeFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [CostType.is_active.in_(filters.states)]
    if filters.search is not None:
        criteria.append(
            or_(contains(CostType.code, filters.search), contains(CostType.label, filters.search))
        )
    if filters.kinds is not None:
        criteria.append(CostType.kind.in_(filters.kinds))
    return criteria


def _key(column: TypeColumn) -> SQLColumnExpression[object]:
    keys: dict[TypeColumn, SQLColumnExpression[object]] = {
        "code": CostType.code,
        "label": CostType.label,
        "kind": CostType.kind,
        # False before true: the active natures first in the ascending order.
        "is_active": not_(CostType.is_active),
    }
    return keys[column]


def list_cost_types(
    session: Session,
    filters: CostTypeFilters,
    sort: CostTypeSort,
    page: Page,
    *,
    may_change: bool,
) -> CostTypePage:
    """Read a page of the natures the filters keep, in the order of the sort, and count them all.

    Equals are ordered as the table is unsorted — by the code — then by identifier, ascending
    whatever the direction (WF-IHM-0060). A page beyond the last one is empty, and counts the same.
    ``may_change``: the reader may change the cost settings, which gives the commands.
    """
    criteria = _criteria(filters)
    total = session.scalars(select(func.count()).select_from(CostType).where(*criteria)).one()
    asked = _key(sort.column)
    order = (asked.desc() if sort.descending else asked, CostType.code, CostType.id)
    natures = session.scalars(
        select(CostType).where(*criteria).order_by(*order).limit(page.limit).offset(page.offset)
    ).all()
    return CostTypePage(_views(session, natures, may_change=may_change), total)


def _read_view(session: Session, type_id: UUID) -> CostTypeView:
    nature = session.get_one(CostType, type_id, populate_existing=True)
    return _views(session, [nature], may_change=True)[0]


def present_cost_types(session: Session, type_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the identifiers given, those a nature bears: the witness looks for its own."""
    return frozenset(session.scalars(select(CostType.id).where(CostType.id.in_(type_ids))))


def _refuse_taken(session: Session, code: str, *, besides: UUID | None) -> None:
    """Refuse a code another nature holds, deactivated or not, naming it (409)."""
    query = select(CostType.id).where(CostType.code == code)
    if besides is not None:
        query = query.where(CostType.id != besides)
    holder = session.scalars(query).first()
    if holder is not None:
        raise already_exists([value_taken("/code", holder)])


def _collision(
    session: Session, error: IntegrityError, write: CostTypeDraft, type_id: UUID
) -> Exception:
    """Say which rule a write broke, when a concurrent one took the code first (409)."""
    broken = unique_violated(error)
    if broken == IDENTIFIER_INDEX:
        return identifier_taken(type_id)
    if broken == CODE_INDEX:
        holder = session.scalars(
            select(CostType.id).where(CostType.code == write.code, CostType.id != type_id)
        ).first()
        if holder is not None:
            return already_exists([value_taken("/code", holder)])
    return error


def create_cost_type(
    session: Session, write: CostTypeDraft, act: Act, *, identifier: UUID | None = None
) -> CostTypeView:
    """Create an active nature of one of the three kinds, with a code no nature holds.

    A code another nature holds, deactivated or not, is refused naming it (409): the unique index
    decides when two creations meet, the second one waits for the first and is refused. The
    identifier is the one the loader of the witness imposes: one already borne is refused (409),
    the API gives none.
    """
    _refuse_taken(session, write.code, besides=None)
    type_id = new_id() if identifier is None else identifier
    try:
        with session.begin_nested():
            session.execute(
                insert(CostType).values(
                    id=type_id,
                    code=write.code,
                    label=write.label,
                    kind=write.kind,
                    is_active=True,
                    created_at=act.at,
                    created_by=act.author,
                    updated_at=act.at,
                    updated_by=act.author,
                )
            )
    except IntegrityError as error:
        raise _collision(session, error, write, type_id) from None
    return _read_view(session, type_id)


def update_cost_type(
    session: Session, type_id: UUID, write: CostTypeDraft, lock_version: int, act: Act
) -> CostTypeView:
    """Change the code, the label and the kind of a nature whose version is the one read.

    Refused if unknown (404) or stale (412); a code another nature holds (409).
    """
    lock_row(session, CostType, type_id, lock_version)
    _refuse_taken(session, write.code, besides=type_id)
    values: dict[str, object] = {"code": write.code, "label": write.label, "kind": write.kind}
    try:
        with session.begin_nested():
            change_row(session, CostType, type_id, values, (lock_version, act))
    except IntegrityError as error:
        raise _collision(session, error, write, type_id) from None
    return _read_view(session, type_id)


def set_cost_type_activation(
    session: Session, type_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> CostTypeView:
    """Deactivate or reactivate a nature whose version is the one read.

    Refused if unknown (404) or stale (412). A nature already in the state asked for is not
    written. Its categories follow it when they exist (US-0820b).
    """
    nature = lock_row(session, CostType, type_id, lock_version)
    if nature.is_active != is_active:
        change_row(session, CostType, type_id, {"is_active": is_active}, (lock_version, act))
    return _read_view(session, type_id)
