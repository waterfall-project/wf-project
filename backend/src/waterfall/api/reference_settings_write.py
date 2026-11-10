# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writing of the settings the installation shares, and the change it makes (FBS-3.1).

What ``updateReferenceSettings`` reads of its body — the shape of ``ReferenceSettingsWrite`` and
the judgement of its values by the rules of their modules, all at once (422) —, in a module with
no router, so that the route and the loader of the witness (``waterfall.witness``) both import it
and the loader depends on no module of routes.
"""

from decimal import Decimal

from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import LockVersion, RiskMatrixSettings
from waterfall.core.cost_settings.interface import (
    IndexThresholds,
    RiskMatrix,
    SettingsChange,
    company_name_faults,
)
from waterfall.core.indicator_settings.interface import (
    ThresholdTexts,
    delay_faults,
    read_thresholds,
)
from waterfall.core.risk_settings.interface import matrix_faults
from waterfall.platform.errors import (
    VALIDATION_FAILED,
    FieldError,
    UnprocessableError,
    json_pointer,
)


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
    delay are judged together, so that one answer names every field in default (422). ``None`` is
    a field absent, or sent null: ``change_of`` tells them apart, and refuses the second
    (``sent_null``).
    """

    company_name: str | None = None
    risk_matrix: RiskMatrixSettings | None = None
    index_thresholds: ThresholdsWrite | None = None
    max_weeks_between_reviews: int | None = None
    lock_version: LockVersion


def sent_null(body: SettingsWrite, name: str) -> list[FieldError]:
    """Refuse a field sent null (``VALIDATION_FAILED`` at its pointer): the contract types none so.

    As in the other writings of the service, a null is no absence: only a field absent stays as it
    is.
    """
    if name in body.model_fields_set and getattr(body, name) is None:
        return [FieldError(json_pointer(name), VALIDATION_FAILED)]
    return []


def change_of(body: SettingsWrite) -> SettingsChange:
    """Read the change a body carries, or refuse (422) every field in default, in their order."""
    faults = sent_null(body, "company_name")
    if body.company_name is not None:
        faults.extend(company_name_faults(body.company_name))
    faults.extend(sent_null(body, "risk_matrix"))
    matrix = None
    if (sent := body.risk_matrix) is not None:
        matrix = RiskMatrix(
            tuple(Decimal(bound.root.root) for bound in sent.probability_bounds),
            tuple(Decimal(bound.root.root) for bound in sent.severity_bounds),
            tuple(zone.value for zone in sent.zones),
        )
        faults.extend(matrix_faults(matrix))
    faults.extend(sent_null(body, "index_thresholds"))
    thresholds: IndexThresholds | None = None
    if (texts := body.index_thresholds) is not None:
        thresholds, refused = read_thresholds(ThresholdTexts(**texts.model_dump()))
        faults.extend(refused)
    faults.extend(sent_null(body, "max_weeks_between_reviews"))
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
