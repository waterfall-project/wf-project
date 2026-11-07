# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of a task (WF-PLA-0130).

``setTaskProgress`` (US-1410).

Registered by the application, empty until US-1410 serves them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
