# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amendments of a revision: a differential opened, abandoned (WF-REV-0100).

``createCostStructure`` (US-2550/L3), a differential opened as the copy of the main structure, and
``deleteCostStructure`` (US-2550/L4), a differential abandoned, under the command
``create_structure`` of the revision.

Registered by the application, empty until US-2550 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
