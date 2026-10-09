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
    """Start the API service, or say why it cannot start (WF-SEC-0010).

    The service takes no argument but ``--version``: any other one is refused with status 2.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if arguments:
        sys.stderr.write(
            f"usage: {NAME} [--version]\n{NAME}: unexpected argument: {arguments[0]}\n"
        )
        return 2
    try:
        settings = load_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    get_logger(__name__).info(
        "service.starting", version=__version__, host=settings.host, port=settings.port
    )
    uvicorn.run(
        create_app(), host=settings.host, port=settings.port, log_config=None, access_log=False
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
