# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An archive restored on a fresh platform, before it starts (US-2950, #4114).

The reference set is engendered once per version, backed up, and its archive kept out of the
platform; a platform that needs it restores it instead of engendering it again. It is restored as
the test of a restoration restores a backup on its ephemeral platform (``waterfall.restore.trial``,
US-2930): the archive read, its manifest and each dump checked (``extracted``), the two databases
replaced by the dumps, as their owners, and Waterfall's migrated to the revision of the
installation, before Keycloak, the API and the worker start on them. No backup of the list is
named, no task is run, and nothing is inscribed: the platform is made from the archive, it is not
restored by an account (WF-ADM-0160 is not asked of it).

Unlike the ephemeral platform, this one lives on: what a restoration writes back is written back
(``keep_for_restoration``, ``write_back_after_restoration``). Its database, freshly migrated, gives
the rights of its role of the service, its schedule of the backups as shipped, and no backup, no
deposit, no inscription; the tasks the archive caught queued or running — the backup that took it
among them — fail (#892), so that the worker of the platform does not run them again, and the
backups and deposits of the source, whose objects are not in this platform's bucket, are not listed.

A platform is fresh while the database of its identity provider holds no table: Keycloak has never
started on it, and starts on the database restored. One that has is refused before anything
changes: its caches would serve the realm it held.
"""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import inspect

from waterfall.core.backups.interface import keep_for_restoration, write_back_after_restoration
from waterfall.platform.database import create_database_engine, utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import get_logger
from waterfall.worker.backup import DATABASES
from waterfall.worker.restore import extracted, replace

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sqlalchemy import Engine

logger = get_logger(__name__)


class NotFreshError(RuntimeError):
    """The platform is not fresh: its identity provider has started on it."""


def is_fresh(provider: str) -> bool:
    """Tell whether the database of the identity provider at ``provider`` holds no table."""
    engine = create_database_engine(provider)
    try:
        with engine.connect() as connection:
            return not inspect(connection).get_table_names()
    finally:
        engine.dispose()


def restore_fresh(
    archive: Path, databases: Mapping[str, str], migrate: Callable[[Engine], None]
) -> None:
    """Restore ``archive`` into the ``databases`` of a fresh platform, as their owners.

    An archive that does not read back whole, or of a newer version, is refused (422) and a
    platform that is not fresh (``NotFreshError``), each before any database is touched.
    """
    if not is_fresh(databases["identity_provider"]):
        message = "the identity provider has started on this platform: it is not fresh"
        raise NotFreshError(message)
    restoration = new_id()
    with tempfile.TemporaryDirectory(prefix="waterfall-restore-fresh-") as work:
        folder = Path(work)
        dumps = extracted(archive, folder)
        owner = create_database_engine(databases["waterfall"])
        try:
            with owner.begin() as connection:
                keep_for_restoration(connection, restoration)
            for name in DATABASES:
                replace(name, dumps[name], databases[name], folder)
            migrate(owner)
            with owner.begin() as connection:
                subjects = write_back_after_restoration(connection, restoration, utc_now())
        finally:
            owner.dispose()
    # A fresh platform has anonymised no account since the archive: its journal kept is empty, and
    # the archive's own holds none named. One would be removed from the realm by a restoration;
    # here Keycloak has not started, and the log says it.
    if subjects:
        logger.warning("restore.fresh_accounts_anonymised_again", count=len(subjects))
    logger.info("restore.fresh_done")
