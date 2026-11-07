# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports in two steps (WF-INTF-0080, WF-INTF-0090).

``uploadFile``, ``openImport``, ``getImport``, ``listImports``, ``abandonImport`` and
``applyImport`` (US-1420/L1).

Registered by the application, empty until US-1420 serves them (US-1380/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["exchanges"])
