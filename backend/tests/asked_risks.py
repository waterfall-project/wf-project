# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/risks.py`` ask for (EP-08).

``test_access_evaluation.py`` gathers them; US-2570 declares the operations it serves, with the
quality on its project each asks for besides.
"""

CONSULT = "risks.read"
CHANGE = "risks.write"

# The permissions each operation asks for, in the order they are evaluated: a risk is read by the
# holder of the permission to consult the risks, declared and renamed by the holder of the
# permission to enter them (US-2570/L1).
ASKED: dict[str, tuple[str, ...]] = {
    "createRisk": (CONSULT, CHANGE),
    "getRisk": (CONSULT,),
    "updateRisk": (CONSULT, CHANGE),
}
# The quality on its project each operation that names one asks for, evaluated by
# ``RequiresProject``: ``consultation``, ``contributor`` or ``project_manager`` (WF-ADM-0110).
ON_PROJECT: dict[str, str] = {
    "createRisk": "contributor",
    "getRisk": "consultation",
    "updateRisk": "contributor",
}
