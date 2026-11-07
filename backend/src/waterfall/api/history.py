# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The history that can be undone, and the paste of a block (WF-IHM-0110, 0050).

``undoLastChange``, ``redoLastUndo``, ``previewPaste`` and ``applyPaste`` (US-1450/L2).

Registered by the application, empty until US-1450 serves them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
