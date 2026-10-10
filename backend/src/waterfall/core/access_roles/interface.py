# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the roles offer to the other modules and to the API.

The catalogue, delivered and not modifiable (WF-ADM-0100), and the roles, read as the table of
the roles shows them, filtered and sorted (WF-ADM-0090, WF-IHM-0060). Their writes and the guard
of the last administrator (WF-ADM-0120) arrive with the next lot of US-0380; the effective
permissions of an account and the evaluation of an action with US-0390.
"""

from waterfall.core.access_roles.roles import (
    CataloguePermission,
    RoleFilters,
    RoleSort,
    RoleView,
    SortColumn,
    list_permissions,
    list_roles,
    read_role,
)

__all__ = [
    "CataloguePermission",
    "RoleFilters",
    "RoleSort",
    "RoleView",
    "SortColumn",
    "list_permissions",
    "list_roles",
    "read_role",
]
