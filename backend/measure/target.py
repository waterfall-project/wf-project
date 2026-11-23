# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the measure runs on: the database of the service platform, and the structure it reads."""

import importlib
import os
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, get_args
from uuid import uuid4

from redis import Redis
from sqlalchemy.engine import URL

from waterfall.core.planning.interface import Place
from waterfall.core.projects.interface import (
    ContributorFilters,
    ContributorSort,
    ProjectFilters,
    ProjectPage,
    ProjectSort,
    ProjectState,
    Viewer,
    list_contributors,
    list_projects,
)
from waterfall.core.revisions.interface import MAIN, list_cost_structures, read_revision
from waterfall.platform.cache import IndicatorsCache
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.permissions import ALL_PROJECTS_READ

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
_REDIS_PORT = 6379
_CACHE_TTL = 600
_CACHE_TIMEOUT = 1.0

_ALL_STATES = frozenset(get_args(ProjectState.__value__))
_PAGE = ProjectPage(limit=50, offset=0)


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
    raw_port = os.environ.get("WATERFALL_POSTGRES_PORT", str(_DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError:
        message = f"WATERFALL_POSTGRES_PORT is not a port number: {raw_port!r}"
        raise MeasureError(message) from None
    url = URL.create(
        "postgresql", username=_ROLE, password=password, host=_HOST, port=port, database="waterfall"
    )
    return url.render_as_string(hide_password=False)


def cache_from_environment() -> IndicatorsCache:
    """Give the cache of the indicators, in the Redis of the slot's platform, from the environment.

    The port is the slot's (``WATERFALL_REDIS_PORT``), the password that of the platform
    (``WATERFALL_REDIS_PASSWORD``); the cache is the service's own class, with a delay of a second.
    """
    password = os.environ.get("WATERFALL_REDIS_PASSWORD")
    if not password:
        message = "WATERFALL_REDIS_PASSWORD is not set: the guide, 'Commandes'"
        raise MeasureError(message)
    raw_port = os.environ.get("WATERFALL_REDIS_PORT", str(_REDIS_PORT))
    try:
        port = int(raw_port)
    except ValueError:
        message = f"WATERFALL_REDIS_PORT is not a port number: {raw_port!r}"
        raise MeasureError(message) from None
    client = Redis(
        host=_HOST,
        port=port,
        password=password,
        socket_timeout=_CACHE_TIMEOUT,
        socket_connect_timeout=_CACHE_TIMEOUT,
    )
    return IndicatorsCache(client, _CACHE_TTL)


@cache
def database_of(address: str) -> Database:
    """Give the database of a process, opened once: its connections warm, as the service's are."""
    return Database(create_database_engine(address))


def locate(database: Database) -> Target:
    """Read from the database the structure of the current revision of the project measured."""
    with database.transaction() as session:
        # The one place a viewer is made out of nothing: before the manager is known, the project
        # is listed by one that sees them all (the interface of the projects takes no other way).
        everything = Viewer(uuid4(), (ALL_PROJECTS_READ,))
        found = list_projects(
            session,
            everything,
            ProjectFilters(search=PROJECT_CODE, states=_ALL_STATES),
            ProjectSort(),
            _PAGE,
        )
        project = next((each for each in found.projects if each.code == PROJECT_CODE), None)
        if project is None or project.current_revision_id is None:
            message = (
                f"{PROJECT_CODE} has no current revision: start the platform and load the "
                "witness (make service-up, make service-install, make service-witness)"
            )
            raise MeasureError(message)
        project_id, revision_id = project.project_id, project.current_revision_id
        managers = list_contributors(
            session,
            project_id,
            ContributorFilters(kinds=frozenset({"project_manager"})),
            ContributorSort(),
        ).items
        if not managers:
            message = f"{PROJECT_CODE} has no project manager"
            raise MeasureError(message)
        manager = managers[0].user_id
        structure = next(
            (
                each
                for each in list_cost_structures(
                    session, project_id, revision_id, Viewer(manager, ())
                )
                if each.kind == MAIN
            ),
            None,
        )
        if structure is None:
            message = f"{PROJECT_CODE} has no main structure in its current revision"
            raise MeasureError(message)
        lock_version = read_revision(
            session, project_id, revision_id, Viewer(manager, ())
        ).lock_version
    return Target(Place(project_id, revision_id, structure.structure_id), lock_version, manager)
