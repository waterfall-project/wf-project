# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/risk_provisions.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-2580 declares the operations it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "risks.read"
CHANGE = "risks.write"

# The permissions each operation asks for, in the order they are evaluated.
# The provision of a risk is changed by whoever may enter the risks (US-2580/L1).
ASKED: dict[str, tuple[str, ...]] = {"updateRiskProvision": (CONSULT, CHANGE)}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {"updateRiskProvision": "contributor"}
