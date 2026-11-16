# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks (WF-DEV-0060, WF-DEV-0010).

``getEstimateIndicators`` and ``getMissingRates`` (US-1510), read by whoever may consult the
estimate (``estimate.read``): the revision named, else the current one, else the last one marked —
a marked one as its marking kept it (US-1670/L2); the scope of the indicators, the project, a
subproject or the set out of any subproject. An amount that a missing rate prevents from being
computed is served in the envelope the contract reads (``ComputableMoney``, ``Computable``), the
categories and the year named.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.scopes import kept_document, scope_of
from waterfall.core.estimate.interface import IndicatorsAsked, estimate_indicators, missing_rates
from waterfall.core.indicators.interface import estimate_document, missing_rate_document
from waterfall.core.revisions.interface import read_revision_for
from waterfall.platform.database import utc_now

router = APIRouter(tags=["estimate"])

CONSULT = "estimate.read"
INDICATORS = "/projects/{project_id}/estimate-indicators"


@router.get(
    INDICATORS,
    operation_id="getEstimateIndicators",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_indicators(
    project_id: UUID,
    session: Transaction,
    revision_id: Annotated[UUID | None, Query()] = None,
    scope: Annotated[str, Query()] = "project",
) -> dict[str, Any]:
    """Give the total of an estimate, its ventilations and its differences, in one reading.

    A marked revision answers the document its marking kept, ``is_stored`` true (WF-DAT-0040), never
    computed again; the current one is computed at the reading. A scope the marking did not keep —
    a subproject created since, one the project does not have — is unknown to the revision (422).
    Only a revision marked before the indicators were kept, which holds no document at all, is
    computed at the reading, ``is_stored`` false (EP-10, "La conservation au marquage").
    """
    read = read_revision_for(session, project_id, revision_id)
    if read.marked:
        kept = kept_document(session, read.revision_id, "estimate", scope_of(scope))
        if kept is not None:
            return kept
    asked = IndicatorsAsked(revision_id, scope, utc_now())
    return estimate_document(estimate_indicators(session, project_id, asked))


@router.get(
    f"{INDICATORS}/missing-rates",
    operation_id="getMissingRates",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_missing_rates(
    project_id: UUID, session: Transaction, revision_id: Annotated[UUID | None, Query()] = None
) -> list[dict[str, Any]]:
    """Give the categories of labour an estimate employs without a rate for its year."""
    return [missing_rate_document(each) for each in missing_rates(session, project_id, revision_id)]
