# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings the installation shares (FBS-3.1, FBS-3.3, FBS-3.4).

``getReferenceSettings`` and ``updateReferenceSettings``. The settings are read by any session:
the currency goes with every amount, the bounds, the thresholds and the delay qualify what every
reader of a project sees (WF-REF-0140 to WF-REF-0180). They are written field by field, each under
the permission of its function (WF-ADM-0100), judged on the fields the body carries before anything
else (``RequiresByField``); then each value by the module that holds its rule, all at once (422);
then the counter they share (412). The currency is never written (WF-REF-0140).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import LockVersion, ReferenceSettings, RiskMatrixSettings
from waterfall.api.evaluation import Requires, RequiresByField
from waterfall.core.cost_settings.interface import (
    FIELD_PERMISSIONS,
    IndexThresholds,
    ReferenceSettingsView,
    RiskMatrix,
    SettingsChange,
    company_name_faults,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.core.indicator_settings.interface import (
    ThresholdTexts,
    delay_faults,
    read_thresholds,
)
from waterfall.core.risk_settings.interface import matrix_faults
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError, UnprocessableError
from waterfall.platform.installation import read_settings

router = APIRouter(tags=["reference"])

VALIDATION_FAILED = "VALIDATION_FAILED"
# Read by any session; written by whoever holds the permission of each field carried.
OPEN = [Depends(Requires())]
WRITE = [Depends(Requires()), Depends(RequiresByField(FIELD_PERMISSIONS))]


class ThresholdsWrite(ContractModel):
    """The four thresholds as a writing sends them: their form and range are judged by the rule.

    ``IndexThreshold`` of the contract refuses by its pattern what the contract names two codes
    for, ``NUMBER_INVALID`` and ``THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE``: the texts reach the rule of
    the indicator settings, which says each.
    """

    cost_watch: str
    cost_alert: str
    schedule_watch: str
    schedule_alert: str


class SettingsWrite(ContractModel):
    """``ReferenceSettingsWrite``, its values judged by the rules of their modules, all at once.

    The shape is the validation's — the matrix as the contract has it, the thresholds texts, the
    delay a whole number —; the name, the order of the bounds, the thresholds and the range of the
    delay are judged together, so that one answer names every field in default (422).
    """

    company_name: str | None = None
    risk_matrix: RiskMatrixSettings | None = None
    index_thresholds: ThresholdsWrite | None = None
    max_weeks_between_reviews: int | None = None
    lock_version: LockVersion


def _plain(value: Decimal) -> str:
    """Write a decimal as the contract's examples do, without a useless zero: ``0.1``."""
    return format(value.normalize(), "f")


def reference_settings(view: ReferenceSettingsView, language: str) -> ReferenceSettings:
    """Describe the settings as the contract does, the language that of the installation."""
    matrix, thresholds = view.risk_matrix, view.index_thresholds
    return ReferenceSettings.model_validate(
        {
            "currency_code": view.currency_code,
            "company_name": view.company_name,
            "default_language": language,
            "risk_matrix": {
                "probability_bounds": [_plain(bound) for bound in matrix.probability_bounds],
                "severity_bounds": [_plain(bound) for bound in matrix.severity_bounds],
                "zones": list(matrix.zones),
            },
            "index_thresholds": {
                "cost_watch": _plain(thresholds.cost_watch),
                "cost_alert": _plain(thresholds.cost_alert),
                "schedule_watch": _plain(thresholds.schedule_watch),
                "schedule_alert": _plain(thresholds.schedule_alert),
            },
            "max_weeks_between_reviews": view.max_weeks_between_reviews,
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(view.created_by),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(view.updated_by),
            },
            "lock_version": view.lock_version,
        }
    )


def change_of(body: SettingsWrite) -> SettingsChange:
    """Read the change a body carries, or refuse (422) every field in default, in their order."""
    faults: list[FieldError] = []
    if body.company_name is not None:
        faults.extend(company_name_faults(body.company_name))
    matrix = None
    if (sent := body.risk_matrix) is not None:
        matrix = RiskMatrix(
            tuple(Decimal(bound.root.root) for bound in sent.probability_bounds),
            tuple(Decimal(bound.root.root) for bound in sent.severity_bounds),
            tuple(zone.value for zone in sent.zones),
        )
        faults.extend(matrix_faults(matrix))
    thresholds: IndexThresholds | None = None
    if (texts := body.index_thresholds) is not None:
        thresholds, refused = read_thresholds(ThresholdTexts(**texts.model_dump()))
        faults.extend(refused)
    if body.max_weeks_between_reviews is not None:
        faults.extend(delay_faults(body.max_weeks_between_reviews))
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return SettingsChange(
        company_name=body.company_name,
        risk_matrix=matrix,
        index_thresholds=thresholds,
        max_weeks_between_reviews=body.max_weeks_between_reviews,
    )


@router.get(
    "/reference/settings",
    operation_id="getReferenceSettings",
    dependencies=OPEN,
    response_model_exclude_unset=True,
)
def get_reference_settings(session: Transaction) -> ReferenceSettings:
    """Give the settings, which the bootstrap writes with the installation (WF-EXP-0020)."""
    language = read_settings(session).default_language
    return reference_settings(read_reference_settings(session), language)


@router.patch(
    "/reference/settings",
    operation_id="updateReferenceSettings",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def update_reference_settings(
    body: SettingsWrite, account: Caller, session: Transaction
) -> ReferenceSettings:
    """Write the fields carried, judged all at once (422), unless the counter is stale (412)."""
    language = read_settings(session).default_language
    change = change_of(body)
    act = Act(account.user_id, utc_now())
    view = write_reference_settings(session, change, body.lock_version.root, act)
    return reference_settings(view, language)
