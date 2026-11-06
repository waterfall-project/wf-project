# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/cost_types.py`` ask for: the natures and the categories of cost.

``test_access_evaluation.py`` gathers them; US-0820 declares each operation it serves.
"""

CHANGE = "cost_settings.write"

# The permissions each operation asks for, in the order they are evaluated. The active natures
# are read by any open session (WF-DEV-0020): the lists ask for none; every write asks
# for the permission to change the cost settings.
ASKED: dict[str, tuple[str, ...]] = {
    "listCostTypes": (),
    "createCostType": (CHANGE,),
    "updateCostType": (CHANGE,),
    "setCostTypeActivation": (CHANGE,),
}
# The permission a list asks for besides when it asks for deactivated objects (decision of the
# author of 2026-11-06, #2084): the permission to change, not to read, as the contract refuses.
INACTIVE: dict[str, str] = {"listCostTypes": CHANGE}
