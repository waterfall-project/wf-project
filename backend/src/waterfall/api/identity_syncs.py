# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the accounts of the identity provider, asked for and reported (WF-ADM-0070).

The reading is the worker's (WF-ARC-0090): the request deposits the task and answers at once, and
the report of the latest reading that ended — asked for, or the one the platform schedules — is read
apart. Asking for one is a write of the accounts; reading its report, a consultation of them. An
account of Waterfall the report names is read as it is when the report is: an account anonymised
since has no name nor address (#920).
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, IdentitySyncReport
from waterfall.api.evaluation import Requires
from waterfall.api.tasks import task_ref
from waterfall.core.users.interface import (
    Skipped,
    SkippedAccount,
    latest_report,
    read_account_label,
)
from waterfall.platform.errors import NotFoundError
from waterfall.platform.tasks import BackgroundTask, submit

router = APIRouter(tags=["users"])

NOT_FOUND = "NOT_FOUND"


@router.post(
    "/identity-syncs",
    operation_id="startIdentitySync",
    dependencies=[Depends(Requires("users.write"))],
    status_code=202,
    response_model_exclude_unset=True,
)
def post_identity_sync(
    account: Caller, session: Transaction, services: ServicesOf
) -> BackgroundTaskRef:
    """Deposit a reading of the accounts for the worker, asked for by the caller."""
    task_id = submit(session, services.queue, "identity_sync", account.user_id)
    return task_ref(session.get_one(BackgroundTask, task_id))


@router.get(
    "/identity-syncs/latest",
    operation_id="getLatestIdentitySync",
    dependencies=[Depends(Requires("users.read"))],
)
def get_latest_identity_sync(session: Transaction) -> IdentitySyncReport:
    """Give the report of the latest reading of the accounts that ended; none yet is a 404."""
    report = latest_report(session)
    if report is None:
        raise NotFoundError(NOT_FOUND)
    return IdentitySyncReport.model_validate(
        {
            "task_id": report.task_id,
            "finished_at": report.finished_at,
            "created": report.created,
            "updated": report.updated,
            "deactivated": report.deactivated,
            "restored": report.restored,
            "skipped": [skipped(session, each) for each in report.skipped],
            "removed": report.removed,
        }
    )


def skipped(session: Session, entry: Skipped) -> dict[str, Any]:
    """Describe what a reading left as it was: an account as it is now, or a person."""
    if isinstance(entry, SkippedAccount):
        label = read_account_label(session, entry.user_id)
        return {
            "kind": "account",
            "user_id": entry.user_id,
            "subject": None,
            "last_name": None if label is None else label.last_name,
            "first_name": None if label is None else label.first_name,
            "email": None if label is None else label.email,
            "code": entry.code,
        }
    return {
        "kind": "person",
        "user_id": None,
        "subject": entry.subject,
        "last_name": entry.last_name,
        "first_name": entry.first_name,
        "email": entry.email,
        "code": entry.code,
    }
