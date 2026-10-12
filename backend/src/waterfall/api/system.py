# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the system family of the contract: the probes, and the installation."""

from fastapi import APIRouter

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.contract.models import Installation
from waterfall.api.maintenance import in_maintenance
from waterfall.platform.installation import read_settings

router = APIRouter(tags=["system"])


@router.get("/health", operation_id="getLiveness")
def get_liveness(services: ServicesOf) -> dict[str, str]:
    """Answer as soon as the process is up, touching no component of data; say a maintenance.

    A restoration that holds the platform in maintenance is said, and its end, which the front
    waits for (#604): the process is alive all the same.
    """
    return {"status": "maintenance" if in_maintenance(services.maintenance) else "ok"}


@router.get("/installation", operation_id="getInstallation")
def get_installation(session: Transaction) -> Installation:
    """Give what the front must know of the installation before any session, to anybody.

    Its language by default, which the front falls back on (WF-INTF-0160), and the bounds of what
    it lets pass; refused while the installation is not bootstrapped (503).
    """
    settings = read_settings(session)
    return Installation.model_validate(
        {
            "default_language": settings.default_language,
            "avatar_max_bytes": settings.avatar_max_bytes,
            "external_backup_max_bytes": settings.external_backup_max_bytes,
        }
    )
