# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The minimal reference a project needs (WF-CYC-0120).

``getReferenceReadiness``: the four questions the cost and the resource settings answer,
in the order of the enumeration.

Registered by the application, empty until US-0810/L2 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
