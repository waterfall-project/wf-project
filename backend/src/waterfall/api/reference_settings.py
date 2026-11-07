# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings the installation shares (FBS-3.1, FBS-3.3, FBS-3.4).

``getReferenceSettings`` and ``updateReferenceSettings``. The settings are read by any session:
the currency goes with every amount, the bounds, the thresholds and the delay qualify what every
reader of a project sees (WF-REF-0140 to WF-REF-0180). They are written field by field, each under
the permission of its function (WF-ADM-0100), judged on the fields the body carries before anything
else (``RequiresByField``); then each value by the module that holds its rule, all at once (422);
then the counter they share (412) — the values before the counter, an order the contract does not
fix: a writing in default is said so even when it is stale besides. A field sent null is refused as
a value in default, as the contract types none of them nullable: only a field absent stays as it
is. A writing that carries no field writes nothing, the counter included. The currency is never
written (WF-REF-0140).
"""

from decimal import Decimal

from fastapi import APIRouter, Depends

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.models import ReferenceSettings
from waterfall.api.evaluation import Requires, RequiresByField
from waterfall.api.reference_settings_write import SettingsWrite, change_of
from waterfall.core.cost_settings.interface import (
    FIELD_PERMISSIONS,
    ReferenceSettingsView,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.installation import read_settings

router = APIRouter(tags=["reference"])

# Read by any session; written by whoever holds the permission of each field carried.
OPEN = [Depends(Requires())]
WRITE = [Depends(Requires()), Depends(RequiresByField(FIELD_PERMISSIONS))]


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
    """Write the fields carried, judged all at once (422), unless the counter is stale (412).

    The values are judged before the counter: a writing in default and stale is refused 422.
    """
    language = read_settings(session).default_language
    change = change_of(body)
    act = Act(account.user_id, utc_now())
    view = write_reference_settings(session, change, body.lock_version.root, act)
    return reference_settings(view, language)
