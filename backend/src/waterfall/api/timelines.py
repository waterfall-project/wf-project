# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The named timelines of a project and the inscriptions of its tasks (WF-PLA-0140).

``listTimelines``, ``createTimeline`` and ``deleteTimeline`` (US-1400/L1);
``setNodeTracking`` (US-1400/L2).

Registered by the application, empty until US-1400 serves them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["planning"])
