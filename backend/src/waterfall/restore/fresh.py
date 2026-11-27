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
deposit, no inscription; the backups and deposits of the source, whose objects are not in this
platform's bucket, are not listed. The tasks of a backup the archive caught queued or running — the
backup that took it among them — are forgotten, as those that ended: the platform has scheduled no
backup, and does not say its latest one failed (``last_scheduled_outcome``); the other tasks caught
pending fail (#892), so that the worker of the platform does not run them again.

A platform is fresh while the database of its identity provider holds no table — Keycloak has never
started on it, and starts on the database restored; its caches would serve the realm it held — and
Waterfall's holds nothing its migrations did not write: no inscription, no backup, no deposit, no
task, which the restoration would write back into the set. One that is not is refused before
anything changes.
"""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import inspect

from waterfall.core.backups.interface import (
    holds_what_a_restoration_keeps,
    keep_for_restoration,
    write_back_after_restoration,
)
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
    """The platform is not fresh: its identity provider has started on it, or Waterfall has run."""


def not_fresh(databases: Mapping[str, str]) -> str | None:
    """Say what makes the platform of ``databases`` not fresh; ``None`` if it is.

    The database of the identity provider holds a table, or Waterfall's a row its migrations alone
    do not write (``holds_what_a_restoration_keeps``).

    A check of the operator, not a lock: nothing prevents Keycloak or a worker from starting on the
    platform between this reading and the replacement of the databases. The operator restores before
    he starts them, and does not start them meanwhile.
    """
    provider = create_database_engine(databases["identity_provider"])
    try:
        with provider.connect() as connection:
            if inspect(connection).get_table_names():
                return "the identity provider has started on this platform"
    finally:
        provider.dispose()
    waterfall = create_database_engine(databases["waterfall"])
    try:
        with waterfall.connect() as connection:
            if holds_what_a_restoration_keeps(connection):
                return "the database of Waterfall holds more than its migrations"
    finally:
        waterfall.dispose()
    return None


def restore_fresh(
    archive: Path, databases: Mapping[str, str], migrate: Callable[[Engine], None]
) -> None:
    """Restore ``archive`` into the ``databases`` of a fresh platform, as their owners.

    An archive that does not read back whole, or of a newer version, is refused (422) and a
    platform that is not fresh (``NotFreshError``), each before any database is touched.
    """
    held = not_fresh(databases)
    if held is not None:
        raise NotFreshError(held)
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
                subjects = write_back_after_restoration(
                    connection, restoration, utc_now(), fresh=True
                )
        finally:
            owner.dispose()
    # A fresh platform has anonymised no account since the archive: its journal kept is empty, and
    # the archive's own holds none named. One would be removed from the realm by a restoration;
    # here Keycloak has not started, and the log says it.
    if subjects:
        logger.warning("restore.fresh_accounts_anonymised_again", count=len(subjects))
    logger.info("restore.fresh_done")
