# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Apply the migrations: the command ``waterfall-migrate`` and what tests call."""

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

from waterfall import __version__
from waterfall.platform.settings import SettingsError, load_settings

NAME = "waterfall-migrate"


def alembic_config(engine: Engine | None = None) -> Config:
    """Build the configuration of Alembic, on the engine given or else on the settings."""
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent))
    if engine is not None:
        config.attributes["engine"] = engine
    return config


def upgrade(engine: Engine | None = None, revision: str = "head") -> None:
    """Apply the migrations that are not applied yet, up to ``revision``."""
    command.upgrade(alembic_config(engine), revision)


def downgrade(engine: Engine, revision: str) -> None:
    """Undo migrations down to ``revision``: for the tests and a development database.

    Never for an installation, whose rollback concerns the code and never the schema (the
    specification, 4.5.3): ``waterfall-migrate`` only goes up.
    """
    command.downgrade(alembic_config(engine), revision)


def main(argv: Sequence[str] | None = None) -> int:
    """Apply every pending migration to the database of the settings, or say why it cannot."""
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
        load_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    upgrade()
    return 0


if __name__ == "__main__":
    sys.exit(main())
