# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The minimal reference a project needs (WF-CYC-0120).

``getReferenceReadiness``, read by any session: the four questions the cost and the resource
settings answer, each in its module, composed here in the order of the enumeration — the default
calendar with hours, an active category of labour, an active category of provision for risks, an
active role of resources. The refusal of the creation of a project is EP-04's.
"""

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import MissingEnum, ReferenceReadiness
from waterfall.api.evaluation import Requires
from waterfall.core.cost_settings.interface import (
    labour_categories_exist,
    provision_category_active,
)
from waterfall.core.resource_settings.interface import (
    active_role_exists,
    default_calendar_has_hours,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

router = APIRouter(tags=["reference"])

# Each prerequisite, and the question of its module that tells whether it is held.
QUESTIONS: dict[MissingEnum, Callable[[Session], bool]] = {
    MissingEnum.default_calendar_with_hours: default_calendar_has_hours,
    MissingEnum.active_cost_category: labour_categories_exist,
    MissingEnum.active_provision_category: provision_category_active,
    MissingEnum.active_resource_role: active_role_exists,
}


@router.get(
    "/reference/readiness",
    operation_id="getReferenceReadiness",
    dependencies=[Depends(Requires())],
    response_model_exclude_unset=True,
)
def get_reference_readiness(session: Transaction) -> ReferenceReadiness:
    """Name each prerequisite missing, in the order of the enumeration; complete without any."""
    missing = [prerequisite for prerequisite in MissingEnum if not QUESTIONS[prerequisite](session)]
    return ReferenceReadiness(is_complete=not missing, missing=missing)
