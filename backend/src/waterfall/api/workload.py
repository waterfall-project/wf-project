# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of a project: the hours of its lines by role and by period.

``getProjectWorkload`` (US-1520).

Registered by the application, empty until US-1520 serves it (US-1490/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["estimate"])
