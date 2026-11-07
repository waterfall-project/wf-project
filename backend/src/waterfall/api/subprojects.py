# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of a project (WF-PRJ-0050).

``listSubprojects``, ``createSubproject``, ``updateSubproject`` and ``deleteSubproject``.

A project is read by its contributors and by the holders of ``all_projects_read``
(``RequiresProject``); its subprojects are written by its project managers, as the command
``update`` of the project is. The body is judged field by field: a code too long is
``VALUE_TOO_LONG``; one that holds a character a tab refuses or is a reserved name is
``SUBPROJECT_CODE_INVALID``, which the module of the projects names (#1502).
"""

from typing import Annotated, Any, LiteralString, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import AfterValidator, Field
from pydantic_core import PydanticCustomError
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction
from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import LockVersion, SortOrder, Subproject
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.queries import Search
from waterfall.core.projects.interface import (
    SubprojectChange,
    SubprojectColumn,
    SubprojectFilters,
    SubprojectSort,
    SubprojectView,
    SubprojectWrite,
    code_faults,
    create_subproject,
    delete_subproject,
    list_subprojects,
    update_subproject,
)
from waterfall.core.projects.tables import SUBPROJECT_CODE_LENGTH
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["projects"])

CONSULT = "project_settings.read"
CHANGE = "project_settings.write"


def _checked(code: str) -> str:
    """Refuse a code that is blank, holds a character a tab refuses or is a reserved name.

    The service judges the same (``code_faults``), for the witness; here the faults of the code
    add to those of the label, as the contract's ``fields`` names each field.
    """
    for fault in code_faults(code):
        message = (
            "a subproject code cannot be blank"
            if fault.code == "VALUE_REQUIRED"
            else "a subproject code cannot name a tab"
        )
        raise PydanticCustomError(cast("LiteralString", fault.code), message, dict(fault.params))
    return code


# ``DeclaredSubprojectCode`` of the contract, judged field by field: the generated model gives one
# refusal to a pattern that fails, where the contract names three; the characters and the names
# are judged by the module of the projects.
Code = Annotated[
    str, Field(min_length=1, max_length=SUBPROJECT_CODE_LENGTH), AfterValidator(_checked)
]
Label = Annotated[str, Field(min_length=1, max_length=300, pattern=r"\S")]


class SubprojectWriteBody(ContractModel):
    """``SubprojectWrite`` of the contract, its code judged as ``Code`` judges it."""

    code: Code
    label: Label


class SubprojectUpdateBody(SubprojectWriteBody):
    """``SubprojectUpdate`` of the contract."""

    lock_version: LockVersion


def described(session: Session, views: list[SubprojectView]) -> list[Subproject]:
    """Describe subprojects as the contract does, their authors named as they are today."""
    wanted = {
        author
        for view in views
        for author in (view.created_by, view.updated_by)
        if author is not None
    }
    authors = read_authors(session, wanted)
    return [
        Subproject.model_validate(
            {
                "subproject_id": view.subproject_id,
                "code": view.code,
                "label": view.label,
                "has_actual_costs": view.has_actual_costs,
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


def subproject_filters(
    *, search: Search = None, has_actual_costs: Annotated[bool | None, Query()] = None
) -> SubprojectFilters:
    """Read the filters of the list."""
    return SubprojectFilters(search, has_actual_costs)


def subproject_sort(
    sort_by: SubprojectColumn | None = None, sort_order: SortOrder = SortOrder.asc
) -> SubprojectSort:
    """Read the sort the list asks for; none, the code."""
    return SubprojectSort(sort_by, descending=sort_order is SortOrder.desc)


@router.get(
    "/projects/{project_id}/subprojects",
    operation_id="listSubprojects",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_subprojects(
    project_id: UUID,
    actor: Acting,
    session: Transaction,
    filters: Annotated[SubprojectFilters, Depends(subproject_filters)],
    sort: Annotated[SubprojectSort, Depends(subproject_sort)],
) -> list[dict[str, Any]]:
    """Give the subprojects of a project, searched, filtered and sorted by the server."""
    views = list_subprojects(session, project_id, viewer_of(actor), filters, sort)
    return [item.model_dump(mode="json", exclude_unset=True) for item in described(session, views)]


@router.post(
    "/projects/{project_id}/subprojects",
    operation_id="createSubproject",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE, manager=True))],
    status_code=201,
    response_model=Subproject,
    response_model_exclude_unset=True,
)
def post_subproject(
    project_id: UUID,
    body: SubprojectWriteBody,
    actor: Acting,
    session: Transaction,
) -> Subproject:
    """Create a subproject of a project; only its managers may."""
    act = Act(actor.user_id, utc_now())
    view = create_subproject(
        session, project_id, SubprojectWrite(body.code, body.label), act, viewer_of(actor)
    )
    return described(session, [view])[0]


@router.patch(
    "/projects/{project_id}/subprojects/{subproject_id}",
    operation_id="updateSubproject",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE, manager=True))],
    response_model=Subproject,
    response_model_exclude_unset=True,
)
def patch_subproject(
    project_id: UUID,
    subproject_id: UUID,
    body: SubprojectUpdateBody,
    actor: Acting,
    session: Transaction,
) -> Subproject:
    """Change the code and the label of a subproject at the version read; only managers may."""
    act = Act(actor.user_id, utc_now())
    change = SubprojectChange(
        subproject_id, SubprojectWrite(body.code, body.label), body.lock_version.root
    )
    view = update_subproject(session, project_id, change, act, viewer_of(actor))
    return described(session, [view])[0]


@router.delete(
    "/projects/{project_id}/subprojects/{subproject_id}",
    operation_id="deleteSubproject",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE, manager=True))],
    status_code=204,
)
def remove_subproject(
    project_id: UUID,
    subproject_id: UUID,
    lock_version: Annotated[int, Query(ge=0)],
    actor: Acting,
    session: Transaction,
) -> Response:
    """Delete for good a subproject that nothing cites, at the version read; only managers may."""
    delete_subproject(session, project_id, subproject_id, lock_version, viewer_of(actor))
    return Response(status_code=204)
