# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of an amendment into the main structure (WF-REV-0050).

``getStructureMergeReport`` (US-2560/L1), the report before the merge, and ``mergeCostStructure``
(US-2560/L2), the merge confirmed and handed to the worker, under ``structure_merge``.

Registered by the application, empty until US-2560 serves it (US-2550/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
