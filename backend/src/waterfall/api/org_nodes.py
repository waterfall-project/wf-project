# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the organisation (FBS-3.2).

``listOrgNodes``, ``createOrgNode``, ``updateOrgNode`` and ``setOrgNodeActivation``.

Registered by the application, empty until US-0840 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
