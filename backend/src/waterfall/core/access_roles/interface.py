# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the roles offer to the other modules and to the API.

The catalogue, delivered and not modifiable (WF-ADM-0100); the roles, composed, read, changed and
deleted (WF-ADM-0090); the roles an account holds, its effective permissions and the evaluation
of an action against them (WF-ADM-0110); the first roles of an account created, and the roles of
an account set, under the guard (``attributions``); the description of the three predefined roles,
for the bootstrap (WF-ADM-0010); the guard of the last administrator, which every write that may
take the administration from an account runs under, the deactivation of an account by its own
refusal, that account read, and the lock of the rule, which a write takes before any of the rows it
locks (WF-ADM-0120); and what the table of the accounts filters and sorts
of the roles each one holds (``listUsers``).
"""

from waterfall.core.access_roles.administrators import (
    LAST_ADMINISTRATOR,
    guard_deactivation,
    guard_last_administrator,
    lock_administrators,
    sole_administrator,
)
from waterfall.core.access_roles.attributions import (
    UNKNOWN_ACCESS_ROLE,
    Attribution,
    give_first_roles,
    set_access_roles,
    unknown_roles,
)
from waterfall.core.access_roles.evaluation import (
    PERMISSION_MISSING,
    Actor,
    Holding,
    actor_of,
    effective_permissions,
    holding,
    require,
)
from waterfall.core.access_roles.predefined import PredefinedRole, predefined_roles
from waterfall.core.access_roles.roles import (
    ACCESS_ROLE_IN_USE,
    CataloguePermission,
    HeldRole,
    RoleFilters,
    RoleSort,
    RoleView,
    RoleWrite,
    SortColumn,
    create_role,
    delete_role,
    holding_one_of,
    labels_held,
    list_permissions,
    list_roles,
    read_role,
    roles_held,
    roles_held_by,
    update_role,
)
from waterfall.platform.audit import Act

__all__ = [
    "ACCESS_ROLE_IN_USE",
    "LAST_ADMINISTRATOR",
    "PERMISSION_MISSING",
    "UNKNOWN_ACCESS_ROLE",
    "Act",
    "Actor",
    "Attribution",
    "CataloguePermission",
    "HeldRole",
    "Holding",
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
    "give_first_roles",
    "guard_deactivation",
    "guard_last_administrator",
    "holding",
    "holding_one_of",
    "labels_held",
    "list_permissions",
    "list_roles",
    "lock_administrators",
    "predefined_roles",
    "read_role",
    "require",
    "roles_held",
    "roles_held_by",
    "set_access_roles",
    "sole_administrator",
    "unknown_roles",
    "update_role",
]
