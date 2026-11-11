# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The categories of cost.

Read, listed, created, changed, deactivated and reactivated (WF-REF-0040); the label and
the kind of the nature of one, for a role of resources.

A category sits under one nature, active when it is created or moved there; its code and its
accounting code are unique among the categories, deactivated ones included. Its kind is that of its
nature: a category is moved to a nature of another kind only if nothing binds it — no line employs
it, no rate is set on it, no role of resources is attached to it —, and its commands say so in
advance, by the very function that refuses the call (``kind_change_missing``). A category is never
reactivated under a nature that is deactivated (WF-REF-0010).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, func, insert, not_, or_, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.cost_settings.commands import (
    CommandAvailability,
    Holdings,
    cost_category_commands,
    kind_change_missing,
)
from waterfall.core.cost_settings.employment import category_is_employed
from waterfall.core.cost_settings.interface.hourly_rates import category_is_rated
from waterfall.core.cost_settings.records import (
    Audit,
    Page,
    already_exists,
    audits_of,
    change_row,
    identifier_taken,
    lock_natures,
    lock_row,
    share_natures,
    value_taken,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import (
    category_has_roles,
    lock_reference,
    roles_of_categories,
)
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

UNKNOWN_COST_TYPE = "UNKNOWN_COST_TYPE"
INACTIVE_REFERENCE_OBJECT = "INACTIVE_REFERENCE_OBJECT"
CODE_INDEX = "uq_cost_category_code"
ACCOUNTING_CODE_INDEX = "uq_cost_category_accounting_code"
IDENTIFIER_INDEX = "pk_cost_category"

type CategoryColumn = Literal["code", "label", "cost_type", "accounting_code", "is_active"]


@dataclass(frozen=True, slots=True)
class CostCategoryView:
    """A category as it is read: its nature named, its commands, its audit."""

    cost_category_id: UUID
    code: str
    label: str
    cost_type_id: UUID
    cost_type_label: str
    cost_type_kind: str
    cost_type_is_active: bool
    accounting_code: str
    is_active: bool
    commands: tuple[CommandAvailability, ...]
    audit: Audit


@dataclass(frozen=True, slots=True)
class CostCategoryFilters:
    """What the table keeps; a filter absent keeps everything (WF-IHM-0130).

    ``states`` are the values of ``is_active`` kept: the active categories alone unless asked.
    """

    search: str | None = None
    cost_type_id: UUID | None = None
    states: frozenset[bool] = frozenset({True})


@dataclass(frozen=True, slots=True)
class CostCategorySort:
    """The column of the sort and its direction; the code unless said otherwise (WF-IHM-0060)."""

    column: CategoryColumn = "code"
    descending: bool = False


@dataclass(frozen=True, slots=True)
class CostCategoryPage:
    """A page of the categories the filters keep, and how many they keep in all."""

    categories: list[CostCategoryView]
    total: int


@dataclass(frozen=True, slots=True)
class CostCategoryDraft:
    """What a category is created or changed with."""

    code: str
    label: str
    accounting_code: str
    cost_type_id: UUID


@dataclass(frozen=True, slots=True)
class CategoryLabel:
    """What a role of resources shows of its category, and what admits it (WF-REF-0090).

    ``cost_type_id`` its nature, by which a line of estimate is filtered (EP-07).
    """

    cost_category_id: UUID
    label: str
    cost_type_kind: str
    is_active: bool
    cost_type_is_active: bool
    cost_type_id: UUID | None = None


def category_holdings(session: Session, category_ids: Collection[UUID]) -> dict[UUID, Holdings]:
    """Say of each category given what binds it: a line, a rate, a role of resources."""
    employed = category_is_employed(session, category_ids)
    rated = category_is_rated(session, category_ids)
    with_roles = category_has_roles(session, category_ids)
    return {
        each: Holdings(each in employed, each in rated, each in with_roles) for each in category_ids
    }


def role_refusal(session: Session, category_ids: Sequence[UUID], missing: str) -> ConflictError:
    """Refuse a change of kind for the first condition a nature or a category lacks (409).

    A role is named, with its code and its label, wherever the refusal is for a role.
    """
    params: dict[str, object] = {"missing_condition": missing}
    if missing.endswith("_without_role"):
        params["resource_roles"] = [
            {"resource_role_id": str(role.resource_role_id), "code": role.code, "label": role.label}
            for role in roles_of_categories(session, category_ids)
        ]
    return ConflictError(STATE_FORBIDS_OPERATION, params)


def _views(
    session: Session, rows: Sequence[tuple[CostCategory, CostType]], *, may_change: bool
) -> list[CostCategoryView]:
    audits = audits_of(session, [category for category, _ in rows])
    held = category_holdings(session, [category.id for category, _ in rows]) if may_change else {}
    return [
        CostCategoryView(
            cost_category_id=category.id,
            code=category.code,
            label=category.label,
            cost_type_id=nature.id,
            cost_type_label=nature.label,
            cost_type_kind=nature.kind,
            cost_type_is_active=nature.is_active,
            accounting_code=category.accounting_code,
            is_active=category.is_active,
            commands=cost_category_commands(
                is_active=category.is_active,
                type_is_active=nature.is_active,
                holdings=held.get(category.id, Holdings()),
                may_change=may_change,
            ),
            audit=audit,
        )
        for (category, nature), audit in zip(rows, audits, strict=True)
    ]


def _criteria(filters: CostCategoryFilters) -> list[ColumnElement[bool]]:
    criteria: list[ColumnElement[bool]] = [CostCategory.is_active.in_(filters.states)]
    if filters.search is not None:
        texts = (CostCategory.code, CostCategory.label, CostCategory.accounting_code)
        criteria.append(or_(*(contains(text, filters.search) for text in texts)))
    if filters.cost_type_id is not None:
        criteria.append(CostCategory.cost_type_id == filters.cost_type_id)
    return criteria


def _keys(column: CategoryColumn) -> tuple[SQLColumnExpression[object], ...]:
    keys: dict[CategoryColumn, tuple[SQLColumnExpression[object], ...]] = {
        "code": (CostCategory.code,),
        "label": (CostCategory.label,),
        # The nature by its label alone: equals are told apart by the code of the category,
        # then by identifier.
        "cost_type": (CostType.label,),
        "accounting_code": (CostCategory.accounting_code,),
        # False before true: the active categories first in the ascending order.
        "is_active": (not_(CostCategory.is_active),),
    }
    return keys[column]


def list_cost_categories(
    session: Session,
    filters: CostCategoryFilters,
    sort: CostCategorySort,
    page: Page,
    *,
    may_change: bool,
) -> CostCategoryPage:
    """Read a page of the categories the filters keep, in the order of the sort, and count them all.

    Equals keep the order of the table unsorted, the code, then come by identifier, ascending
    whatever the direction (WF-IHM-0060). A page beyond the last one is empty, and counts the same.
    ``may_change``: the reader may change the cost settings, which gives the commands.
    """
    criteria = _criteria(filters)
    total = session.scalars(select(func.count()).select_from(CostCategory).where(*criteria)).one()
    asked = [key.desc() if sort.descending else key for key in _keys(sort.column)]
    order = (*asked, CostCategory.code, CostCategory.id)
    rows = session.execute(
        select(CostCategory, CostType)
        .join(CostType, CostType.id == CostCategory.cost_type_id)
        .where(*criteria)
        .order_by(*order)
        .limit(page.limit)
        .offset(page.offset)
    )
    return CostCategoryPage(_views(session, list(rows), may_change=may_change), total)


def _read_view(session: Session, category_id: UUID) -> CostCategoryView:
    row = session.execute(
        select(CostCategory, CostType)
        .join(CostType, CostType.id == CostCategory.cost_type_id)
        .where(CostCategory.id == category_id)
        .execution_options(populate_existing=True)
    ).one()
    return _views(session, [row], may_change=True)[0]


def read_cost_categories(
    session: Session, category_ids: Collection[UUID]
) -> list[CostCategoryView]:
    """Read the categories given, deactivated or not, without their commands, by code.

    What a marked revision keeps of those its lines employ (EP-07, US-1500). An identifier no
    category bears is left out.
    """
    if not category_ids:
        return []
    rows = session.execute(
        select(CostCategory, CostType)
        .join(CostType, CostType.id == CostCategory.cost_type_id)
        .where(CostCategory.id.in_(list(category_ids)))
        .order_by(CostCategory.code, CostCategory.id)
        .execution_options(populate_existing=True)
    ).all()
    return _views(session, [(category, nature) for category, nature in rows], may_change=False)


def present_cost_categories(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the identifiers given, those a category bears: the witness looks for its own."""
    found = session.scalars(select(CostCategory.id).where(CostCategory.id.in_(category_ids)))
    return frozenset(found)


def category_labels(
    session: Session, category_ids: Collection[UUID], *, locked: bool = False
) -> dict[UUID, CategoryLabel]:
    """Give the label and the kind of the nature of each category given, deactivated ones too.

    A role of resources names its category, and is admitted only a category of labour, active
    (WF-REF-0090). An identifier no category bears is left out. ``locked`` shares, before anything
    is read, the lock of the natures until the transaction ends (``share_natures``): every change of
    the kind or of the state of a category or of its nature takes it first, then reads the roles
    that bind the category (``category_has_roles``), so that it waits for the role attached to it
    meanwhile, or is waited for. No row is locked here: that lock, which both take before any row,
    orders them, and neither waits for a row the other holds.
    """
    if locked:
        share_natures(session)
    rows = session.execute(
        select(CostCategory, CostType)
        .join(CostType, CostType.id == CostCategory.cost_type_id)
        .where(CostCategory.id.in_(category_ids))
        .execution_options(populate_existing=True)
    )
    return {
        category.id: CategoryLabel(
            category.id,
            category.label,
            nature.kind,
            category.is_active,
            nature.is_active,
            nature.id,
        )
        for category, nature in rows
    }


def categories_named(session: Session, labels: Collection[str]) -> dict[str, list[UUID]]:
    """Give the categories each label names, deactivated ones too; a label with none is absent.

    What a cell pasted into the estimate names its category by (EP-07, US-1560); two categories may
    bear one label, which the caller refuses as unknown.
    """
    found: dict[str, list[UUID]] = {}
    if not labels:
        return found
    rows = session.execute(
        select(CostCategory.label, CostCategory.id)
        .where(CostCategory.label.in_(list(labels)))
        .order_by(CostCategory.code)
    )
    for label, category_id in rows:
        found.setdefault(label, []).append(category_id)
    return found


def category_label_of(
    held: SQLColumnExpression[UUID],
) -> SQLColumnExpression[str | None]:
    """Give, of a column of categories, the label of the category held: a sort by the code points.

    For the table of the roles of resources, which holds the column and does not name this table.
    """
    return select(CostCategory.label).where(CostCategory.id == held).scalar_subquery()


def _nature_fault(
    session: Session, cost_type_id: UUID
) -> tuple[CostType | None, FieldError | None]:
    """Read the nature a category is given, and the fault of the field if it admits none (422)."""
    nature = session.scalars(
        select(CostType)
        .where(CostType.id == cost_type_id)
        .execution_options(populate_existing=True)
    ).first()
    if nature is None:
        return None, FieldError("/cost_type_id", UNKNOWN_COST_TYPE)
    if not nature.is_active:
        return nature, FieldError("/cost_type_id", INACTIVE_REFERENCE_OBJECT)
    return nature, None


def _holders(
    session: Session, write: CostCategoryDraft, *, besides: UUID | None
) -> list[FieldError]:
    """Name the codes of the write that another category holds, each with its holder (409)."""
    faults: list[FieldError] = []
    for pointer, column, value in (
        ("/code", CostCategory.code, write.code),
        ("/accounting_code", CostCategory.accounting_code, write.accounting_code),
    ):
        query = select(CostCategory.id).where(column == value)
        if besides is not None:
            query = query.where(CostCategory.id != besides)
        holder = session.scalars(query).first()
        if holder is not None:
            faults.append(value_taken(pointer, holder))
    return faults


def _refuse_taken(session: Session, write: CostCategoryDraft, *, besides: UUID | None) -> None:
    faults = _holders(session, write, besides=besides)
    if faults:
        raise already_exists(faults)


def create_cost_category(
    session: Session, write: CostCategoryDraft, act: Act, *, identifier: UUID | None = None
) -> CostCategoryView:
    """Create an active category under an active nature, with codes no category holds (WF-REF-0040).

    The nature is read under the lock of the natures: a nature deactivated meanwhile, with its
    categories, is refused (422), as one unknown or deactivated before. A code or an accounting
    code another category holds, deactivated or not, is refused naming it (409). ``identifier`` is
    the one the loader of the witness imposes: an identifier already borne is refused (409), the
    API gives none.
    """
    lock_natures(session)
    _, fault = _nature_fault(session, write.cost_type_id)
    if fault is not None:
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    _refuse_taken(session, write, besides=None)
    category_id = new_id() if identifier is None else identifier
    try:
        with session.begin_nested():
            session.execute(
                insert(CostCategory).values(
                    id=category_id,
                    code=write.code,
                    label=write.label,
                    accounting_code=write.accounting_code,
                    cost_type_id=write.cost_type_id,
                    is_active=True,
                    created_at=act.at,
                    created_by=act.author,
                    updated_at=act.at,
                    updated_by=act.author,
                )
            )
    except IntegrityError as error:
        raise _collision(session, error, write, category_id) from None
    return _read_view(session, category_id)


def _collision(
    session: Session,
    error: IntegrityError,
    write: CostCategoryDraft,
    category_id: UUID,
    *,
    besides: UUID | None = None,
) -> Exception:
    """Say which rule a write broke, when a concurrent one took the value first (409)."""
    broken = unique_violated(error)
    if broken == IDENTIFIER_INDEX:
        return identifier_taken(category_id)
    if broken in {CODE_INDEX, ACCOUNTING_CODE_INDEX}:
        faults = _holders(session, write, besides=besides)
        if faults:
            return already_exists(faults)
    return error


def update_cost_category(
    session: Session, category_id: UUID, write: CostCategoryDraft, lock_version: int, act: Act
) -> CostCategoryView:
    """Change the codes, the label and the nature of a category whose version is the one read.

    Refused if unknown (404) or stale (412); a nature unknown or deactivated that the category
    moves to is refused (422) — it keeps its own, deactivated or not —; a code another category
    holds (409). A move to a nature of another kind is refused (409) while the category is
    employed, rated or held by a role of resources; to a nature of the same kind, never.
    """
    lock_reference(session)
    lock_natures(session)
    category = lock_row(session, CostCategory, category_id, lock_version)
    moved = write.cost_type_id != category.cost_type_id
    if moved:
        _, fault = _nature_fault(session, write.cost_type_id)
        if fault is not None:
            raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    _refuse_taken(session, write, besides=category_id)
    if moved:
        _refuse_kind_change(session, category, write.cost_type_id)
    values: dict[str, object] = {
        "code": write.code,
        "label": write.label,
        "accounting_code": write.accounting_code,
        "cost_type_id": write.cost_type_id,
    }
    try:
        with session.begin_nested():
            change_row(session, CostCategory, category_id, values, (lock_version, act))
    except IntegrityError as error:
        raise _collision(session, error, write, category_id, besides=category_id) from None
    return _read_view(session, category_id)


def _refuse_kind_change(session: Session, category: CostCategory, new_type_id: UUID) -> None:
    """Refuse the move of a category to a nature of another kind that something binds (409)."""
    rows = session.execute(
        select(CostType.id, CostType.kind).where(
            CostType.id.in_([category.cost_type_id, new_type_id])
        )
    ).all()
    kinds = dict(rows)
    if kinds[category.cost_type_id] == kinds[new_type_id]:
        return
    held = category_holdings(session, [category.id])[category.id]
    missing = kind_change_missing("cost_category", held)
    if missing:
        raise role_refusal(session, [category.id], missing[0])


def set_cost_category_activation(
    session: Session, category_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> CostCategoryView:
    """Deactivate or reactivate a category whose version is the one read.

    Refused if unknown (404) or stale (412); its reactivation under a nature that is deactivated
    is refused (409, ``cost_type_active`` lacking, the nature named), as its command says in
    advance. A category already in the state asked for is not written.
    """
    if not is_active:
        lock_reference(session)
    lock_natures(session)
    category = lock_row(session, CostCategory, category_id, lock_version)
    if category.is_active != is_active:
        nature = session.get_one(CostType, category.cost_type_id, populate_existing=True)
        # The command of the reactivation, as the list says it, decides the refusal.
        command = cost_category_commands(
            is_active=False, type_is_active=nature.is_active, holdings=Holdings(), may_change=True
        )[0]
        if is_active and not command.is_available:
            raise ConflictError(
                STATE_FORBIDS_OPERATION,
                {
                    "missing_condition": command.missing_conditions[0],
                    "conflicting_object_id": str(nature.id),
                },
            )
        change_row(
            session, CostCategory, category_id, {"is_active": is_active}, (lock_version, act)
        )
    return _read_view(session, category_id)
