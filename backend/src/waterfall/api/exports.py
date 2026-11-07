# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports, and the file a background task produced (WF-INTF-0050, WF-PLA-0120).

``requestExport`` and ``getBackgroundTaskResult`` (US-1430/L2); the image of the tree
(US-1440/L2).

Registered by the application, empty until US-1430 and US-1440 serve them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["exchanges"])
