# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``waterfall-api load-witness``: the witness of the reference loaded on a platform (EP-05).

It reads ``WATERFALL_DATABASE_URL``, the role of the service, and ``WATERFALL_WITNESS_PATH``, the
directory of the description; a setting that lacks, or a path that is no directory, stops it at
start, named (2). Then, in one transaction, under an advisory lock of its own that keeps two
loadings apart, each slice in its order (``loader``): a failure — a file that strays from the
contract, an identifier already held — writes nothing and ends it (1), said in the structured logs.
Run again on a platform that holds the witness, it writes nothing and succeeds, saying so.

The command ``waterfall-api`` starts here: ``load-witness`` loads, anything else is the
bootstrap's, which passes on to the API what is not its own.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall import bootstrap, schema
from waterfall.api import main as api
from waterfall.platform.audit import Act
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import ServiceError
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.settings import SettingsError, WitnessSettings, load_witness_settings
from waterfall.witness.description import Witness
from waterfall.witness.loader import load_slices

if TYPE_CHECKING:
    from collections.abc import Sequence

COMMAND = "load-witness"
# The key of the advisory lock of the transaction that loads the witness.
WITNESS_LOCK = 4_200_810

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Load the witness if asked to, ``load-witness``; else, run the bootstrap's command."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != [COMMAND]:
        return bootstrap.main(arguments)
    try:
        settings = load_witness_settings()
    except SettingsError as error:
        sys.stderr.write(f"{api.NAME} {COMMAND}: {error}\n")
        return 2
    if not Path(settings.witness_path).is_dir():
        sys.stderr.write(f"{api.NAME} {COMMAND}: WATERFALL_WITNESS_PATH: is not a directory\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    return load_witness(settings)


def load_witness(settings: WitnessSettings) -> int:
    """Load the witness the settings designate on their database; give the status of the command.

    Under a correlation of its own, as the platform.
    """
    schema.declared()
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            return _load(database, Path(settings.witness_path))
    finally:
        database.dispose()


def _load(database: Database, directory: Path) -> int:
    try:
        with database.transaction() as session:
            session.execute(select(func.pg_advisory_xact_lock(WITNESS_LOCK)))
            written = load_slices(session, Witness(directory, Act(None, utc_now())))
    except ServiceError as refused:
        # A rule of a module refused an object of the witness: a state to correct, not a trace.
        refusal = (refused.code, dict(refused.params))
    except Exception:
        logger.exception("witness.failed")
        return 1
    else:
        if written:
            logger.info("witness.loaded", slices=written)
        else:
            logger.info("witness.already_loaded")
        return 0
    logger.error("witness.refused", code=refusal[0], params=refusal[1])
    return 1
