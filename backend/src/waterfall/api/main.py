# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the API service."""

import sys
from collections.abc import Sequence

import uvicorn

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.platform.logs import configure_logging, get_logger
from waterfall.platform.settings import SettingsError, load_settings

NAME = "waterfall-api"


def main(argv: Sequence[str] | None = None) -> int:
    """Start the API service, or say why it cannot start (WF-SEC-0010)."""
    if list(sys.argv[1:] if argv is None else argv) == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    try:
        settings = load_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level)
    get_logger(__name__).info(
        "service.starting", version=__version__, host=settings.host, port=settings.port
    )
    uvicorn.run(
        create_app(), host=settings.host, port=settings.port, log_config=None, access_log=False
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
