# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the roles offer to the other modules and to the API.

The catalogue, delivered and not modifiable (WF-ADM-0100); the roles, composed, read, changed and
deleted (WF-ADM-0090); the roles an account holds, its effective permissions and the evaluation
of an action against them (WF-ADM-0110); the description of the three predefined roles, for the
bootstrap (WF-ADM-0010); and the guard of the last administrator, which every write that may take
the administration from an account runs under (WF-ADM-0120).
"""

from waterfall.core.access_roles.administrators import (
    LAST_ADMINISTRATOR,
    guard_last_administrator,
)
from waterfall.core.access_roles.evaluation import (
    PERMISSION_MISSING,
    Actor,
    actor_of,
    effective_permissions,
    granted_permissions,
    require,
)
from waterfall.core.access_roles.predefined import PredefinedRole, predefined_roles
from waterfall.core.access_roles.roles import (
    ACCESS_ROLE_IN_USE,
    Act,
    CataloguePermission,
    HeldRole,
    RoleFilters,
    RoleSort,
    RoleView,
    RoleWrite,
    SortColumn,
    create_role,
    delete_role,
    list_permissions,
    list_roles,
    read_role,
    roles_held,
    update_role,
)

__all__ = [
    "ACCESS_ROLE_IN_USE",
    "LAST_ADMINISTRATOR",
    "PERMISSION_MISSING",
    "Act",
    "Actor",
    "CataloguePermission",
    "HeldRole",
    "PredefinedRole",
    "RoleFilters",
    "RoleSort",
    "RoleView",
    "RoleWrite",
    "SortColumn",
    "actor_of",
    "create_role",
    "delete_role",
    "effective_permissions",
    "granted_permissions",
    "guard_last_administrator",
    "list_permissions",
    "list_roles",
    "predefined_roles",
    "read_role",
    "require",
    "roles_held",
    "update_role",
]
