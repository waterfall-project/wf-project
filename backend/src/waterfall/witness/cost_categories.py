# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The categories of cost of the witness, each under its nature.

``volume/cost_categories.json``; the category of provision of the bootstrap stays. Written by
``create_cost_category`` with the identifiers the witness imposes, each under its nature — which
must be active, being written before: a category of the witness deactivated is deactivated
afterwards, itself.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import CostCategory
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    create_cost_category,
    present_cost_categories,
    set_cost_category_activation,
)
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness


class CostCategories(BaseModel):
    """The value of ``listCostCategories`` the witness describes its categories by."""

    items: list[CostCategory]


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    categories = witness.read("volume/cost_categories.json", CostCategories).items
    imposed = {category.cost_category_id.root for category in categories}
    if is_loaded(imposed, present_cost_categories(session, imposed)):
        return False
    for category in categories:
        draft = CostCategoryDraft(
            category.code, category.label, category.accounting_code, category.cost_type_id.root
        )
        created = create_cost_category(
            session, draft, witness.act, identifier=category.cost_category_id.root
        )
        if not category.is_active:
            set_cost_category_activation(
                session,
                created.cost_category_id,
                is_active=False,
                lock_version=created.audit.lock_version,
                act=witness.act,
            )
    return bool(categories)
