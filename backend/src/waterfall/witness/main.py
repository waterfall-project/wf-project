# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``waterfall-api load-witness``: the witness of the reference loaded on a platform (EP-05).

It reads ``WATERFALL_DATABASE_URL``, the role of the service, and ``WATERFALL_WITNESS_PATH``, the
directory of the description; a setting that lacks, or a path that is no directory, stops it at
start, named (2). Then, in one transaction, under an advisory lock of its own that keeps two
loadings apart, each slice in its order (``loader``), every identifier the witness does not impose
drawn in order (``drawn_in_order``), so that two loadings give the same ones: a failure — a file
that strays from the contract, an identifier already held — writes nothing and ends it (1), said in
the structured logs. Run again on a platform that holds the witness, it writes nothing and succeeds,
saying so.

The command ``waterfall-api`` starts here: ``load-witness`` loads, ``load-reference`` loads the
witness then the reference set (``reference_load``, US-2950), ``check-reference`` checks it
(``reference_check``), ``backup-reference`` keeps it as a backup and ``restore-reference`` restores
it on a fresh platform (``reference_archive``), anything else is the bootstrap's,
which passes on to the API what is not its own.
"""

import sys
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall import bootstrap, schema
from waterfall.api import main as api
from waterfall.platform.audit import Act
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import ServiceError
from waterfall.platform.identifiers import drawn_in_order
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.settings import SettingsError, WitnessSettings, load_witness_settings
from waterfall.witness import reference_archive, reference_check, reference_load
from waterfall.witness.description import Witness
from waterfall.witness.loader import load_slices

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

COMMAND = "load-witness"
# The key of the advisory lock of the transaction that loads the witness.
WITNESS_LOCK = 4_200_810
# The instant the identifiers the loader draws bear: the installation of the witness, before any
# identifier the service draws afterwards (US-2650/L1).
DRAWN_AT = datetime(2025, 9, 1, 9, 0, tzinfo=UTC)

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Load the witness, or the reference set, if asked to; else, run the bootstrap's command."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    commands: dict[str, Callable[[list[str]], int]] = {
        reference_load.COMMAND: lambda rest: reference_load.main(rest, lambda: main([COMMAND])),
        reference_check.COMMAND: reference_check.main,
        reference_archive.BACKUP: partial(reference_archive.main, reference_archive.BACKUP),
        reference_archive.RESTORE: partial(reference_archive.main, reference_archive.RESTORE),
    }
    if arguments and arguments[0] in commands:
        return commands[arguments[0]](arguments[1:])
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
        with (
            TIME_ZONE.reading_from(stored_in(database)),
            logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM),
        ):
            return _load(database, Path(settings.witness_path))
    finally:
        database.dispose()


def _load(database: Database, directory: Path) -> int:
    try:
        with database.transaction() as session:
            session.execute(select(func.pg_advisory_xact_lock(WITNESS_LOCK)))
            with drawn_in_order(DRAWN_AT):
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
