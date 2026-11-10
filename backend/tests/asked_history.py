# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/history.py`` ask for (EP-06).

``test_access_evaluation.py`` gathers them; US-1450 declares each operation it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "planning.read"

# The permissions of the three grids, one at least of which a paste, an undoing and a redoing ask
# for (#2601, #2774).
ENTRIES = ("planning.write", "estimate.write", "remaining.write")

# The permissions each operation asks for, in the order they are evaluated: a paste, an undoing and
# a redoing, which the three grids make alike, one at least of their permissions (#2601, #2774). A
# paste is refused besides without ``planning.write`` when it writes the columns of a task (#2775),
# an undoing and a redoing for the permission of the write of the entry, which the planning judges
# once it knows the entry (``test_nodes_entries.py``).
ASKED: dict[str, tuple[str, ...]] = {
    "previewPaste": (CONSULT, *ENTRIES),
    "applyPaste": (CONSULT, *ENTRIES),
    "undoLastChange": (CONSULT, *ENTRIES),
    "redoLastUndo": (CONSULT, *ENTRIES),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "previewPaste": "contributor",
    "applyPaste": "contributor",
    "undoLastChange": "contributor",
    "redoLastUndo": "contributor",
}
