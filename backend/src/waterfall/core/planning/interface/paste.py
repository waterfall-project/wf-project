# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste of a block of cells into the planning: its plan previewed, then applied.

``previewPaste`` judges each cell of the block on the facet task in the order of ``NodeColumn``, by
the very functions of the entry of a cell, and keeps the plan with the counter of the structure
(``history.keep_plan``); ``applyPaste`` reads the plan again, refuses a structure that moved (412),
judges again and writes the rows accepted in one operation and one entry of the history (EP-06,
"L'historique annulable et le collage").

Declared by US-1380/L1; US-1450/L2 fills them, and gives each its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def preview_paste(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Judge a block of cells, and keep its plan (``previewPaste``)."""
    msg = "preview_paste is filled by US-1450/L2"
    raise NotImplementedError(msg)


def apply_paste(session: Session, project_id: UUID, plan_id: UUID, act: Act) -> None:
    """Apply the plan of a paste, and give the nodes written (``applyPaste``)."""
    msg = "apply_paste is filled by US-1450/L2"
    raise NotImplementedError(msg)
