# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings the installation shares (FBS-3.1, FBS-3.3, FBS-3.4).

``getReferenceSettings`` and ``updateReferenceSettings``, each field written under the
permission of its function (WF-ADM-0100).

Registered by the application, empty until US-0810/L2 serves them.
"""

from fastapi import APIRouter

router = APIRouter(tags=["reference"])
