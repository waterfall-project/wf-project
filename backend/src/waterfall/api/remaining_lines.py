# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line of the remaining to commit reestimated (WF-RAE-0040, WF-IHM-0110).

``setLineRemaining`` (US-1580/L2), under the quality of contributor and ``remaining.write``, read
under ``remaining.read``; the reading of the lines, their creation and their deletion stay with the
routers of the planning and of the estimate, which ask the facet of their kind.

Only the figures of ``reestimated_amount_basis`` sent change, at the counter read; a field the
schema does not know — an amount, which no entry carries (WF-RAE-0040) — is refused (422
``FIELD_NOT_ACCEPTED``). The answer is what a write of the tree gives back (``NodesWritten``): the
line, and its task when the entry completes it, the ancestors recomputed.
"""

from decimal import Decimal
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import RootModel

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import ReestimatedAmountBasis, RemainingUpdate
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import (
    STRUCTURE,
    Placed,
    Sent,
    Writing,
    unknown_fields,
    written_of,
)
from waterfall.core.estimate.interface import LineEntry, LineRemaining, set_line_remaining
from waterfall.platform.errors import VALIDATION_FAILED, UnprocessableError

router = APIRouter(tags=["remaining"])

CONSULT = "remaining.read"
CHANGE = "remaining.write"
BASIS = "reestimated_amount_basis"
MAX_ROOTS = 2


def _figure(value: Any) -> Decimal | None:
    """Read a figure a body sends, none if null."""
    if value is None:
        return None
    # In the body received, the quantity is the contract's `Decimal`, a root model of a string (one
    # level); `Hours` is a root model of that `Decimal` (two levels); `Money` is a root model of a
    # string (one). Two levels are peeled; a third would be no figure, and `Decimal` refuses it.
    root: object = value
    for _ in range(MAX_ROOTS):
        if isinstance(root, RootModel):
            root = cast("RootModel[Any]", root).root
    return Decimal(str(root))


def remaining_entry(body: RemainingUpdate, raw: Sent) -> LineRemaining:
    """Read what a re-estimate sends of a line; refuse a field its schema does not know (422)."""
    unknown = unknown_fields(raw, RemainingUpdate, "")
    unknown += unknown_fields(raw.get(BASIS), ReestimatedAmountBasis, f"/{BASIS}")
    if unknown:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(unknown))
    basis = body.reestimated_amount_basis
    figures = LineEntry(
        quantity=_figure(basis.quantity),
        hours=_figure(basis.hours),
        unit_disbursement=_figure(basis.unit_disbursement),
        sent=frozenset(basis.model_fields_set),
        lock_version=body.lock_version.root,
    )
    completed_on = None if body.completed_on is None else body.completed_on.root
    return LineRemaining(figures, body.reason, completed_on)


@router.put(
    f"{STRUCTURE}/nodes/{{node_id}}/remaining",
    operation_id="setLineRemaining",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def put_remaining(
    place: Placed,
    node_id: UUID,
    entry: Annotated[LineRemaining, Depends(remaining_entry)],
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Re-estimate a line at the counter read; complete its task when its last open line is 0."""
    return written_of(set_line_remaining(session, place, node_id, entry, writer))
