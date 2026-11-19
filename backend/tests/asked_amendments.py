# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/amendments.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-2550 declares the operations it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "revisions.read"
CHANGE = "revisions.write"

# The permissions each operation asks for, in the order they are evaluated: a differential is
# opened by the holder of the permission to manage the revisions, as a revision is (US-2550/L3).
ASKED: dict[str, tuple[str, ...]] = {
    "createCostStructure": (CONSULT, CHANGE),
    # The abandonment is guarded as the opening is: ``create_structure`` (US-2550/L4).
    "deleteCostStructure": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "createCostStructure": "contributor",
    "deleteCostStructure": "contributor",
}
