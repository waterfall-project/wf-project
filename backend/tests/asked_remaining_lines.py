# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/remaining_lines.py`` ask for (EP-09).

``test_access_evaluation.py`` gathers them; US-1580 declares each operation it serves, with the
quality on its project each asks for besides.
"""

# The permissions each operation asks for, in the order they are evaluated: a line is re-estimated
# by the holder of the permission to write the remaining to commit, read under that to consult it
# (US-1580/L2).
ASKED: dict[str, tuple[str, ...]] = {
    "setLineRemaining": ("remaining.read", "remaining.write"),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "setLineRemaining": "contributor",
}
