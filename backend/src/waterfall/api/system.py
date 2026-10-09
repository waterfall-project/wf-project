# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The probes of the system family of the contract."""

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health", operation_id="getLiveness")
def get_liveness() -> dict[str, str]:
    """Answer as soon as the process is up, touching no component of data."""
    return {"status": "ok"}
