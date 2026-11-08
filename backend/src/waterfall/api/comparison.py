# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (WF-REV-0080).

``compareRevisions`` (US-1530).

Registered by the application, empty until US-1530 serves it (US-1490/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
