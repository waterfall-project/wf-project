# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration, on an ephemeral platform (WF-EXP-0060, US-2930).

``waterfall-restore test`` runs beside an ephemeral platform — a PostgreSQL, a Keycloak and an API
made for the test, which no user reaches —, the only place out of the production where a copy not
anonymised exists (WF-EXP-0010). In this order:

1. it asks the production for the latest scheduled backup whose verification passed, as the role
   of the service;
2. it reads that archive from the bucket of the backups, each dump checked against its digest, and
   what its manifest says it holds (``waterfall.worker.inventory``);
3. it replaces the two databases of the ephemeral platform by the dumps, as their owners, and
   migrates Waterfall's to the revision of the installation, as a restoration does
   (``waterfall.worker.restore``), but keeps nothing and writes nothing back: the ephemeral
   platform has nothing of its own to keep;
4. it says it has restored (``restored``), on which the ephemeral Keycloak and API start, and waits
   for the API to be ready, the database and the identity provider available (``Readiness``);
5. it counts the projects, the marked revisions, the lines of cost and the accounts of the
   identity provider in the databases restored, digests the indicators of the revisions the
   manifest sampled, and compares;
6. it gives its outcome back to the production, which inscribes it in ``restore_test``, as the
   role of the service, by its own connection: the ephemeral platform exposes nothing, and the
   production reaches none of it.

It fails, and says so in its journal and by its status, if any count differs — the number of the
projects first —, if a sampled revision kept other indicators, if the platform did not start, or
if the backup could not be read or restored; the reasons are in the row it inscribes. Without a
backup to test, it inscribes nothing: a test names the backup it restored.
"""

import json
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx2
from sqlalchemy.orm import Session

from waterfall.core.backups.interface import (
    MANIFEST,
    BackupToTest,
    RestoreCounts,
    RestoreTestOutcome,
    backup_to_test,
    record_restore_test,
)
from waterfall.platform.database import create_database_engine, utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.keycloak import trusted
from waterfall.platform.logs import get_logger
from waterfall.platform.storage import MissingObjectError
from waterfall.worker.backup import DATABASES, REALM
from waterfall.worker.inventory import Inventory, accounts_of, counted, inventory_of
from waterfall.worker.restore import extracted, replace

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.storage import Bucket

# Why a test failed before it could count (``RestoreTest.failure``); a count that differs gives
# ``<count>_differ`` (``waterfall.worker.inventory``).
UNREADABLE = "backup_unreadable"
WITHOUT_INVENTORY = "manifest_without_inventory"
NOT_RESTORED = "not_restored"
NOT_STARTED = "not_started"
NOT_COUNTED = "not_counted"
# The readiness of the API (``getReadiness``), and the components it must say available.
READINESS = "/api/v1/health/ready"
OK = 200
NEEDED = frozenset({"database", "identity_provider"})
# The pause between two asks of the readiness, and how long one ask waits, in seconds.
PAUSE = 5.0
ASK_TIMEOUT = 10.0

logger = get_logger(__name__)


def ready(status: int, body: object) -> bool:
    """Tell whether an answer of the readiness says the platform started, its components available.

    The API answers 200 once its database answers; the identity provider must answer too: the test
    starts Keycloak on its database restored.
    """
    if status != OK or not isinstance(body, dict):
        return False
    components = cast("dict[str, Any]", body).get("components")
    if not isinstance(components, list):
        return False
    listed = cast("list[object]", components)
    described = [cast("dict[str, Any]", each) for each in listed if isinstance(each, dict)]
    available = {each.get("component") for each in described if each.get("is_available") is True}
    return available >= NEEDED


@dataclass(frozen=True, slots=True)
class Readiness:
    """Wait for the ephemeral API to be ready, ``patience`` seconds at most."""

    ask: Callable[[], tuple[int, object]]
    patience: float
    pause: float = PAUSE
    clock: Callable[[], float] = field(default=time.monotonic)
    sleep: Callable[[float], None] = field(default=time.sleep)

    @classmethod
    def of(cls, address: str, verify: str | None, patience: float) -> Readiness:
        """Ask the readiness of the API at ``address``, checked against the roots of ``verify``."""

        def ask() -> tuple[int, object]:
            with httpx2.Client(
                base_url=address, verify=trusted(verify), timeout=ASK_TIMEOUT
            ) as http:
                answer = http.get(READINESS)
            try:
                return answer.status_code, answer.json()
            except ValueError:
                return answer.status_code, None

        return cls(ask, patience)

    def __call__(self) -> bool:
        """Tell whether the API got ready in time; an API that does not answer is not ready."""
        deadline = self.clock() + self.patience
        while True:
            try:
                status, body = self.ask()
            except httpx2.HTTPError:
                status, body = 0, None
            if ready(status, body):
                return True
            if self.clock() >= deadline:
                return False
            self.sleep(self.pause)


def manifest_of(archive: Path) -> dict[str, Any]:
    """Read the manifest of an archive; unreadable (422) if it does not hold one that reads."""
    try:
        with tarfile.open(archive, mode="r:") as tar:
            member = tar.extractfile(MANIFEST)
            said = json.loads(member.read()) if member is not None else None
    except (tarfile.TarError, OSError, KeyError, ValueError, RecursionError) as error:
        raise UnprocessableError(UNREADABLE) from error
    if not isinstance(said, dict):
        raise UnprocessableError(UNREADABLE)
    return cast("dict[str, Any]", said)


@dataclass(frozen=True, slots=True)
class Tested:
    """What a test found: its counts, if it got to count, and why it failed, if it did."""

    counts: RestoreCounts | None = None
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class Ephemeral:
    """The ephemeral platform, as the test drives it.

    ``databases`` are its two databases, by their name in the archive, as their owners; ``migrate``
    brings Waterfall's to the revision of the installation; ``restored`` tells the platform it may
    start, and ``started`` waits for it, then tells whether it did.
    """

    databases: Mapping[str, str]
    migrate: Callable[[Engine], None]
    restored: Callable[[], None]
    started: Callable[[], bool]


class RestoreTrial:
    """Test the restoration of the latest scheduled backup verified, on an ephemeral platform."""

    def __init__(
        self, production: Database, bucket: Bucket, ephemeral: Ephemeral, realm: str = REALM
    ) -> None:
        """Read the backups of ``production`` from ``bucket``; restore them on ``ephemeral``.

        ``realm`` is the realm whose accounts are counted, the installation's.
        """
        self.production = production
        self.bucket = bucket
        self.ephemeral = ephemeral
        self.databases = ephemeral.databases
        self.realm = realm

    def __call__(self) -> bool:
        """Test, then inscribe the outcome in the production; tell whether the test succeeded."""
        started_at = utc_now()
        with self.production.transaction() as session:
            backup = backup_to_test(session)
        if backup is None:
            logger.error("restore_test.no_backup")
            return False
        tested = self.tested(backup)
        outcome = RestoreTestOutcome(started_at, utc_now(), backup, tested.counts, tested.failure)
        with self.production.transaction() as session:
            test_id = record_restore_test(session, outcome)
        said = {"restore_test_id": str(test_id), "backup_id": str(backup.backup_id)}
        if tested.failure is None:
            logger.info("restore_test.succeeded", **said)
            return True
        logger.error("restore_test.failed", reason=tested.failure, **said)
        return False

    def tested(self, backup: BackupToTest) -> Tested:
        """Restore a backup on the ephemeral platform, have it start, count and compare."""
        with tempfile.TemporaryDirectory(prefix="waterfall-restore-test-") as work:
            folder = Path(work)
            archive = folder / "tested.tar"
            try:
                self.bucket.download(backup.object_key, archive)
                expected = inventory_of(manifest_of(archive))
                dumps = extracted(archive, folder)
            except MissingObjectError:
                logger.warning("restore_test.unreadable", reason="archive_missing")
                return Tested(failure=UNREADABLE)
            except UnprocessableError as error:
                logger.warning("restore_test.unreadable", reason=error.code)
                return Tested(failure=UNREADABLE)
            if expected is None:
                return Tested(failure=WITHOUT_INVENTORY)
            try:
                self.replaced(dumps, folder)
            except Exception:
                logger.exception("restore_test.not_restored")
                return Tested(failure=NOT_RESTORED)
        self.ephemeral.restored()
        reasons = [] if self.ephemeral.started() else [NOT_STARTED]
        try:
            found = self.counted(expected)
        except Exception:
            logger.exception("restore_test.not_counted")
            return Tested(failure=", ".join([*reasons, NOT_COUNTED]))
        reasons += expected.differences(found)
        counts = RestoreCounts(
            found.projects, found.marked_revisions, found.cost_lines, found.identity_accounts
        )
        return Tested(counts, ", ".join(reasons) or None)

    def replaced(self, dumps: Mapping[str, Path], folder: Path) -> None:
        """Replace each database of the ephemeral platform by its dump, then migrate Waterfall's."""
        for name in DATABASES:
            replace(name, dumps[name], self.databases[name], folder)
        owner = create_database_engine(self.databases["waterfall"])
        try:
            self.ephemeral.migrate(owner)
        finally:
            owner.dispose()

    def counted(self, expected: Inventory) -> Inventory:
        """Count the databases restored, and digest the indicators of the revisions sampled."""
        provider = create_database_engine(self.databases["identity_provider"])
        try:
            with provider.connect() as connection:
                accounts = accounts_of(connection, self.realm)
        finally:
            provider.dispose()
        owner = create_database_engine(self.databases["waterfall"])
        try:
            with Session(owner) as session, session.begin():
                return counted(session, accounts, list(expected.sample))
        finally:
            owner.dispose()
