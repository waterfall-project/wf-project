# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line of an estimate changed (WF-DEV-0020, WF-IHM-0110).

``updateEstimateLine`` (US-1490/L3); the creation, the deletion, the move and the reading of a line
stay with the routers of the planning, which ask the facet of its kind.

The line is written by the contributors of the project who may write the estimate
(``estimate.write``, read under ``estimate.read``), cell by cell: only what is sent changes, at the
counter read, and the answer is what a write of the tree gives back (``NodesWritten``).
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import EstimateLineUpdate
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import (
    STRUCTURE,
    Sent,
    line_entry,
    place_of,
    unknown_fields,
    writer_of,
    written_of,
)
from waterfall.core.estimate.interface import LineEntry, update_line
from waterfall.core.planning.interface import Place, Writer
from waterfall.platform.errors import VALIDATION_FAILED, UnprocessableError

router = APIRouter(tags=["estimate"])

CONSULT = "estimate.read"
CHANGE = "estimate.write"


def line_change(body: EstimateLineUpdate, raw: Sent) -> LineEntry:
    """Read what a modification sends of a line; refuse a field unknown, or nothing sent (422)."""
    sent = frozenset(body.model_fields_set - {"lock_version"})
    unknown = unknown_fields(raw, EstimateLineUpdate, "")
    # A modification sends one field at least beside its counter (``minProperties``).
    if unknown or not sent:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(unknown))
    return line_entry(body, sent, body.lock_version.root)


@router.patch(
    f"{STRUCTURE}/nodes/{{node_id}}/estimate-line",
    operation_id="updateEstimateLine",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def patch_line(
    place: Annotated[Place, Depends(place_of)],
    node_id: UUID,
    entry: Annotated[LineEntry, Depends(line_change)],
    writer: Annotated[Writer, Depends(writer_of)],
    session: Transaction,
) -> dict[str, Any]:
    """Write what is sent of a line at the counter read; nothing else changes."""
    return written_of(update_line(session, place, node_id, entry, writer))
