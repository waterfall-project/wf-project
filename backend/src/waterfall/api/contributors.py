# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of a project and their kind (WF-PRJ-0060).

``listContributors``, ``setContributors`` and ``listContributorSuggestions``.

A project is read by its contributors and by the holders of ``all_projects_read``
(``RequiresProject``); its list is written by its project managers, and by one caller who is no
contributor, in the one case the contract names: every project manager of the project is
deactivated, and the caller holds the permission of the settings of the project and
``all_projects_read`` (the rescue, ``project_rescue``). The guard lets that caller pass; the module
of the projects judges it under the lock of the project, on the list as it stands (WF-ADM-0090).
"""

from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BeforeValidator

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.contract.models import (
    Contributor,
    ContributorKind,
    ContributorList,
    ContributorSuggestion,
    ContributorsWrite,
    LockVersion,
    SortOrder,
)
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.queries import Search, listed
from waterfall.core.access_roles.interface import NOT_CONTRIBUTOR
from waterfall.core.projects.interface import (
    ContributorColumn,
    ContributorEntry,
    ContributorFilters,
    ContributorSort,
    ContributorsRead,
    ContributorsToWrite,
    list_contributor_suggestions,
    list_contributors,
    set_contributors,
)
from waterfall.platform.errors import ForbiddenError

router = APIRouter(tags=["projects"])

CONSULT = "project_settings.read"
CHANGE = "project_settings.write"
COLUMNS: dict[str, ContributorColumn] = {
    "display_name": "display_name",
    "kind": "kind",
    "is_active": "is_active",
}


class RequiresContributorsWrite(RequiresProject):
    """The guard of the write of the list: a project manager, or the rescue of the project.

    Judged as ``RequiresProject`` judges an action reserved to the project managers, but for the
    caller who is no contributor and holds the permissions of the rescue: it is let pass, and
    the module of the projects decides on the list under the lock (403 ``NOT_CONTRIBUTOR`` if
    the project has an active project manager).
    """

    def __call__(self, request: Request, actor: Acting, services: ServicesOf) -> None:
        """Refuse the write as the caller stands on the project, or let it run."""
        try:
            super().__call__(request, actor, services)
        except ForbiddenError as refused:
            if refused.code != NOT_CONTRIBUTOR:
                raise


def _lacking_counter(body: object) -> object:
    """Read a counter sent null (only) as absent: the list lacks it (``VALUE_REQUIRED``)."""
    if not isinstance(body, dict):
        return body
    sent = cast("dict[str, object]", body)
    return {
        name: value for name, value in sent.items() if name != "lock_version" or value is not None
    }


type WriteBody = Annotated[ContributorsWrite, BeforeValidator(_lacking_counter), Body()]


def listed_contributors(read: ContributorsRead) -> ContributorList:
    """Describe the contributors read as the contract does."""
    return ContributorList(
        items=[
            Contributor.model_validate(
                {
                    "user_id": view.user_id,
                    "display_name": view.display_name,
                    "kind": view.kind,
                    "is_active": view.is_active,
                }
            )
            for view in read.items
        ],
        lock_version=None if read.lock_version is None else LockVersion(read.lock_version),
    )


def contributor_filters(
    *,
    search: Search = None,
    kinds: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> ContributorFilters:
    """Read the filters of the list; a kind that is none is refused (422)."""
    named = listed("kinds", kinds, ContributorKind)
    return ContributorFilters(
        search=search,
        kinds=None if named is None else frozenset(kind.value for kind in named),
        is_active=is_active,
    )


def contributor_sort(
    sort_by: Annotated[str | None, Query(pattern="^(display_name|kind|is_active)$")] = None,
    sort_order: SortOrder = SortOrder.asc,
) -> ContributorSort:
    """Read the sort the list asks for; none, the project managers first, then by name."""
    return ContributorSort(
        None if sort_by is None else COLUMNS[sort_by], descending=sort_order is SortOrder.desc
    )


@router.get(
    "/projects/{project_id}/contributors",
    operation_id="listContributors",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=ContributorList,
)
def get_contributors(
    project_id: UUID,
    session: Transaction,
    filters: Annotated[ContributorFilters, Depends(contributor_filters)],
    sort: Annotated[ContributorSort, Depends(contributor_sort)],
) -> ContributorList:
    """Give the contributors of a project, filtered, searched and sorted by the server."""
    return listed_contributors(list_contributors(session, project_id, filters, sort))


@router.put(
    "/projects/{project_id}/contributors",
    operation_id="setContributors",
    dependencies=[Depends(RequiresContributorsWrite(CONSULT, CHANGE, manager=True))],
)
def put_contributors(
    project_id: UUID, body: WriteBody, actor: Acting, session: Transaction
) -> ContributorList:
    """Write the whole list of the contributors at the counter read; only a manager may."""
    write = ContributorsToWrite(
        tuple(ContributorEntry(line.user_id.root, line.kind.value) for line in body.contributors),
        body.lock_version.root,
    )
    return listed_contributors(set_contributors(session, project_id, write, viewer_of(actor)))


@router.get(
    "/projects/{project_id}/contributors/suggestions",
    operation_id="listContributorSuggestions",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=list[ContributorSuggestion],
)
def get_contributor_suggestions(
    project_id: UUID, session: Transaction
) -> list[ContributorSuggestion]:
    """Give the accounts the lines of the project propose; none while no line employs a role."""
    return [
        ContributorSuggestion.model_validate(
            {
                "user_id": suggestion.user_id,
                "display_name": suggestion.display_name,
                "is_active": True,
                "org_node_id": suggestion.org_node_id,
                "org_node_label": suggestion.org_node_label,
                "resource_role_ids": list(suggestion.resource_role_ids),
                "resource_role_labels": list(suggestion.resource_role_labels),
            }
        )
        for suggestion in list_contributor_suggestions(session, project_id)
    ]
