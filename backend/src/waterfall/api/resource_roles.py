# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources (FBS-3.2).

``listResourceRoles``, ``createResourceRole``, ``updateResourceRole`` and
``setResourceRoleActivation``.

Registered by the application, empty until US-0850 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
