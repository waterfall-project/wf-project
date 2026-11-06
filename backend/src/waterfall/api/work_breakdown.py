# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work breakdown of a project (WF-PRJ-0020).

``getWorkBreakdown`` and ``setWorkBreakdown``.

Registered by the application, empty until US-0950 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["projects"])
