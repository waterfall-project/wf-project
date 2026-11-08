# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The history that can be undone, and the paste of a block (WF-IHM-0110, 0050).

``previewPaste`` and ``applyPaste`` (the two steps of a paste of a block of cells, WF-IHM-0050),
``undoLastChange`` and ``redoLastUndo`` (the last change of the caller undone or redone,
WF-IHM-0110) — US-1450/L2.

They write the planning, as the caller who may write it does (``planning.write``, the quality of
contributor of the project); a paste is judged at its preview and again at its confirmation. The
history is kept per revision, per account and per session of sign-in: a token without one is
refused by 403 ``SESSION_ID_MISSING``. An undoing is refused for the permission of the entry it
undoes, which the planning judges once it knows the entry (``remaining.write`` for the state of a
task).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import PasteApply, PastePreview
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.nodes import STRUCTURE, Placed, Writing, written_of
from waterfall.core.planning.interface import (
    PasteBlock,
    PasteConfirmation,
    PasteRefusal,
    UndoDone,
    apply_paste,
    preview_paste,
    redo_last_undo,
    undo_last_change,
)

router = APIRouter(tags=["revisions"])

CONSULT = "planning.read"
CHANGE = "planning.write"
REVISION = "/projects/{project_id}/revisions/{revision_id}"


def _refused(each: PasteRefusal) -> dict[str, Any]:
    """Write the refusal of a cell of a block as the contract does (``PasteRejection``)."""
    refusal: dict[str, Any] = {"row": each.row, "code": each.code}
    if each.column is not None:
        refusal["column"] = each.column
    if each.params:
        refusal["params"] = dict(each.params)
    return refusal


def _undone(done: UndoDone) -> dict[str, Any]:
    """Write what an undoing or a redoing did as the contract does (``UndoResult``)."""
    return {
        "undone": {
            "kind": done.kind,
            "node_ids": [str(each) for each in done.node_ids],
            "risk_ids": [],
        },
        "written": written_of(done.written),
        "remaining_depth": done.remaining_depth,
    }


@router.post(
    f"{STRUCTURE}/nodes/paste-preview",
    operation_id="previewPaste",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def post_paste_preview(
    place: Placed, body: PastePreview, writer: Writing, session: Transaction
) -> dict[str, Any]:
    """Judge a block pasted from a spreadsheet, and keep its plan; nothing is written."""
    block = PasteBlock(
        target_node_id=body.target_node_id.root,
        target_column=body.target_column.value,
        rows=tuple(tuple(cells) for cells in body.rows),
    )
    planned = preview_paste(session, place, block, writer)
    # The service does not create a node by paste yet: the rows beyond the last node are refused.
    return {
        "paste_id": str(planned.paste_id),
        "accepted": planned.accepted,
        "created": 0,
        "rejected": [_refused(each) for each in planned.rejected],
    }


@router.post(
    f"{STRUCTURE}/nodes/paste",
    operation_id="applyPaste",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def post_paste(
    place: Placed, body: PasteApply, writer: Writing, session: Transaction
) -> dict[str, Any]:
    """Write the accepted rows of a plan in one operation, at the counter of the structure read."""
    confirmation = PasteConfirmation(body.paste_id.root, body.lock_version.root)
    applied = apply_paste(session, place, confirmation, writer)
    return {
        **written_of(applied.written),
        "rejected": [_refused(each) for each in applied.rejected],
    }


@router.post(
    f"{REVISION}/undo",
    operation_id="undoLastChange",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def post_undo(
    project_id: UUID, revision_id: UUID, actor: Acting, writer: Writing, session: Transaction
) -> dict[str, Any]:
    """Undo the last change of the caller in a revision, one by one, in reverse order."""
    done = undo_last_change(session, project_id, revision_id, writer, actor.permissions)
    return _undone(done)


@router.post(
    f"{REVISION}/redo",
    operation_id="redoLastUndo",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def post_redo(
    project_id: UUID, revision_id: UUID, actor: Acting, writer: Writing, session: Transaction
) -> dict[str, Any]:
    """Redo the last undoing of the caller in a revision, in the order of the changes."""
    done = redo_last_undo(session, project_id, revision_id, writer, actor.permissions)
    return _undone(done)
