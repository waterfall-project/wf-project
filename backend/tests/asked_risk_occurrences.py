# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/risk_occurrences.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-2620 declares the operations it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "risks.read"

# The permissions each operation asks for, in the order they are evaluated: the report of an
# occurrence is read by whoever consults the risks of the project (US-2620/L1); the occurrence
# itself is the permission of its own, which includes the merge it triggers (US-2620/L2).
ASKED: dict[str, tuple[str, ...]] = {
    "getRiskOccurrenceReport": (CONSULT,),
    "declareRiskOccurrence": (CONSULT, "risk_occurrence"),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "getRiskOccurrenceReport": "consultation",
    "declareRiskOccurrence": "contributor",
}
