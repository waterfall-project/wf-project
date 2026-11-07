# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of the API service.

It serves the operations of the contract and nothing else: no documentation page, no
``openapi.json`` — the contract is written by hand and is the only description of the
interface (WF-ARC-0060). A path with a slash the contract does not write is not redirected.
"""

from typing import TYPE_CHECKING

from fastapi import FastAPI

from waterfall import __version__, schema
from waterfall.api import (
    access_roles,
    actual_cost_mapping,
    audit,
    avatars,
    backups,
    calendars,
    contributors,
    cost_types,
    exports,
    history,
    hourly_rates,
    identity_syncs,
    imports,
    lifecycle,
    me,
    nodes,
    org_nodes,
    progress,
    projects,
    reference,
    reference_settings,
    resource_roles,
    restores,
    revisions,
    scheduling,
    skeleton,
    subprojects,
    system,
    tasks,
    timelines,
    uploads,
    users,
    work_breakdown,
)
from waterfall.api.maintenance import MaintenanceMiddleware
from waterfall.api.middleware import CorrelationMiddleware
from waterfall.api.problems import install_problem_handlers
from waterfall.core.exchanges import interface as exchanges_interface
from waterfall.core.history import interface as history_interface
from waterfall.core.planning import interface as planning_interface

if TYPE_CHECKING:
    from waterfall.api.authentication import Services

# The single prefix of version the contract declares in its ``servers``.
PREFIX = "/api/v1"
# The modules that fill the registries of the others at the import of their interface (#2180):
# imported here whether or not a route reads them yet, so that no revision is copied, closed or
# designated, and no reference changed, without their part.
EXTENDING = (exchanges_interface, history_interface, planning_interface)


def create_app(services: Services) -> FastAPI:
    """Build the application on its services: its routes, its correlation, its envelope of errors.

    Nothing is reached before a request needs it: a probe answers without the database or
    Keycloak.
    """
    schema.declared()
    app = FastAPI(
        title="Waterfall API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )
    # Added first, run second: a refusal in maintenance carries the correlation of its request.
    app.add_middleware(MaintenanceMiddleware, maintenance=services.maintenance)
    app.add_middleware(CorrelationMiddleware)
    install_problem_handlers(app)
    app.state.services = services
    app.include_router(system.router, prefix=PREFIX)
    app.include_router(me.router, prefix=PREFIX)
    app.include_router(avatars.router, prefix=PREFIX)
    app.include_router(users.router, prefix=PREFIX)
    app.include_router(identity_syncs.router, prefix=PREFIX)
    app.include_router(access_roles.router, prefix=PREFIX)
    app.include_router(tasks.router, prefix=PREFIX)
    app.include_router(audit.router, prefix=PREFIX)
    app.include_router(backups.router, prefix=PREFIX)
    app.include_router(restores.router, prefix=PREFIX)
    app.include_router(uploads.router, prefix=PREFIX)
    # The reference (EP-05): a router per story, each registered here from the start.
    for reference_router in (
        reference.router,
        reference_settings.router,
        cost_types.router,
        hourly_rates.router,
        org_nodes.router,
        resource_roles.router,
        calendars.router,
        actual_cost_mapping.router,
    ):
        app.include_router(reference_router, prefix=PREFIX)
    # The projects and their revisions (EP-04): a router per story, each registered here from the
    # start.
    for project_router in (
        projects.router,
        contributors.router,
        subprojects.router,
        work_breakdown.router,
        revisions.router,
        lifecycle.router,
    ):
        app.include_router(project_router, prefix=PREFIX)
    # The planning, its imports and its exports (EP-06): a router per story, each registered here
    # from the start.
    for planning_router in (
        nodes.router,
        scheduling.router,
        timelines.router,
        progress.router,
        imports.router,
        exports.router,
        history.router,
        skeleton.router,
    ):
        app.include_router(planning_router, prefix=PREFIX)
    return app
