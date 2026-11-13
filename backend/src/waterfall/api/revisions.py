# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of a project and their structures (FBS-4.1).

``listRevisions``, ``createRevision``, ``getRevision`` — with, for a marked revision, what it keeps
of the reference (``snapshot``, US-1500) —, ``abandonRevision`` and ``listCostStructures``
(US-0960); ``markRevision``, which submits its task to the worker and
answers 202 with it, which ``getBackgroundTask`` follows (US-0970, WF-ARC-0090).

Each names the project and is judged by ``RequiresProject``: the permission of the function of
the revisions and the quality of the caller on the project (WF-ADM-0110, WF-PRJ-0060). The
history and the structures are read by whoever consults the revisions; a revision is opened by
a contributor holding the permission to manage them, and marked or abandoned by a project manager
holding the permission of that action, a structuring action of its own (WF-ADM-0100).
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import (
    BackgroundTaskRef,
    CostStructure,
    PaginationMeta,
    Revision,
    RevisionCreate,
    RevisionMark,
    RevisionStatus,
)
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.queries import Offset, Search, listed
from waterfall.api.tasks import task_ref
from waterfall.core.estimate.interface import KeptReference, Stamp, kept_reference
from waterfall.core.projects.interface import CommandAvailability, Viewer
from waterfall.core.revisions.interface import (
    KEPT,
    MarkingRequest,
    RevisionAsked,
    RevisionFilters,
    RevisionPage,
    RevisionToAbandon,
    RevisionView,
    abandon_revision,
    create_revision,
    list_cost_structures,
    list_revisions,
    read_revision,
    submit_marking,
)
from waterfall.core.users.interface import Author, read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.tasks import BackgroundTask

router = APIRouter(tags=["revisions"])

CONSULT = "revisions.read"
MANAGE = "revisions.write"
ABANDON = "revision_abandon"
MARK = "revision_mark"
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
REVISIONS = "/projects/{project_id}/revisions"
REVISION = f"{REVISIONS}/{{revision_id}}"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _plain(value: Decimal) -> str:
    """Write a decimal as the contract's examples do, without a useless zero: ``0.03``."""
    return format(value.normalize(), "f")


def _commands(commands: tuple[CommandAvailability, ...]) -> list[dict[str, Any]]:
    return [
        {
            "command": command.command,
            "is_available": command.is_available,
            "missing_conditions": list(command.missing_conditions),
        }
        for command in commands
    ]


def _audit(stamp: Stamp, authors: Mapping[UUID, Author]) -> dict[str, Any]:
    """Describe the audit an image keeps, its authors named as they are today."""
    created, updated = stamp.created_by, stamp.updated_by
    return {
        "created_at": stamp.created_at,
        "created_by": actor_ref(None if created is None else authors.get(created)),
        "updated_at": stamp.updated_at,
        "updated_by": actor_ref(None if updated is None else authors.get(updated)),
    }


def snapshot(session: Session, kept: KeptReference) -> dict[str, Any]:
    """Describe what a marked revision keeps of the reference (``RevisionSnapshot``, WF-REV-0030).

    Every field as it was at the marking; the authors, accounts, named as they are today.
    """
    stamps = [each.stamp for each in (*kept.resource_roles, *kept.calendars, *kept.cost_categories)]
    authors = read_authors(
        session,
        {
            author
            for stamp in stamps
            for author in (stamp.created_by, stamp.updated_by)
            if author is not None
        },
    )
    roles = [
        {
            "resource_role_id": role.resource_role_id,
            "code": role.code,
            "label": role.label,
            "org_node_id": role.org_node_id,
            "org_node_label": role.org_node_label,
            "cost_category_id": role.cost_category_id,
            "cost_category_label": role.cost_category_label,
            "calendar_id": role.calendar_id,
            "calendar_label": role.calendar_label,
            "capacity": {
                "monthly_hours": _plain(role.monthly_hours),
                "headcount": _plain(role.headcount),
            },
            "is_active": role.stamp.is_active,
            "audit": _audit(role.stamp, authors),
            "lock_version": role.stamp.lock_version,
        }
        for role in kept.resource_roles
    ]
    calendars = [
        {
            "calendar_id": calendar.calendar_id,
            "label": calendar.label,
            "weekly_hours": {day: _plain(calendar.weekly_hours.of(day)) for day in DAYS},
            "is_default": calendar.is_default,
            "is_active": calendar.stamp.is_active,
            "audit": _audit(calendar.stamp, authors),
            "lock_version": calendar.stamp.lock_version,
        }
        for calendar in kept.calendars
    ]
    categories = [
        {
            "cost_category_id": category.cost_category_id,
            "code": category.code,
            "label": category.label,
            "cost_type_id": category.cost_type_id,
            "cost_type_label": category.cost_type_label,
            "cost_type_kind": category.cost_type_kind,
            "cost_type_is_active": category.cost_type_is_active,
            "accounting_code": category.accounting_code,
            "is_active": category.stamp.is_active,
            "audit": _audit(category.stamp, authors),
            "lock_version": category.stamp.lock_version,
        }
        for category in kept.cost_categories
    ]
    rates = [
        {
            "cost_category_id": rate.cost_category_id,
            "year": rate.year,
            "amount": f"{rate.amount:.2f}",
        }
        for rate in kept.hourly_rates
    ]
    return {
        "employed_reference": {
            "resource_roles": roles,
            "calendars": calendars,
            "cost_categories": categories,
            "hourly_rates": rates,
        }
    }


def described(
    session: Session,
    views: list[RevisionView],
    snapshots: Mapping[UUID, dict[str, Any]] | None = None,
) -> list[Revision]:
    """Describe revisions as the contract does, their authors named as they are today.

    ``snapshots`` what each marked revision ``getRevision`` reads keeps of the reference, by
    revision: omitted for the others, the current one and every revision of a list or a write.
    """
    snapshots = snapshots or {}
    wanted = {
        author
        for view in views
        for author in (view.created_by, view.updated_by)
        if author is not None
    }
    authors = read_authors(session, wanted)
    return [
        Revision.model_validate(
            {
                "revision_id": view.revision_id,
                "project_id": view.project_id,
                "version_name": view.version_name,
                "description": view.description,
                "status": view.status,
                "marked_at": view.marked_at,
                "is_reference": view.is_reference,
                "reference_year": view.reference_year,
                "inflation_rate": _plain(view.inflation_rate),
                "win_probability": _plain(view.win_probability),
                "source_revision_id": view.source_revision_id,
                "source_version_name": view.source_version_name,
                "available_commands": _commands(view.commands),
                "audit": {
                    "created_at": view.created_at,
                    "created_by": actor_ref(
                        None if view.created_by is None else authors.get(view.created_by)
                    ),
                    "updated_at": view.updated_at,
                    "updated_by": actor_ref(
                        None if view.updated_by is None else authors.get(view.updated_by)
                    ),
                },
                "lock_version": view.lock_version,
                **(
                    {"snapshot": snapshots[view.revision_id]}
                    if view.revision_id in snapshots
                    else {}
                ),
            }
        )
        for view in views
    ]


def viewer_of(actor: Acting) -> Viewer:
    """Give the caller as the modules of the projects read it: its account and its permissions."""
    return Viewer(actor.user_id, actor.permissions)


def revision_filters(
    *, status: Annotated[str | None, Query()] = None, search: Search = None
) -> RevisionFilters:
    """Read the filters of the history: the statuses named, a text searched."""
    named = listed("status", status, RevisionStatus)
    return RevisionFilters(
        statuses=None if named is None else frozenset(each.value for each in named),
        search=search,
    )


def page_of(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> RevisionPage:
    """Read the page asked for: fifty revisions from the latest, unless said otherwise."""
    return RevisionPage(limit, offset)


@router.get(
    REVISIONS,
    operation_id="listRevisions",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_revisions(
    project_id: UUID,
    actor: Acting,
    session: Transaction,
    filters: Annotated[RevisionFilters, Depends(revision_filters)],
    page: Annotated[RevisionPage, Depends(page_of)],
) -> dict[str, Any]:
    """Give a page of the history of a project, the latest revision first (WF-REV-0070)."""
    read = list_revisions(session, project_id, viewer_of(actor), filters, page)
    meta = PaginationMeta(limit=page.limit, offset=page.offset, total=read.total)
    items = described(session, read.revisions)
    return {
        "items": [item.model_dump(mode="json", exclude_unset=True) for item in items],
        "meta": meta.model_dump(),
    }


@router.post(
    REVISIONS,
    operation_id="createRevision",
    dependencies=[Depends(RequiresProject(CONSULT, MANAGE))],
    status_code=201,
    response_model_exclude_unset=True,
)
def post_revision(
    project_id: UUID, body: RevisionCreate, actor: Acting, account: Caller, session: Transaction
) -> Revision:
    """Open the current revision of a project, a copy of its last marked one (WF-REV-0010).

    The body's ``apply_rate_update`` accepts the update of the rates the proposal would present at
    the rate of the reference (WF-REV-0060, #1764); its ``description`` is kept on the revision,
    which its marking takes up (#2171).
    """
    act = Act(account.user_id, utc_now())
    asked = RevisionAsked(body.description, apply_rate_update=bool(body.apply_rate_update))
    opened = create_revision(session, project_id, act, viewer_of(actor), asked)
    return described(session, [opened])[0]


@router.get(
    REVISION,
    operation_id="getRevision",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model_exclude_unset=True,
)
def get_revision(
    project_id: UUID, revision_id: UUID, actor: Acting, session: Transaction
) -> Revision:
    """Give a revision of a project, with the commands its reader holds on it (WF-REV-0090).

    A marked revision with what it keeps of the reference (``snapshot``, WF-REV-0030); the current
    one follows the reference, and has none.
    """
    view = read_revision(session, project_id, revision_id, viewer_of(actor))
    kept: dict[UUID, dict[str, Any]] = {}
    if view.status == "marked":
        kept[view.revision_id] = snapshot(session, kept_reference(session, project_id, revision_id))
    return described(session, [view], kept)[0]


@router.delete(
    REVISION,
    operation_id="abandonRevision",
    dependencies=[Depends(RequiresProject(CONSULT, ABANDON, manager=True))],
    status_code=204,
)
def delete_revision(
    project_id: UUID,
    revision_id: UUID,
    lock_version: Annotated[int, Query(ge=0, le=2147483647)],
    actor: Acting,
    session: Transaction,
) -> Response:
    """Abandon the current revision of a project at the counter read; its rows are deleted."""
    act = Act(actor.user_id, utc_now())
    abandoned = RevisionToAbandon(revision_id, lock_version)
    abandon_revision(session, project_id, abandoned, act, viewer_of(actor))
    return Response(status_code=204)


def marking_request(project_id: UUID, revision_id: UUID, body: RevisionMark) -> MarkingRequest:
    """Read the marking asked for: the revision of the path, the name, the counter read."""
    # A description absent keeps the one given at the creation; a null one clears it (#2171).
    description = body.description if "description" in body.model_fields_set else KEPT
    return MarkingRequest(
        project_id, revision_id, body.version_name, description, body.lock_version.root
    )


@router.post(
    f"{REVISION}/mark",
    operation_id="markRevision",
    dependencies=[Depends(RequiresProject(CONSULT, MARK, manager=True))],
    status_code=202,
    response_model_exclude_unset=True,
)
def post_marking(
    request: Annotated[MarkingRequest, Depends(marking_request)],
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> BackgroundTaskRef:
    """Deposit the marking of the current revision for the worker, and say where it stands.

    Judged under the lock of the revision at the counter read, nothing deposited if refused; the
    task is written in the transaction of the request, and deposited once it is committed.
    """
    act = Act(actor.user_id, utc_now())
    task_id = submit_marking(session, services.queue, request, act, viewer_of(actor))
    return task_ref(session.get_one(BackgroundTask, task_id))


@router.get(
    f"{REVISION}/structures",
    operation_id="listCostStructures",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_structures(
    project_id: UUID, revision_id: UUID, actor: Acting, session: Transaction
) -> list[dict[str, Any]]:
    """Give the structures of a revision, the main one first, with their commands (WF-REV-0100)."""
    views = list_cost_structures(session, project_id, revision_id, viewer_of(actor))
    return [
        CostStructure.model_validate(
            {
                "structure_id": view.structure_id,
                "revision_id": view.revision_id,
                "kind": view.kind,
                "label": view.label,
                "planning_start_on": view.planning_start_on,
                "is_merged": view.is_merged,
                "available_commands": _commands(view.commands),
                "lock_version": view.lock_version,
            }
        ).model_dump(mode="json", exclude_unset=True)
        for view in views
    ]
