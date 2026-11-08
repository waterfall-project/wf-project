# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of the rates of a revision to those of the reference (WF-REV-0060).

``getRateUpdateProposal`` and ``applyRateUpdate`` (US-1500).

Registered by the application, empty until US-1500 serves them (US-1490/L1).
"""

from fastapi import APIRouter

router = APIRouter(tags=["revisions"])
