# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/risk_register.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-2600 declares the operations it serves, with the
quality on its project each asks for besides.
"""

# The permissions each operation asks for, in the order they are evaluated.
ASKED: dict[str, tuple[str, ...]] = {
    "listRisks": ("risks.read",),
    "getProjectRiskMatrix": ("risks.read",),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "listRisks": "consultation",
    "getProjectRiskMatrix": "consultation",
}
