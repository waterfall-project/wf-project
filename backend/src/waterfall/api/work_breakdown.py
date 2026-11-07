# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work breakdown of a project (WF-PRJ-0020).

``getWorkBreakdown`` and ``setWorkBreakdown``.

A project is read by its contributors and by the holders of ``all_projects_read``
(``RequiresProject``); its work breakdown is written, whole, by its project managers.
"""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BeforeValidator

from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.models import (
    LockVersion,
    WorkBreakdown,
    WorkBreakdownKind,
    WorkBreakdownReading,
)
from waterfall.api.evaluation import RequiresProject
from waterfall.api.queries import Search, listed
from waterfall.core.projects.interface import (
    DeliverableEntry,
    OrderItemEntry,
    WorkBreakdownFilters,
    WorkBreakdownRead,
    WorkBreakdownToWrite,
    WorkPackageEntry,
    read_work_breakdown,
    set_work_breakdown,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["projects"])

CONSULT = "project_settings.read"
CHANGE = "project_settings.write"


def _lacking_counter(body: object) -> object:
    """Read a counter sent null (only) as absent: a filtered reading's has none (VALUE_REQUIRED)."""
    if not isinstance(body, dict):
        return body
    sent = cast("dict[str, object]", body)
    return {
        name: value for name, value in sent.items() if name != "lock_version" or value is not None
    }


type WriteBody = Annotated[WorkBreakdown, BeforeValidator(_lacking_counter), Body()]


def described(read: WorkBreakdownRead) -> WorkBreakdownReading:
    """Describe the work breakdown read as the contract does.

    No task bears a work package or an order item before EP-06: ``attached_task`` is null.
    """
    return WorkBreakdownReading.model_validate(
        {
            "work_packages": [
                {
                    "work_package_id": package.work_package_id,
                    "label": package.label,
                    "is_match": package.is_match,
                    "attached_task": None,
                    "order_items": [
                        {
                            "order_item_id": item.order_item_id,
                            "label": item.label,
                            "is_match": item.is_match,
                            "attached_task": None,
                            "deliverables": [
                                {
                                    "deliverable_id": deliverable.deliverable_id,
                                    "label": deliverable.label,
                                    "is_match": deliverable.is_match,
                                }
                                for deliverable in item.deliverables
                            ],
                        }
                        for item in package.order_items
                    ],
                }
                for package in read.work_packages
            ],
            "lock_version": None if read.lock_version is None else LockVersion(read.lock_version),
        }
    )


def entries_of(body: WorkBreakdown) -> tuple[WorkPackageEntry, ...]:
    """Read the work breakdown a body carries; an element without identifier is new."""
    return tuple(
        WorkPackageEntry(
            package.label,
            tuple(
                OrderItemEntry(
                    item.label,
                    tuple(
                        DeliverableEntry(
                            deliverable.label,
                            None
                            if deliverable.deliverable_id is None
                            else deliverable.deliverable_id.root,
                        )
                        for deliverable in item.deliverables
                    ),
                    None if item.order_item_id is None else item.order_item_id.root,
                )
                for item in package.order_items
            ),
            None if package.work_package_id is None else package.work_package_id.root,
        )
        for package in body.work_packages
    )


def work_breakdown_filters(
    *, search: Search = None, kinds: Annotated[str | None, Query()] = None
) -> WorkBreakdownFilters:
    """Read the filters of the reading; a nature that is none is refused (422)."""
    named = listed("kinds", kinds, WorkBreakdownKind)
    return WorkBreakdownFilters(
        search=search,
        kinds=None if named is None else frozenset(kind.value for kind in named),
    )


@router.get(
    "/projects/{project_id}/work-breakdown",
    operation_id="getWorkBreakdown",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=WorkBreakdownReading,
)
def get_work_breakdown(
    project_id: UUID,
    session: Transaction,
    filters: Annotated[WorkBreakdownFilters, Depends(work_breakdown_filters)],
) -> WorkBreakdownReading:
    """Give the work breakdown of a project, whole or what the filters retain."""
    return described(read_work_breakdown(session, project_id, filters))


@router.put(
    "/projects/{project_id}/work-breakdown",
    operation_id="setWorkBreakdown",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE, manager=True))],
    response_model=WorkBreakdownReading,
)
def put_work_breakdown(
    project_id: UUID, body: WriteBody, account: Caller, session: Transaction
) -> WorkBreakdownReading:
    """Write the whole work breakdown at the counter read; only a project manager may."""
    write = WorkBreakdownToWrite(entries_of(body), body.lock_version.root)
    act = Act(account.user_id, utc_now())
    return described(set_work_breakdown(session, project_id, write, act))
