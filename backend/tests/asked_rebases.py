# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/rebases.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-3050 declares the operations it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "revisions.read"
CHANGE = "revisions.write"

# The permissions each operation asks for, in the order they are evaluated: the report of an update
# is read by whoever consults the revisions, without a 403, as the report of a merge (US-3050/L3).
ASKED: dict[str, tuple[str, ...]] = {
    "getStructureRebaseReport": (CONSULT,),
    # The update is guarded as the opening of a differential is: ``create_structure`` (US-3050/L4).
    "rebaseCostStructure": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "getStructureRebaseReport": "consultation",
    "rebaseCostStructure": "contributor",
}
