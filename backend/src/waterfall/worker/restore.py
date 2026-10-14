# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Read a backup and replace the two databases by its dumps, nothing partial (WF-ADM-0160).

The archive's manifest is read and each dump checked against its digest; one of a newer version
than the installation is refused before anything changes. Each database is made again from its
dump, as its owner (#701), without the owners and the rights of the source. What runs the
restoration — the service ``restore`` that US-0440/L2b brings (#985) — does so in this order: it
keeps what the module of the backups writes back (``keep_for_restoration``), replaces the two
databases by these functions, applies the migrations that follow the backup, and only then writes
back (``write_back_after_restoration``): the rights kept are given back to the role of the service
on the tables of the installation, which a backup of an earlier revision lacks until it is
migrated. Taken up after an interruption, it starts again from the beginning (WF-ARC-0090).
"""

import json
import re
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

from waterfall import __version__
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.logs import get_logger
from waterfall.worker.backup import (
    CHUNK,
    DATABASES,
    MANIFEST,
    connect,
    connection,
    digest,
    listed,
    reached,
)

BACKUP_FROM_NEWER_VERSION = "BACKUP_FROM_NEWER_VERSION"
FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"
# What pg_restore says of its own error starts a line of its own. The lines that follow it —
# ``DETAIL``, ``CONTEXT``, ``Command was:`` — quote the rows of the dump, the secrets of the clients
# of the identity provider and the digests of its passwords among them, which no mask of the
# journal knows (WF-OBS-0020): they are left out, and so is a value the error quotes — from the
# first opening quotation mark, of whatever form, to the end of the line: a value may hold a
# quotation mark or a line break that cuts it, and a few bytes may follow it. The mask fails
# closed, losing only what the message says after it. A server that does not say its severity in
# English (``ERREUR:``, lc_messages of a PostgreSQL of the IT department) says its message in a
# language whose words are unknown here: all it says is masked.
ERROR_LINE = "pg_restore: error: "
SERVER_ERROR = "ERROR:"
SEPARATOR = ": "
# Any quotation mark, opening or closing, in English and in other languages: a German message
# opens its value with », a Danish one with the single angle quotation mark.
QUOTED = re.compile("[\"'\u00ab\u00bb\u2039\u203a\u201c\u201d\u201e\u2018\u2019\u201a].*")
MASK = "..."

# The event a database the restoration cannot reach writes to the journal of the service.
UNREACHED = "restore.database_unreached"

logger = get_logger(__name__)


class RestoreError(RuntimeError):
    """A database reached that pg_restore could not restore: an internal error, not an outage."""


def release(version: str) -> tuple[int, ...]:
    """Give the numbers of the release of a version, ``1.10.2`` before ``1.9`` never."""
    numbers = re.findall(r"\d+", version.split("+", maxsplit=1)[0])
    return tuple(int(number) for number in numbers[:3])


def extracted(path: Path, folder: Path, taken_at: datetime | None = None) -> dict[str, Path]:
    """Read an archive: its manifest, a version no newer than the installed one, each dump checked.

    A newer version is refused (422, ``BACKUP_FROM_NEWER_VERSION``); an archive that does not read
    back whole — a database of the platform lacking, a dump missing, unlike its digest, or that
    ``pg_restore`` does not list — as unreadable (422), before any database is touched; so is one
    whose manifest does not say ``taken_at``, the date confirmed, when it is given. Nothing of the
    archive is extracted but under a name chosen here.
    """
    try:
        with tarfile.open(path) as tar:
            manifest = json.loads(_member(tar, MANIFEST).read())
            said = None if taken_at is None else datetime.fromisoformat(str(manifest["taken_at"]))
            if said != taken_at:
                raise UnprocessableError(FILE_FORMAT_UNREADABLE)
            version = str(manifest["application_version"])
            if release(version) > release(__version__):
                params = {"backup_version": version, "installed_version": __version__}
                raise UnprocessableError(BACKUP_FROM_NEWER_VERSION, params)
            databases = manifest["databases"]
            if sorted(str(database["name"]) for database in databases) != sorted(DATABASES):
                raise UnprocessableError(FILE_FORMAT_UNREADABLE)
            dumps: dict[str, Path] = {}
            for database in databases:
                copy = folder / f"restored-{len(dumps)}.dump"
                with copy.open("wb") as written:
                    shutil.copyfileobj(_member(tar, database["file"]), written, CHUNK)
                if digest(copy) != database["sha256"] or not listed(copy):
                    raise UnprocessableError(FILE_FORMAT_UNREADABLE)
                dumps[str(database["name"])] = copy
    except (tarfile.TarError, OSError, KeyError, TypeError, ValueError) as error:
        raise UnprocessableError(FILE_FORMAT_UNREADABLE) from error
    return dumps


def _member(tar: tarfile.TarFile, name: str) -> Any:
    member = tar.extractfile(name)
    if member is None:
        raise KeyError(name)
    return member


def replace(name: str, dump: Path, address: str, folder: Path) -> None:
    """Make a database again from its dump, as its owner: its schema dropped, the dump restored.

    The schema is dropped and made again in a transaction of its own; the dump is then restored in
    one transaction of ``pg_restore``, without the owners and the rights of the source: the role of
    the service of another installation has another name. Interrupted between the two, the
    database is left with an empty schema, and the restoration taken up starts again from the
    beginning (WF-ARC-0090). A database that stops answering is unavailable (503), one that answers
    and refuses the dump an internal error (#907).
    """
    with connect(address, UNREACHED) as session:
        session.execute("DROP SCHEMA public CASCADE")
        session.execute("CREATE SCHEMA public")
    environment = connection(address, folder / f"{name}.service")
    with dump.open("rb") as read:
        done = subprocess.run(
            [
                "/usr/bin/pg_restore",
                # The service ``connection`` writes (``SERVICE`` of the backup).
                "--dbname=service=backup",
                "--single-transaction",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--no-password",
            ],
            stdin=read,
            capture_output=True,
            env=environment,
            check=False,
        )
    if done.returncode != 0:
        reached(address, UNREACHED)
        logger.error("restore.replace_failed", database=name, said=errors_of(done.stderr))
        raise RestoreError(name)


def errors_of(said: bytes) -> list[str]:
    """Give the errors pg_restore said, without the rows they quote nor a value quoted in them.

    A line of pg_restore's own error is kept: what it did, and the message of the server, each
    value the server quotes masked — the name of a constraint, of a column, or a value refused.
    """
    lines = said.decode(errors="replace").splitlines()
    return [_masked(line) for line in lines if line.startswith(ERROR_LINE)]


def _masked(line: str) -> str:
    done, separator, said = line.removeprefix(ERROR_LINE).partition(SEPARATOR)
    if not separator:
        return line
    if not said.startswith(SERVER_ERROR):
        return ERROR_LINE + done + separator + MASK
    said = QUOTED.sub(f'"{MASK}"', said, count=1)
    return ERROR_LINE + done + separator + said
