# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of a project and their structures (FBS-4.1).

``listRevisions``, ``createRevision``, ``getRevision``, ``abandonRevision`` and
``listCostStructures`` (US-0960); ``markRevision``, which submits its task (US-0970).

Registered by the application, empty until US-0960 and US-0970 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
