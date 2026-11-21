# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The external locations of the backups (WF-ADM-0170): ``listExternalBackupLocations``, their test.

The locations are those the installation declares in a file its deployment mounts
(``ExternalLocations``, US-2910/L3), read at the start of the process: their name, their nature
and their description are served, never what reaches them — an address, a key, a secret
(`ExternalBackupLocation`). Listed under the permission to read the backups; tested under the one
to change them besides (WF-ADM-0100). A test writes then erases a witness file, at the root of the
location or in the folder given, and says its outcome, a refusal by its reason
(``ExternalBackupFailure``); it waits thirty seconds at most, and holds no connection to the
database meanwhile. A location the installation does not declare does not exist (404).
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from waterfall.api.authentication import ServicesOf
from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import ExternalBackupLocation, ExternalBackupLocationTest
from waterfall.api.evaluation import Requires
from waterfall.core.backups.interface import path_faults
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    NOT_FOUND,
    VALIDATION_FAILED,
    FieldError,
    NotFoundError,
    UnprocessableError,
)
from waterfall.platform.external_locations import try_location

router = APIRouter(tags=["platform"])

READ = [Depends(Requires("backups.read"))]
TEST = [Depends(Requires("backups.read", "backups.write"))]


class LocationTestWrite(ContractModel):
    """``ExternalBackupLocationTestRequest`` as a test sends it: the folder unjudged, or none."""

    path: str | None = None


@router.get(
    "/external-backup-locations",
    operation_id="listExternalBackupLocations",
    dependencies=READ,
)
def get_external_backup_locations(services: ServicesOf) -> list[ExternalBackupLocation]:
    """Give the locations the installation declares, by their names: nothing that reaches them."""
    return [
        ExternalBackupLocation.model_validate(
            {"name": name, "kind": location.kind, "description": location.description}
        )
        for name, location in services.external_locations.declared()
    ]


@router.post(
    "/external-backup-locations/{location_name}/test",
    operation_id="testExternalBackupLocation",
    dependencies=TEST,
)
def post_external_backup_location_test(
    location_name: str,
    services: ServicesOf,
    body: Annotated[LocationTestWrite | None, Body()] = None,
) -> ExternalBackupLocationTest:
    """Write then erase a witness file in a location, and say how it went.

    A location not declared is not found (404); a folder that is not relative, or that leaves the
    location, is refused (422), as one sent null, before anything is written.
    """
    location = services.external_locations.get(location_name)
    if location is None:
        raise NotFoundError(NOT_FOUND)
    path = None if body is None else body.path
    if body is not None and "path" in body.model_fields_set and path is None:
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError("/path", VALIDATION_FAILED),)
        )
    if path is not None and (faults := path_faults("/path", path)):
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    tested_at = utc_now()
    failure = try_location(location, path or "")
    return ExternalBackupLocationTest.model_validate(
        {"location": location_name, "path": path, "tested_at": tested_at, "failure": failure}
    )
