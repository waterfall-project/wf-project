# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects (FBS-4.2).

``listProjects``, ``createProject``, ``getProject`` and ``updateProject``.

A project is created by the holder of the permission to create one (``project_create``); every
other operation names the project and is judged by ``RequiresProject``: the permission of the
settings of the project and the quality of the caller on it, which the module of the projects
reads (WF-ADM-0110, WF-PRJ-0060). The list holds the projects the caller may open and no other.
The code of a project is judged by the validation of the body, to name the barre oblique alone
when a code holds it, however blank the rest (``PROJECT_CODE_INVALID``, #1658).
"""

from datetime import UTC
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AfterValidator, AwareDatetime, Field
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import (
    LockVersion,
    PaginationMeta,
    Percent,
    PlanningDate,
    Project,
    ProjectClient,
    ProjectState,
    SortOrder,
)
from waterfall.api.evaluation import Acting, Requires, RequiresProject
from waterfall.api.queries import Search, listed, refuse_query
from waterfall.core.projects.interface import (
    ProjectChange,
    ProjectColumn,
    ProjectDraft,
    ProjectFilters,
    ProjectPage,
    ProjectSort,
    ProjectView,
    Viewer,
    create_project,
    list_projects,
    read_project,
    update_project,
)
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    VALIDATION_FAILED,
    FieldError,
    UnprocessableError,
    json_pointer,
)

router = APIRouter(tags=["projects"])

CONSULT = "project_settings.read"
CHANGE = "project_settings.write"
CREATE = "project_create"
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
CODE_LENGTH = 50
# The one separator of the element of the ERP that bears the code (WF-CRE-0020).
FORBIDDEN_IN_CODE = "/"
PROJECT_CODE_INVALID = "PROJECT_CODE_INVALID"
# The fields of an update that are never null (a null sent is refused), and the other ones, which
# a null empties; the contract types ``order_received_on`` and ``client`` so (WF-PRJ-0080).
NEVER_NULL = ("label", "inflation_rate", "win_probability")


def _checked(code: str) -> str:
    """Refuse a code that holds the barre oblique, however blank the rest; or a blank one.

    The barre oblique comes first (contract, ``ProjectCode``, D-07); a code made of blanks only is
    refused as any blank label is, and an empty one before, by the bounds of its length.
    """
    if FORBIDDEN_IN_CODE in code:
        raise PydanticCustomError(
            PROJECT_CODE_INVALID,
            "a project code holds a character that separates the element of the ERP",
            {"forbidden_characters": [FORBIDDEN_IN_CODE]},
        )
    if not code.strip():
        message = "a project code is not blank"
        raise ValueError(message)
    return code


# ``ProjectCode`` of the contract, judged field by field: the generated model gives one refusal
# to a pattern that fails, where the contract names three.
Code = Annotated[str, Field(min_length=1, max_length=CODE_LENGTH), AfterValidator(_checked)]


class ProjectCreateBody(ContractModel):
    """``ProjectCreate`` of the contract, its code judged as ``Code`` judges it."""

    label: Annotated[str, Field(min_length=1, max_length=300, pattern=r"\S")]
    description: str | None = None
    client: ProjectClient | None = None
    code: Code | None = None


class ProjectUpdateBody(ContractModel):
    """``ProjectUpdate`` of the contract, its code judged as ``Code`` judges it."""

    label: Annotated[str | None, Field(min_length=1, max_length=300, pattern=r"\S")] = None
    description: str | None = None
    client: ProjectClient | None = None
    code: Code | None = None
    inflation_rate: Percent | None = None
    win_probability: Percent | None = None
    order_received_on: PlanningDate | None = None
    lock_version: LockVersion


def _plain(value: Decimal) -> str:
    """Write a decimal as the contract's examples do, without a useless zero: ``0.03``."""
    return format(value.normalize(), "f")


def described(session: Session, views: list[ProjectView]) -> list[Project]:
    """Describe projects as the contract does, their authors named as they are today."""
    wanted = {
        author
        for view in views
        for author in (view.created_by, view.updated_by)
        if author is not None
    }
    authors = read_authors(session, wanted)
    return [
        Project.model_validate(
            {
                "project_id": view.project_id,
                "label": view.label,
                "description": view.description,
                "client": view.client,
                "code": view.code,
                "state": view.state,
                "inflation_rate": _plain(view.inflation_rate),
                "win_probability": _plain(view.win_probability),
                "order_received_on": view.order_received_on,
                "reference_revision_id": view.reference_revision_id,
                "current_revision_id": view.current_revision_id,
                "available_commands": [
                    {
                        "command": command.command,
                        "is_available": command.is_available,
                        "missing_conditions": list(command.missing_conditions),
                    }
                    for command in view.commands
                ],
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
            }
        )
        for view in views
    ]


def viewer_of(actor: Acting) -> Viewer:
    """Give the caller as the module of the projects reads it: its account and its permissions."""
    return Viewer(actor.user_id, actor.permissions)


def project_filters(
    *,
    search: Search = None,
    states: Annotated[str | None, Query()] = None,
    is_contributor: Annotated[bool, Query()] = False,
    since: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    until: Annotated[AwareDatetime | None, Query(alias="to")] = None,
) -> ProjectFilters:
    """Read the filters of the list; a period whose end precedes its start is refused (422).

    The refusal names the end, the start given as its minimum, the rule of every period of the
    contract; an end equal to the start is an empty period.
    """
    named = listed("states", states, ProjectState)
    if since is not None and until is not None and until < since:
        refuse_query(
            [FieldError("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": since.astimezone(UTC)})]
        )
    return ProjectFilters(
        search=search,
        states=None if named is None else frozenset(state.value for state in named),
        contributor_only=is_contributor,
        since=since,
        until=until,
    )


def project_sort(
    sort_by: ProjectColumn | None = None, sort_order: SortOrder = SortOrder.asc
) -> ProjectSort:
    """Read the sort the list asks for; none, the projects changed last first."""
    return ProjectSort(sort_by, descending=sort_order is SortOrder.desc)


def page_of(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProjectPage:
    """Read the page asked for: fifty projects from the first one, unless said otherwise."""
    return ProjectPage(limit, offset)


@router.get(
    "/projects",
    operation_id="listProjects",
    dependencies=[Depends(Requires(CONSULT))],
    response_model=None,
)
def get_projects(
    actor: Acting,
    session: Transaction,
    filters: Annotated[ProjectFilters, Depends(project_filters)],
    sort: Annotated[ProjectSort, Depends(project_sort)],
    page: Annotated[ProjectPage, Depends(page_of)],
) -> dict[str, Any]:
    """Give a page of the projects the caller may open, filtered and sorted by the server."""
    read = list_projects(session, viewer_of(actor), filters, sort, page)
    meta = {
        **PaginationMeta(limit=page.limit, offset=page.offset, total=read.total).model_dump(),
        "states": list(read.states),
    }
    items = described(session, read.projects)
    return {
        "items": [item.model_dump(mode="json", exclude_unset=True) for item in items],
        "meta": meta,
    }


@router.post(
    "/projects",
    operation_id="createProject",
    dependencies=[Depends(Requires(CREATE))],
    status_code=201,
    response_model_exclude_unset=True,
)
def post_project(
    body: ProjectCreateBody, actor: Acting, account: Caller, session: Transaction
) -> Project:
    """Create a project once the minimal reference holds; its creator is its project manager."""
    draft = ProjectDraft(
        label=body.label,
        description=body.description,
        client=None if body.client is None else body.client.root,
        code=body.code,
    )
    act = Act(account.user_id, utc_now())
    return described(session, [create_project(session, draft, act, viewer_of(actor))])[0]


@router.get(
    "/projects/{project_id}",
    operation_id="getProject",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model_exclude_unset=True,
)
def get_project(project_id: UUID, actor: Acting, session: Transaction) -> Project:
    """Give a project, with the commands its reader holds on it (WF-PRJ-0080)."""
    return described(session, [read_project(session, project_id, viewer_of(actor))])[0]


def change_of(body: ProjectUpdateBody) -> ProjectChange:
    """Read the change a body carries; a null sent to a field never null is refused (422)."""
    carried = body.model_fields_set
    faults = [
        FieldError(json_pointer(name), VALIDATION_FAILED)
        for name in NEVER_NULL
        if name in carried and getattr(body, name) is None
    ]
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    values: dict[str, object] = {}
    plain = {
        "label": body.label,
        "description": body.description,
        "code": body.code,
        "client": None if body.client is None else body.client.root,
        "inflation_rate": None
        if body.inflation_rate is None
        else Decimal(body.inflation_rate.root.root),
        "win_probability": None
        if body.win_probability is None
        else Decimal(body.win_probability.root.root),
        "order_received_on": (
            None if body.order_received_on is None else body.order_received_on.root
        ),
    }
    values.update({name: value for name, value in plain.items() if name in carried})
    return ProjectChange(values, body.lock_version.root)


@router.patch(
    "/projects/{project_id}",
    operation_id="updateProject",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE, manager=True))],
    response_model_exclude_unset=True,
)
def patch_project(
    project_id: UUID, body: ProjectUpdateBody, actor: Acting, account: Caller, session: Transaction
) -> Project:
    """Change the attributes of a project at the version read; only its managers may."""
    act = Act(account.user_id, utc_now())
    changed = update_project(session, project_id, change_of(body), act, viewer_of(actor))
    return described(session, [changed])[0]
