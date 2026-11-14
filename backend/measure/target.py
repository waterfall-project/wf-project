# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the measure runs on: the database of the service platform, and the structure it reads."""

import importlib
import os
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.engine import URL

from waterfall.core.planning.interface import Place
from waterfall.platform.database import Database, create_database_engine

if TYPE_CHECKING:
    from uuid import UUID

# The service imports its modules in the order of its application, which registers the facets of
# the nodes and the copies of a revision; the core read alone would not have them.
importlib.import_module("waterfall.api.app")

PROJECT_CODE = "PRJ-001"
"""The project of the witness the measure reads: the one of the volumes of §4.6.2."""

_ROLE = "waterfall_service"
_HOST = "127.0.0.1"
_DEFAULT_PORT = 5432

_STRUCTURE = text(
    "SELECT project.id, project.current_revision_id, structure.id, revision.lock_version "
    "FROM project "
    "JOIN revision ON revision.id = project.current_revision_id "
    "JOIN cost_structure AS structure ON structure.project_id = project.id "
    "AND structure.revision_id = revision.id AND structure.kind = 'main' "
    "WHERE project.code = :code"
)
_MANAGER = text(
    "SELECT user_account_id FROM contributor "
    "WHERE project_id = :project AND kind = 'project_manager' ORDER BY user_account_id LIMIT 1"
)


class MeasureError(Exception):
    """The platform is not what the measure needs: it says what to start."""


@dataclass(frozen=True, slots=True)
class Target:
    """The structure measured, the revision it belongs to, and who manages its project.

    Read from the database at each passage: the identifiers of a loading of the witness are its
    own, and none is written here.
    """

    place: Place
    revision_lock_version: int
    manager_id: UUID


def address_from_environment() -> str:
    """Give the address of the database of the service platform of the slot, from the environment.

    The port is the slot's (``WATERFALL_POSTGRES_PORT``, given by the Makefile), the password that
    of the role of the service, which the platform takes from the same environment.
    """
    password = os.environ.get("WATERFALL_SERVICE_DATABASE_PASSWORD")
    if not password:
        message = "WATERFALL_SERVICE_DATABASE_PASSWORD is not set: the guide, 'Commandes'"
        raise MeasureError(message)
    port = int(os.environ.get("WATERFALL_POSTGRES_PORT", _DEFAULT_PORT))
    url = URL.create(
        "postgresql", username=_ROLE, password=password, host=_HOST, port=port, database="waterfall"
    )
    return url.render_as_string(hide_password=False)


@cache
def database_of(address: str) -> Database:
    """Give the database of a process, opened once: its connections warm, as the service's are."""
    return Database(create_database_engine(address))


def locate(database: Database) -> Target:
    """Read from the database the structure of the current revision of the project measured."""
    with database.transaction() as session:
        found = session.execute(_STRUCTURE, {"code": PROJECT_CODE}).one_or_none()
        if found is None:
            message = (
                f"{PROJECT_CODE} has no current revision with a structure: start the platform "
                "and load the witness (make service-up, make service-install, make service-witness)"
            )
            raise MeasureError(message)
        project_id, revision_id, structure_id, lock_version = found
        manager = session.execute(_MANAGER, {"project": project_id}).scalar_one_or_none()
    if manager is None:
        message = f"{PROJECT_CODE} has no project manager"
        raise MeasureError(message)
    return Target(Place(project_id, revision_id, structure_id), lock_version, manager)
