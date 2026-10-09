# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of the API service.

It serves the operations of the contract and nothing else: no documentation page, no
``openapi.json`` — the contract is written by hand and is the only description of the
interface (WF-ARC-0060).
"""

from fastapi import FastAPI

from waterfall import __version__
from waterfall.api import system
from waterfall.api.middleware import CorrelationMiddleware
from waterfall.api.problems import install_problem_handlers

# The single prefix of version the contract declares in its ``servers``.
PREFIX = "/api/v1"


def create_app() -> FastAPI:
    """Build the application: its routes, its correlation, its envelope of errors."""
    app = FastAPI(
        title="Waterfall API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(CorrelationMiddleware)
    install_problem_handlers(app)
    app.include_router(system.router, prefix=PREFIX)
    return app
