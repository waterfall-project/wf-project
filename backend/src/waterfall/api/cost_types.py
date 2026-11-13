# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The natures and the categories of cost (FBS-3.1).

``listCostTypes``, ``createCostType``, ``updateCostType``, ``setCostTypeActivation`` and the
same four for the categories.

The active natures and categories are read by any open session: they are the vocabulary of the
quotes of the projects (WF-DEV-0020). The deactivated ones — ``include_inactive``, ``is_active``
false — and every write ask for the permission to change the cost settings (``cost_settings.write``,
WF-REF-0150, WF-ADM-0100, decision of the author of 2026-11-06, #2084): a list so asked, without it,
is refused by 403 before it reads. The commands of an object are those of a caller who may change
the cost settings; a reader has none.
"""

from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BeforeValidator

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel, Text
from waterfall.api.contract.models import (
    CostCategory,
    CostCategoryUpdate,
    CostCategoryWrite,
    CostType,
    CostTypeKind,
    CostTypeUpdate,
    CostTypeWrite,
    LockVersion,
    PaginationMeta,
    SortOrder,
)
from waterfall.api.evaluation import Acting, Requires, RequiresForInactive
from waterfall.api.queries import Offset, Search, listed
from waterfall.core.cost_settings.commands import CommandAvailability
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostCategoryFilters,
    CostCategorySort,
    CostCategoryView,
    CostTypeDraft,
    CostTypeFilters,
    CostTypeSort,
    CostTypeView,
    Page,
    create_cost_category,
    create_cost_type,
    list_cost_categories,
    list_cost_types,
    set_cost_category_activation,
    set_cost_type_activation,
    update_cost_category,
    update_cost_type,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["reference"])

CHANGE = "cost_settings.write"
# Any open session reads the active objects; the deactivated ones, and every write, ask for CHANGE.
READ = [Depends(Requires()), Depends(RequiresForInactive(CHANGE))]
WRITE = [Depends(Requires(CHANGE))]
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500


class ActivationBody(ContractModel):
    """The body of the activation of a nature or of a category: the state, and the version read."""

    is_active: bool
    lock_version: LockVersion


def _lacking_type(body: object) -> object:
    """Read a nature sent null (only) as absent: the category lacks it (``VALUE_REQUIRED``)."""
    if not isinstance(body, dict):
        return body
    sent = cast("dict[str, object]", body)
    return {
        name: value for name, value in sent.items() if name != "cost_type_id" or value is not None
    }


# The body of a category: a nature null is a nature lacking, refused as one absent (WF-REF-0040).
type CreationBody = Annotated[CostCategoryWrite, BeforeValidator(_lacking_type), Body()]
type ChangeBody = Annotated[CostCategoryUpdate, BeforeValidator(_lacking_type), Body()]


def commands(held: tuple[CommandAvailability, ...]) -> list[dict[str, object]]:
    """Describe the commands of an object as the contract does."""
    return [
        {
            "command": command.command,
            "is_available": command.is_available,
            "missing_conditions": list(command.missing_conditions),
        }
        for command in held
    ]


def audit(view: CostTypeView | CostCategoryView) -> dict[str, object]:
    """Describe the columns of audit of an object as the contract does."""
    return {
        "created_at": view.audit.created_at,
        "created_by": actor_ref(view.audit.created_by),
        "updated_at": view.audit.updated_at,
        "updated_by": actor_ref(view.audit.updated_by),
    }


def cost_type(view: CostTypeView) -> CostType:
    """Describe a nature as the contract does."""
    return CostType.model_validate(
        {
            "cost_type_id": view.cost_type_id,
            "code": view.code,
            "label": view.label,
            "kind": view.kind,
            "is_active": view.is_active,
            "available_commands": commands(view.commands),
            "audit": audit(view),
            "lock_version": view.audit.lock_version,
        }
    )


def cost_category(view: CostCategoryView) -> CostCategory:
    """Describe a category as the contract does."""
    return CostCategory.model_validate(
        {
            "cost_category_id": view.cost_category_id,
            "code": view.code,
            "label": view.label,
            "cost_type_id": view.cost_type_id,
            "cost_type_label": view.cost_type_label,
            "cost_type_kind": view.cost_type_kind,
            "cost_type_is_active": view.cost_type_is_active,
            "accounting_code": view.accounting_code,
            "is_active": view.is_active,
            "available_commands": commands(view.commands),
            "audit": audit(view),
            "lock_version": view.audit.lock_version,
        }
    )


def kept_states(
    *, include_inactive: bool = False, is_active: bool | None = None
) -> frozenset[bool]:
    """Read the states a list keeps: ``is_active`` prevails over ``include_inactive``."""
    if is_active is None:
        return frozenset({True, False} if include_inactive else {True})
    return frozenset({is_active})


def page_of(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page:
    """Read the page asked for: fifty objects from the first one, unless said otherwise."""
    return Page(limit, offset)


def type_sort(
    sort_by: Literal["code", "label", "kind", "is_active"] = "code",
    sort_order: SortOrder = SortOrder.asc,
) -> CostTypeSort:
    """Read the sort the table of the natures asks for: the code unless said otherwise."""
    return CostTypeSort(sort_by, descending=sort_order is SortOrder.desc)


def category_sort(
    sort_by: Literal["code", "label", "cost_type", "accounting_code", "is_active"] = "code",
    sort_order: SortOrder = SortOrder.asc,
) -> CostCategorySort:
    """Read the sort the table of the categories asks for: the code unless said otherwise."""
    return CostCategorySort(sort_by, descending=sort_order is SortOrder.desc)


def type_filters(
    states: Annotated[frozenset[bool], Depends(kept_states)],
    search: Search = None,
    kinds: Text | None = None,
) -> CostTypeFilters:
    """Read the filters of the table of the natures; the kinds are separated by commas."""
    read = listed("kinds", kinds, CostTypeKind)
    return CostTypeFilters(
        search, None if read is None else frozenset(kind.value for kind in read), states
    )


def category_filters(
    states: Annotated[frozenset[bool], Depends(kept_states)],
    search: Search = None,
    cost_type_id: UUID | None = None,
) -> CostCategoryFilters:
    """Read the filters of the table of the categories."""
    return CostCategoryFilters(search, cost_type_id, states)


@router.get(
    "/reference/cost-types",
    operation_id="listCostTypes",
    dependencies=READ,
    response_model=None,
)
def get_cost_types(
    actor: Acting,
    session: Transaction,
    filters: Annotated[CostTypeFilters, Depends(type_filters)],
    sort: Annotated[CostTypeSort, Depends(type_sort)],
    page: Annotated[Page, Depends(page_of)],
) -> dict[str, object]:
    """Give a page of the natures, filtered and sorted by the server (WF-REF-0030)."""
    read = list_cost_types(session, filters, sort, page, may_change=CHANGE in actor.permissions)
    meta = PaginationMeta(limit=page.limit, offset=page.offset, total=read.total)
    return {
        "items": [
            cost_type(view).model_dump(mode="json", exclude_unset=True) for view in read.types
        ],
        "meta": meta.model_dump(),
    }


@router.post(
    "/reference/cost-types",
    operation_id="createCostType",
    dependencies=WRITE,
    status_code=201,
    response_model_exclude_unset=True,
)
def post_cost_type(body: CostTypeWrite, account: Caller, session: Transaction) -> CostType:
    """Create a nature of one of the three kinds, with a code no nature holds (WF-REF-0030)."""
    draft = CostTypeDraft(body.code, body.label, body.kind.value)
    return cost_type(create_cost_type(session, draft, Act(account.user_id, utc_now())))


@router.patch(
    "/reference/cost-types/{cost_type_id}",
    operation_id="updateCostType",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def patch_cost_type(
    cost_type_id: UUID, body: CostTypeUpdate, account: Caller, session: Transaction
) -> CostType:
    """Change the code, the label and the kind of a nature, unless a category binds its kind."""
    draft = CostTypeDraft(body.code, body.label, body.kind.value)
    act = Act(account.user_id, utc_now())
    return cost_type(update_cost_type(session, cost_type_id, draft, body.lock_version.root, act))


@router.put(
    "/reference/cost-types/{cost_type_id}/activation",
    operation_id="setCostTypeActivation",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_cost_type_activation(
    cost_type_id: UUID, body: ActivationBody, account: Caller, session: Transaction
) -> CostType:
    """Deactivate a nature with its categories, or reactivate it alone (WF-REF-0010)."""
    act = Act(account.user_id, utc_now())
    return cost_type(
        set_cost_type_activation(
            session,
            cost_type_id,
            is_active=body.is_active,
            lock_version=body.lock_version.root,
            act=act,
        )
    )


@router.get(
    "/reference/cost-categories",
    operation_id="listCostCategories",
    dependencies=READ,
    response_model=None,
)
def get_cost_categories(
    actor: Acting,
    session: Transaction,
    filters: Annotated[CostCategoryFilters, Depends(category_filters)],
    sort: Annotated[CostCategorySort, Depends(category_sort)],
    page: Annotated[Page, Depends(page_of)],
) -> dict[str, object]:
    """Give a page of the categories, filtered and sorted by the server (WF-REF-0040)."""
    read = list_cost_categories(
        session, filters, sort, page, may_change=CHANGE in actor.permissions
    )
    meta = PaginationMeta(limit=page.limit, offset=page.offset, total=read.total)
    return {
        "items": [
            cost_category(view).model_dump(mode="json", exclude_unset=True)
            for view in read.categories
        ],
        "meta": meta.model_dump(),
    }


@router.post(
    "/reference/cost-categories",
    operation_id="createCostCategory",
    dependencies=WRITE,
    status_code=201,
    response_model_exclude_unset=True,
)
def post_cost_category(body: CreationBody, account: Caller, session: Transaction) -> CostCategory:
    """Create a category under an active nature, with the codes no category holds (WF-REF-0040)."""
    draft = CostCategoryDraft(body.code, body.label, body.accounting_code, body.cost_type_id.root)
    return cost_category(create_cost_category(session, draft, Act(account.user_id, utc_now())))


@router.patch(
    "/reference/cost-categories/{cost_category_id}",
    operation_id="updateCostCategory",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def patch_cost_category(
    cost_category_id: UUID, body: ChangeBody, account: Caller, session: Transaction
) -> CostCategory:
    """Change a category, and its nature unless the move to another kind is bound."""
    draft = CostCategoryDraft(body.code, body.label, body.accounting_code, body.cost_type_id.root)
    act = Act(account.user_id, utc_now())
    changed = update_cost_category(session, cost_category_id, draft, body.lock_version.root, act)
    return cost_category(changed)


@router.put(
    "/reference/cost-categories/{cost_category_id}/activation",
    operation_id="setCostCategoryActivation",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_cost_category_activation(
    cost_category_id: UUID, body: ActivationBody, account: Caller, session: Transaction
) -> CostCategory:
    """Deactivate a category, or reactivate it under an active nature alone (WF-REF-0010)."""
    act = Act(account.user_id, utc_now())
    return cost_category(
        set_cost_category_activation(
            session,
            cost_category_id,
            is_active=body.is_active,
            lock_version=body.lock_version.root,
            act=act,
        )
    )
