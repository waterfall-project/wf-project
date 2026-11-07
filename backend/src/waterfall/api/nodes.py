# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the tasks of a structure (WF-PLA-0040, 0050, 0070, 0150, 0170).

``listNodes``, ``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies`` and
``resolveRowNumber`` (US-1380/L2); ``deleteNode`` and ``moveNodes`` (US-1380/L3).

Registered by the application, empty until US-1380 serves them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
