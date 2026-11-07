# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The minimal reference a project needs (WF-CYC-0120).

``getReferenceReadiness``, read by any session: the four questions the cost and the resource
settings answer, each in its module, composed by the cost settings in the order of the enumeration —
the default calendar with hours, an active category of labour, an active category of provision for
risks, an active role of resources. The refusal of the creation of a project is EP-04's.
"""

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import MissingEnum, ReferenceReadiness
from waterfall.api.evaluation import Requires
from waterfall.core.cost_settings.interface import missing_prerequisites

router = APIRouter(tags=["reference"])


@router.get(
    "/reference/readiness",
    operation_id="getReferenceReadiness",
    dependencies=[Depends(Requires())],
    response_model_exclude_unset=True,
)
def get_reference_readiness(session: Transaction) -> ReferenceReadiness:
    """Name each prerequisite missing, in the order of the enumeration; complete without any.

    The questions are those of the cost settings (``missing_prerequisites``), which the creation
    of a project asks too; ``MissingEnum`` refuses a name the contract does not enumerate.
    """
    missing = [MissingEnum(name) for name in missing_prerequisites(session)]
    return ReferenceReadiness(is_complete=not missing, missing=missing)
