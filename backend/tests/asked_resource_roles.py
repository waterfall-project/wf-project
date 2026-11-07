# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/resource_roles.py`` ask for: the roles of resources.

``test_access_evaluation.py`` gathers them; US-0850 declares each operation it serves.
"""

CHANGE = "resource_settings.write"

# The permissions each operation asks for, in the order they are evaluated: the active roles are
# read by any open session (WF-DEV-0020, #1745), every write asks for the permission to change the
# resource settings.
ASKED: dict[str, tuple[str, ...]] = {
    "listResourceRoles": (),
    "createResourceRole": (CHANGE,),
    "updateResourceRole": (CHANGE,),
    "setResourceRoleActivation": (CHANGE,),
}
# The permission a list asks for besides when it asks for deactivated objects: the permission to
# change the part, as the contract plays it (``*_inactive_forbidden``; the decision of #2084).
INACTIVE: dict[str, str] = {"listResourceRoles": CHANGE}
