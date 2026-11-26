# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amendments of a revision: a differential opened, read, abandoned (WF-REV-0100).

``createCostStructure`` (US-2550/L3), a differential opened as the copy of the main structure, and
``deleteCostStructure`` (US-2550/L4), a differential abandoned, under the command
``create_structure`` of the revision: a write of the revision by the holder of the permission to
manage the revisions, as the opening of a revision is (``revisions.write``), by a contributor of
the project. The differential is answered as the list of the structures gives it, with its
commands, at its first version.

``listNodes`` is served here (US-2550/L3): the tree of a structure, read by whoever may consult the
planning, as ``nodes`` reads it for every structure but a differential. A differential is read as a
diff with its base, the copy of the main structure it keeps (US-3050/L2), which the server
computes: each node carries its difference — added, removed, modified, unchanged — and what changes
about it (``NodeDifference``, ``NodeChange``), the nodes it removes returned at the place they had,
read-only, and not counted in the totals; ``difference`` keeps the marks it names
(``NodeDifferenceFilter``) and has no effect on another structure. A base is a structure no
operation serves: named by its identifier, it is not found (404).

Registered by the application from US-2550/L1; the opening served by US-2550/L3.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from waterfall.api.authentication import Transaction
from waterfall.api.comparison import DifferenceAsked
from waterfall.api.contract.models import NodeListMeta, StructureCreate, StructureKind
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.nodes import (
    CONSULT as CONSULT_PLANNING,
)
from waterfall.api.nodes import (
    STRUCTURE,
    Placed,
    Writing,
    gives_progress,
    node_body,
    node_reading,
    nodes_body,
    read_body,
    totals_body,
    whole_nodes,
)
from waterfall.api.projects import viewer_of
from waterfall.api.queries import listed
from waterfall.api.revisions import structure_body
from waterfall.core.estimate.interface import Comparison, read_differential
from waterfall.core.planning.interface import (
    NodeFilters,
    abandon_differential,
    list_records,
    open_differential,
)
from waterfall.core.revisions.interface import (
    read_against_base,
    read_cost_structure,
    structure_facts,
)
from waterfall.platform.errors import (
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    NotFoundError,
    UnprocessableError,
)

router = APIRouter(tags=["revisions"])

CONSULT_REVISIONS = "revisions.read"
CHANGE = "revisions.write"
STRUCTURES = "/projects/{project_id}/revisions/{revision_id}/structures"


def revision_of(project_id: UUID, revision_id: UUID) -> tuple[UUID, UUID]:
    """Give the revision the path names, with its project."""
    return project_id, revision_id


RevisionOf = Annotated[tuple[UUID, UUID], Depends(revision_of)]


@router.post(
    STRUCTURES,
    operation_id="createCostStructure",
    dependencies=[Depends(RequiresProject(CONSULT_REVISIONS, CHANGE))],
    status_code=201,
    response_model=None,
)
def post_structure(
    revision: RevisionOf,
    body: StructureCreate,
    writer: Writing,
    actor: Acting,
    session: Transaction,
) -> dict[str, Any]:
    """Open a differential in a revision, the copy of its main structure (WF-REV-0100).

    Only a differential is opened here: the main structure exists from its revision, and the own
    estimate of a risk is born with its risk (422 on ``/kind`` otherwise). Refused on a marked
    revision and while a background task writes in the project (409).
    """
    if body.kind != StructureKind.amendment:
        fault = FieldError("/kind", VALIDATION_FAILED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    project_id, revision_id = revision
    structure_id = open_differential(session, revision, body.label, writer)
    view = read_cost_structure(session, project_id, revision_id, structure_id, viewer_of(actor))
    return structure_body(view)


@router.delete(
    STRUCTURE,
    operation_id="deleteCostStructure",
    dependencies=[Depends(RequiresProject(CONSULT_REVISIONS, CHANGE))],
    status_code=204,
)
def delete_structure(
    place: Placed,
    lock_version: Annotated[int, Query(ge=0, le=2147483647)],
    writer: Writing,
    session: Transaction,
) -> Response:
    """Abandon a differential that is not merged, at the counter read (WF-REV-0100).

    Under the command ``delete`` of the structure, guarded as the opening of a differential is:
    its nodes, their lines and their images are deleted with it, the history of its entries and
    the plans of its pastes forgotten; irreversible, inscribed in the journal. Refused on the main
    structure, the own estimate of a risk and a merged differential, on a marked revision and
    while a background task writes (409), and at another counter (412).
    """
    abandon_differential(session, place, lock_version, writer)
    return Response(status_code=204)


def differential_body(found: Comparison, fields: frozenset[str] | None) -> dict[str, Any]:
    """Write the reading of a differential: each node with its mark and what changes about it."""
    meta = NodeListMeta.model_validate(
        {"summary_depth": found.summary_depth, "scheduled_at": found.scheduled_at}
    )
    return {
        "items": [
            {
                **node_body(each.view, fields),
                "difference": each.difference,
                "changes": list(each.changes),
            }
            for each in found.items
        ],
        "totals": totals_body(found.totals.task_count, found.totals.totals),
        "meta": meta.model_dump(mode="json"),
    }


@router.get(
    f"{STRUCTURE}/nodes",
    operation_id="listNodes",
    tags=["planning"],
    dependencies=[Depends(RequiresProject(CONSULT_PLANNING))],
    response_model=None,
)
def get_nodes(
    place: Placed,
    asked: Annotated[tuple[NodeFilters, frozenset[str] | None], Depends(node_reading)],
    session: Transaction,
    difference: Annotated[str | None, Query()] = None,
) -> Response:
    """Give the nodes of a structure retained, depth first, their totals and its meta.

    A differential, and the own estimate of a risk whole, are read against their base, each node
    marked (``NodeDifference``; US-3050, EP-30).
    """
    filters, fields = asked
    marks = listed("difference", difference, DifferenceAsked)
    facts = structure_facts(session, place.project_id, place.structure_id, lock=False)
    if facts.revision_id != place.revision_id:
        raise NotFoundError(NOT_FOUND)
    if read_against_base(session, place.project_id, facts):
        kept = None if marks is None else tuple(each.value for each in marks)
        found = read_differential(session, place, filters, kept, node_body)
        return read_body(differential_body(found, fields))
    if filters == NodeFilters():
        return whole_nodes(session, place, fields)
    read = list_records(session, place, filters, progress=gives_progress(fields))
    return read_body(nodes_body(read, fields))
