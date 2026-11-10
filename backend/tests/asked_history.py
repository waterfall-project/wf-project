# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/history.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1450 declares each operation it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "planning.read"
CHANGE = "planning.write"

# The permissions of the three grids, one at least of which a paste asks for (#2601).
ENTRIES = ("planning.write", "estimate.write", "remaining.write")

# The permissions each operation asks for, in the order they are evaluated: an undoing and a
# redoing write the planning, the command ``edit_planning`` of the structure; a paste, which the
# three grids make alike, one at least of their permissions (#2601). An undoing is refused besides
# for the permission of the entry it undoes, which the planning judges once it knows the entry
# (``remaining.write`` for the state of a task).
ASKED: dict[str, tuple[str, ...]] = {
    "previewPaste": (CONSULT, *ENTRIES),
    "applyPaste": (CONSULT, *ENTRIES),
    "undoLastChange": (CONSULT, CHANGE),
    "redoLastUndo": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "previewPaste": "contributor",
    "applyPaste": "contributor",
    "undoLastChange": "contributor",
    "redoLastUndo": "contributor",
}
