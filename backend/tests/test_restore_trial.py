# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration, played on a throwaway platform, its failure included (US-2930).

Each test makes an installation of its own (``installations``) — the production —, writes in it a
project, a marked revision and what it kept, a line of cost and accounts of the identity provider,
and has it backed up as the schedule does. The ephemeral platform is two databases made for the
test on the PostgreSQL of the tests, and an API started on the database restored, whose readiness
says whether it started: the test of the restoration restores, starts, counts, compares, and gives
its outcome back to the production, which inscribes it in ``restore_test``.
"""

import io
import json
import tarfile
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import httpx2
import pytest
from backup_rows import Row, recorded
from backup_support import add_accounts
from costs_support import insert_cost_line, write_import
from fastapi.testclient import TestClient
from indicators_support import indicator_row
from installations import created, dropped
from project_rows import AT, MARKED, insert_project, insert_revision, unguarded
from sqlalchemy import exc, func, insert, select, text, update
from sqlalchemy.engine import make_url

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.backups.interface import (
    MANIFEST,
    BackupToTest,
    RestoreTestOutcome,
    backup_to_test,
    record_restore_test,
)
from waterfall.core.backups.tables import RESTORE_TEST_FAILURE_LENGTH, Backup, RestoreTest
from waterfall.core.indicators.interface import kept_indicators_digest
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.revisions.tables import Revision
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.restore.trial import (
    NOT_STARTED,
    READINESS,
    UNREADABLE,
    WITHOUT_INVENTORY,
    Ephemeral,
    Readiness,
    RestoreTrial,
    ready,
)
from waterfall.worker import backup as backup_module
from waterfall.worker.backup import DATABASES, Dumped
from waterfall.worker.inventory import Inventory, inventory_of, read_or_none

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from installations import Installation, Take
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

# The accounts of the realm a test writes: the people, the account of service apart.
PEOPLE = 2


@dataclass
class Written:
    """What a test wrote in the production before its backup."""

    project_id: UUID
    revision_id: UUID


def written(installation: Installation) -> Written:
    """Write a project, its revision marked with what it kept, a line of cost, and two people."""
    project_id, revision_id = uuid4(), uuid4()
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        connection.execute(insert_project(id=project_id))
        connection.execute(select(func.create_project_partitions(project_id)))
        connection.execute(insert_revision(project_id, id=revision_id))
    with owner.begin() as connection:
        connection.execute(
            insert(RevisionIndicator).values(**indicator_row(project_id, revision_id))
        )
        connection.execute(update(Revision).where(Revision.id == revision_id).values(**MARKED))
        insert_cost_line(connection, write_import(connection, project_id))
    owner.dispose()
    provider = create_database_engine(installation.owner["identity_provider"])
    with provider.begin() as connection:
        add_accounts(connection, PEOPLE)
    provider.dispose()
    return Written(project_id, revision_id)


@pytest.fixture
def ephemeral_databases(database_url: str) -> Iterator[dict[str, str]]:
    """Make the two databases of an ephemeral platform, empty; drop them after the test."""
    suffix = uuid4().hex
    names = (f"waterfall_test_ephemeral_{suffix}", f"waterfall_test_ephemeral_idp_{suffix}")
    addresses = [created(database_url, name) for name in names]
    yield dict(zip(DATABASES, addresses, strict=True))
    dropped(database_url, *addresses)
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f'DROP ROLE IF EXISTS "{names[0]}_service"'))
    server.dispose()


@dataclass
class Platform:
    """The ephemeral platform of a test: what it was told, and how its API answered."""

    databases: dict[str, str]
    keycloak: Keycloak
    settings: ServiceSettings
    queue: TaskQueue
    installation: Installation
    after_migrations: Callable[[Engine], None] = lambda _owner: None
    told: list[str] = field(default_factory=list[str])

    def migrate(self, owner: Engine) -> None:
        """Migrate the database restored, then do what the test asks of it."""
        upgrade(owner)
        self.after_migrations(owner)

    def restored(self) -> None:
        """Hear that the databases are restored."""
        self.told.append("restored")

    def started(self) -> bool:
        """Start the API on the database restored, and tell whether its readiness says so."""
        self.told.append("started")
        database = Database(create_database_engine(self.databases["waterfall"]))
        try:
            administration = KeycloakAdmin(self.keycloak, self.settings)
            services = Services(
                database, self.keycloak, administration, self.queue, self.installation.bucket
            )
            with TestClient(create_app(services), raise_server_exceptions=False) as api:
                answer = api.get(READINESS)
            return ready(answer.status_code, answer.json())
        finally:
            database.dispose()

    def ephemeral(self) -> Ephemeral:
        """Give the platform as the test of a restoration drives it."""
        return Ephemeral(self.databases, self.migrate, self.restored, self.started)


@pytest.fixture
def platform(
    ephemeral_databases: dict[str, str],
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    installation: Installation,
) -> Platform:
    """Give the ephemeral platform of a test."""
    return Platform(ephemeral_databases, keycloak, realm_settings, queue, installation)


def trial_on(installation: Installation, ephemeral: Ephemeral) -> RestoreTrial:
    """Give the test of a restoration of the production ``installation`` on ``ephemeral``."""
    return RestoreTrial(installation.database, installation.bucket, ephemeral)


def inscribed_tests(installation: Installation) -> list[RestoreTest]:
    """Read the tests the production inscribed, the latest first."""
    with installation.database.transaction() as session:
        rows = session.scalars(select(RestoreTest).order_by(RestoreTest.finished_at.desc()))
        found = list(rows)
        session.expunge_all()
    return found


def backup_of(installation: Installation, task_id: UUID) -> Backup:
    """Read the backup a task took."""
    with installation.database.transaction() as session:
        backup = session.scalars(select(Backup).where(Backup.task_id == task_id)).one()
        session.expunge(backup)
    return backup


def manifest_said(installation: Installation, task_id: UUID) -> dict[str, object]:
    """Read the manifest of the archive a task took."""
    key = f"backup-{task_id}.tar"
    body = installation.bucket.client.get_object(Bucket=installation.bucket.name, Key=key)["Body"]
    with tarfile.open(fileobj=io.BytesIO(body.read()), mode="r:") as tar:
        member = tar.extractfile(MANIFEST)
        assert member is not None
        return json.loads(member.read())


@pytest.mark.story("US-2930")
def test_the_manifest_of_a_backup_says_what_it_holds_and_the_indicators_of_a_sample(
    installation: Installation, take: Take
) -> None:
    # Propre à l'US : « le nombre de projets, de révisions marquées, de lignes de coût et de comptes
    # du fournisseur d'identité » et « les indicateurs conservés d'un échantillon de révisions
    # marquées » : the manifest says them, the account of service apart.
    project = written(installation)
    said = manifest_said(installation, take())
    inventory = inventory_of(said)
    with installation.database.transaction() as session:
        digest = kept_indicators_digest(session, project.project_id, project.revision_id)
    assert inventory == Inventory(
        1, 1, 1, PEOPLE, {(project.project_id, project.revision_id): digest}
    )
    with installation.database.transaction() as session:
        nothing = kept_indicators_digest(session, project.project_id, uuid4())
    assert digest != nothing


@pytest.mark.requirement("WF-EXP-0060-A")
@pytest.mark.story("US-2930")
def test_the_latest_scheduled_backup_verified_is_restored_started_compared_and_inscribed(
    installation: Installation, take: Take, platform: Platform, logs: Logs
) -> None:
    # « Un test de restauration mensuel est exécuté, et son résultat daté est consultable. » : the
    # production inscribes the result, dated, of the test the ephemeral platform ran; propre à
    # l'US : the platform starts on the databases restored — told once they are —, and its counts
    # and the indicators of the sample are those of the backup.
    written(installation)
    take()
    tested = take()
    before = utc_now()
    assert trial_on(installation, platform.ephemeral())() is True
    (test,) = inscribed_tests(installation)
    backup = backup_of(installation, tested)
    assert (test.backup_id, test.backup_taken_at) == (backup.id, backup.taken_at)
    assert test.succeeded is True
    assert test.failure is None
    assert (test.projects, test.marked_revisions, test.cost_lines, test.identity_accounts) == (
        1,
        1,
        1,
        PEOPLE,
    )
    assert before <= test.started_at <= test.finished_at <= utc_now()
    assert platform.told == ["restored", "started"]
    (succeeded,) = logs.named("restore_test.succeeded")
    assert succeeded["backup_id"] == str(backup.id)


@pytest.mark.requirement("WF-EXP-0060-A")
def test_the_test_fails_and_says_so_when_the_projects_restored_are_not_those_of_the_backup(
    installation: Installation, take: Take, platform: Platform, logs: Logs
) -> None:
    # « Le test échoue et le signale si le nombre de projets restaurés diffère de celui de la
    # sauvegarde. » : a project more in the database restored than in the backup.
    written(installation)
    take()

    def one_project_more(owner: Engine) -> None:
        with owner.begin() as connection:
            connection.execute(insert_project())

    platform.after_migrations = one_project_more
    assert trial_on(installation, platform.ephemeral())() is False
    (test,) = inscribed_tests(installation)
    assert test.succeeded is False
    assert test.failure == "projects_differ"
    assert test.projects == 2
    (failed,) = logs.named("restore_test.failed")
    assert failed["reason"] == "projects_differ"
    assert failed["level"] == "error"


@pytest.mark.story("US-2930")
def test_a_kept_indicator_changed_by_the_restoration_fails_the_test(
    installation: Installation, take: Take, platform: Platform
) -> None:
    # Propre à l'US : « les indicateurs conservés d'un échantillon de révisions marquées sont
    # inchangés » : a document of the sample changed in the database restored, the counts equal.
    project = written(installation)
    take()

    def a_document_changed(owner: Engine) -> None:
        with owner.begin() as connection:
            unguarded(connection)
            connection.execute(
                update(RevisionIndicator)
                .where(RevisionIndicator.revision_id == project.revision_id)
                .values(document={"changed": True})
            )

    platform.after_migrations = a_document_changed
    assert trial_on(installation, platform.ephemeral())() is False
    (test,) = inscribed_tests(installation)
    assert test.failure == "indicators_differ"
    assert (test.projects, test.marked_revisions, test.cost_lines) == (1, 1, 1)


@pytest.mark.story("US-2930")
def test_a_platform_that_does_not_start_fails_the_test_its_counts_kept(
    installation: Installation, take: Take, platform: Platform
) -> None:
    # Propre à l'US : « le test vérifie que la plateforme démarre ».
    written(installation)
    take()
    ephemeral = Ephemeral(platform.databases, platform.migrate, platform.restored, lambda: False)
    assert trial_on(installation, ephemeral)() is False
    (test,) = inscribed_tests(installation)
    assert test.failure == NOT_STARTED
    assert test.identity_accounts == PEOPLE


@pytest.mark.story("US-2930")
def test_an_archive_gone_or_without_what_it_holds_fails_the_test_without_counts(
    installation: Installation, take: Take, platform: Platform, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The archive of a backup taken before US-2930 says nothing of what it holds: the test cannot
    # compare, and fails, nothing started; one gone from the bucket cannot be read.
    manifest = backup_module.manifest

    def as_before(
        taken_at: datetime, revision: str, dumps: list[Dumped], inventory: Inventory
    ) -> dict[str, Any]:
        said = manifest(taken_at, revision, dumps, inventory)
        return {key: value for key, value in said.items() if key != "inventory"}

    monkeypatch.setattr(backup_module, "manifest", as_before)
    take()
    monkeypatch.undo()
    assert trial_on(installation, platform.ephemeral())() is False
    (test,) = inscribed_tests(installation)
    assert (test.failure, test.projects) == (WITHOUT_INVENTORY, None)
    assert platform.told == []
    installation.bucket.remove(backup_of_latest(installation).object_key)
    assert trial_on(installation, platform.ephemeral())() is False
    assert inscribed_tests(installation)[0].failure == UNREADABLE


def backup_of_latest(installation: Installation) -> Backup:
    """Read the latest backup of the production."""
    with installation.database.transaction() as session:
        backup = session.scalars(select(Backup).order_by(Backup.taken_at.desc()).limit(1)).one()
        session.expunge(backup)
    return backup


@pytest.mark.story("US-2930")
def test_neither_a_manual_backup_nor_one_that_failed_its_verification_is_tested(
    installation: Installation, platform: Platform, logs: Logs
) -> None:
    # The latest scheduled backup whose verification passed is the one restored; without one,
    # nothing is restored nor inscribed, and the test says so.
    database = installation.database
    tested = recorded(database, AT, Row(origin="scheduled"))
    recorded(database, AT + timedelta(hours=1), Row(origin="manual"))
    recorded(database, AT + timedelta(hours=2), Row(origin="scheduled", verification="failed"))
    with database.transaction() as session:
        assert backup_to_test(session) == BackupToTest(tested, AT, backup_of_id(session, tested))
    with database.transaction() as session:
        session.execute(update(Backup).values(origin="manual"))
    assert trial_on(installation, platform.ephemeral())() is False
    assert inscribed_tests(installation) == []
    assert platform.told == []
    assert len(logs.named("restore_test.no_backup")) == 1


def backup_of_id(session: Session, backup_id: UUID) -> str:
    """Give the key of the archive of a backup."""
    key = session.scalar(select(Backup.object_key).where(Backup.id == backup_id))
    assert key is not None
    return key


@pytest.mark.story("US-2930")
def test_a_reason_longer_than_its_column_is_cut_and_the_test_still_failed(
    installation: Installation,
) -> None:
    backup_id = recorded(installation.database, AT, Row(origin="scheduled"))
    too_long = "x" * (RESTORE_TEST_FAILURE_LENGTH + 5)
    outcome = RestoreTestOutcome(AT, AT, BackupToTest(backup_id, AT, "key"), None, too_long)
    with installation.database.transaction() as session:
        record_restore_test(session, outcome)
    (test,) = inscribed_tests(installation)
    assert test.succeeded is False
    assert test.failure is not None
    assert len(test.failure) == RESTORE_TEST_FAILURE_LENGTH
    assert test.failure.endswith("…")


SAMPLED = (UUID(int=1), UUID(int=2))
DESCRIBED: dict[str, object] = {
    "projects": 3,
    "marked_revisions": 4,
    "cost_lines": 5,
    "identity_accounts": 6,
    "indicator_sample": [
        {"project_id": str(SAMPLED[0]), "revision_id": str(SAMPLED[1]), "sha256": "ab"}
    ],
}


@pytest.mark.story("US-2930")
def test_what_a_manifest_says_it_holds_is_read_and_nothing_else_is_trusted() -> None:
    assert inventory_of({"inventory": DESCRIBED}) == Inventory(3, 4, 5, 6, {SAMPLED: "ab"})
    assert inventory_of({}) is None
    assert inventory_of({"inventory": []}) is None
    for name, wrong in (
        ("projects", -1),
        ("cost_lines", True),
        ("marked_revisions", "4"),
        ("indicator_sample", [{"project_id": "not a uuid"}]),
        ("indicator_sample", 3),
    ):
        assert inventory_of({"inventory": {**DESCRIBED, name: wrong}}) is None, name
    lacking = {key: value for key, value in DESCRIBED.items() if key != "identity_accounts"}
    assert inventory_of({"inventory": lacking}) is None


@pytest.mark.requirement("WF-EXP-0060-A")
def test_each_count_that_differs_gives_its_reason_the_projects_first() -> None:
    backup = Inventory(3, 4, 5, 6, {SAMPLED: "ab"})
    assert backup.differences(backup) == []
    assert backup.differences(Inventory(2, 4, 5, 7, {SAMPLED: "cd"})) == [
        "projects_differ",
        "identity_accounts_differ",
        "indicators_differ",
    ]


def readiness_said(*available: str) -> dict[str, object]:
    """Give what the readiness answers, the components named available."""
    components = ("database", "cache", "identity_provider")
    return {
        "status": "ready",
        "components": [
            {"component": name, "is_available": name in available} for name in components
        ],
    }


@pytest.mark.story("US-2930")
def test_the_platform_is_ready_when_its_database_and_its_identity_provider_answer() -> None:
    assert ready(200, readiness_said("database", "identity_provider")) is True
    assert ready(200, readiness_said("database")) is False
    assert ready(503, readiness_said("database", "identity_provider")) is False
    assert ready(200, None) is False
    assert ready(200, {"components": "none"}) is False


@dataclass
class Clock:
    """A clock the pauses advance."""

    now: float = 0.0
    pauses: list[float] = field(default_factory=list[float])

    def read(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.pauses.append(seconds)
        self.now += seconds


@pytest.mark.story("US-2930")
def test_the_readiness_is_asked_again_until_the_api_is_ready_or_its_patience_spent() -> None:
    answers: list[tuple[int, object]] = [
        (503, None),
        (200, readiness_said("database", "identity_provider")),
    ]
    refused = [True]
    clock = Clock()

    def ask() -> tuple[int, object]:
        if refused.pop() if refused else False:
            message = "refused"
            raise httpx2.ConnectError(message)
        return answers.pop(0)

    assert Readiness(ask, 60, 5, clock.read, clock.sleep)() is True
    assert clock.pauses == [5, 5]
    late = Clock()
    assert Readiness(lambda: (503, None), 12, 5, late.read, late.sleep)() is False
    assert late.pauses == [5, 5, 5]


class Answering(BaseHTTPRequestHandler):
    """An API whose readiness says its database and its identity provider answer, on HTTP."""

    def do_GET(self) -> None:
        body = json.dumps(readiness_said("database", "identity_provider")).encode()
        status = 200 if self.path == READINESS else 404
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.mark.story("US-2930")
def test_the_readiness_of_the_api_is_asked_at_its_address() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Answering)
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    try:
        address = f"http://127.0.0.1:{server.server_address[1]}"
        assert Readiness.of(address, None, 0)() is True
    finally:
        server.shutdown()
        server.server_close()
    assert Readiness.of(address, None, 0)() is False


@pytest.mark.story("US-2930")
def test_a_platform_that_cannot_be_restored_or_counted_or_an_archive_that_does_not_read_fails(
    installation: Installation, take: Take, platform: Platform
) -> None:
    written(installation)
    task_id = take()
    nowhere: dict[str, str] = dict.fromkeys(
        DATABASES, "postgresql://nobody:nothing@127.0.0.1:9/nowhere"
    )
    unreached = Ephemeral(nowhere, platform.migrate, platform.restored, platform.started)
    assert trial_on(installation, unreached)() is False

    def realm_gone(_owner: Engine) -> None:
        provider = create_database_engine(platform.databases["identity_provider"])
        with provider.begin() as connection:
            connection.execute(text("DROP TABLE user_entity"))
        provider.dispose()

    platform.after_migrations = realm_gone
    assert trial_on(installation, platform.ephemeral())() is False
    platform.told.clear()
    damaged = installation.bucket.client
    damaged.put_object(Bucket=installation.bucket.name, Key=f"backup-{task_id}.tar", Body=b"no")
    assert trial_on(installation, platform.ephemeral())() is False
    reasons = [test.failure for test in reversed(inscribed_tests(installation))]
    assert reasons == ["not_restored", "not_counted", UNREADABLE]
    assert platform.told == []


class Reading:
    """A session that gives the rows of a read in the order a test says, as a database may."""

    def __init__(self, rows: list[tuple[str, str, datetime, dict[str, int]]]) -> None:
        self.rows = rows

    def execute(self, _statement: object) -> Iterator[tuple[str, str, datetime, dict[str, int]]]:
        return iter(self.rows)


@pytest.mark.story("US-2930")
def test_the_digest_of_the_kept_indicators_does_not_depend_on_the_order_a_database_reads_them() -> (
    None
):
    # The collation of a database orders text its own way: the digest sorts what it reads.
    taken = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    rows = [
        ("Z", "a", taken, {"n": 1}),
        ("a", "b", taken, {"n": 2}),
        ("a", "B", taken, {"n": 3}),
        ("_", "a", taken, {"n": 4}),
    ]
    project, revision = uuid4(), uuid4()
    digests = {
        kept_indicators_digest(cast("Session", Reading(order)), project, revision)
        for order in (rows, list(reversed(rows)), [rows[2], rows[0], rows[3], rows[1]])
    }
    assert len(digests) == 1


@pytest.mark.story("US-2930")
def test_a_table_missing_is_not_counted_but_a_right_missing_fails_the_reading(
    ephemeral_databases: dict[str, str], database_url: str
) -> None:
    address = ephemeral_databases["waterfall"]
    owner = create_database_engine(address)
    with owner.begin() as connection:
        connection.execute(text("CREATE TABLE kept (n integer)"))
    owner.dispose()
    assert read_or_none(address, lambda c: c.execute(text("SELECT n FROM absent"))) is None
    assert read_or_none(address, lambda c: c.execute(text("SELECT absent FROM kept"))) is None
    name = f"waterfall_test_reader_{uuid4().hex}"
    secret = uuid4().hex
    database = make_url(address).database
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f"CREATE ROLE \"{name}\" LOGIN PASSWORD '{secret}'"))
        connection.execute(text(f'GRANT CONNECT ON DATABASE "{database}" TO "{name}"'))
    try:
        reader = make_url(address).set(username=name, password=secret)
        refused = reader.render_as_string(hide_password=False)
        with pytest.raises(exc.ProgrammingError):
            read_or_none(refused, lambda c: c.execute(text("SELECT n FROM kept")))
    finally:
        with server.connect() as connection:
            connection.execute(text(f'REVOKE CONNECT ON DATABASE "{database}" FROM "{name}"'))
            connection.execute(text(f'DROP ROLE "{name}"'))
        server.dispose()
