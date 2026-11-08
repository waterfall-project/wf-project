# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line of an estimate changed (WF-DEV-0020, WF-IHM-0110).

``updateEstimateLine`` (US-1490/L3); the creation, the deletion, the move and the reading of a line
stay with the routers of the planning, which ask the facet of its kind.

Registered by the application, empty until US-1490 serves it (US-1490/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["estimate"])
