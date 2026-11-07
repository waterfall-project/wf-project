# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/org_nodes.py`` ask for: the tree of the organisation.

``test_access_evaluation.py`` gathers them; US-0840 declares each operation it serves.
"""

CHANGE = "resource_settings.write"

# The permissions each operation asks for, in the order they are evaluated: the active nodes are
# read by any open session (#1745), every write asks for the permission to change the settings.
ASKED: dict[str, tuple[str, ...]] = {
    "listOrgNodes": (),
    "createOrgNode": (CHANGE,),
    "updateOrgNode": (CHANGE,),
    "setOrgNodeActivation": (CHANGE,),
}
# The permission a list asks for besides when it asks for deactivated objects.
INACTIVE: dict[str, str] = {"listOrgNodes": CHANGE}
