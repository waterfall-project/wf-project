# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fixtures of the tests of the service."""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
from access_rows import role
from backup_support import stand_in_realm, worker_of
from estimate_support import pin_year
from fastapi.testclient import TestClient
from installations import Installation, Take, installed, taker
from installed_reference import install
from migrations_support import scratch_database
from openapi_core import Config, OpenAPI
from project_rows import drop_every_partition, empty_database, unguarded
from pydantic import SecretStr
from realm import KEY, TestRealm
from sharding import in_order, part_of
from sqlalchemy import Engine, insert, text
from sqlalchemy.orm import Session
from support import (
    CONTRACT,
    PLATFORM_ADDRESSES,
    PLATFORM_SECRETS,
    REFERENCE_PARTS,
    WITNESS,
    ContractClient,
    Logs,
    PartSessions,
    ReferenceSessions,
    as_backup,
    bearer,
    captured_logs,
    emptied,
    nowhere,
    raw_account,
    service_role,
)
from task_handlers import deposit
from witness_template import (
    TEMPLATE,
    TEST_DATABASE_VARIABLE,
    WORKER_INPUT,
    Template,
    built,
    cloned,
    dropped,
    finished,
    start,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import Database, create_database_engine, engine_url
from waterfall.platform.installation import DELIVERED_TIME_ZONE, TIME_ZONE
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.maintenance import Maintenance
from waterfall.platform.queue import RESTORES, WORKER_TIMEOUT, TaskQueue
from waterfall.platform.settings import ServiceSettings, WitnessSettings, load_service_settings
from waterfall.platform.storage import Bucket
from waterfall.witness.main import load_witness

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uuid import UUID

    from backup_support import Run

    from waterfall.worker.backup import BackupTask

# A test that skips without declaring it by the mark ``unexecuted`` fails (US-2440): the plugin is
# the tools', shared with their tests, and found on the ``pythonpath`` of pyproject.toml.
pytest_plugins = ("wftools.unexecuted",)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Declare ``--shard``: one part of the tests, as the chain spreads them (back.yml)."""
    parser.addoption(
        "--shard",
        default=None,
        help="i/N: run the i-th of N parts of the tests, one in N in the order of their collection",
    )


# The fixtures whose tests are given a copy of the template.
ON_THE_WITNESS = ("witness", "witness_logged")


def pytest_configure(config: pytest.Config) -> None:
    """Name the template of the witness of the run, or read the name the controller gave."""
    given = cast("dict[str, str] | None", getattr(config, "workerinput", None))
    config.stash[TEMPLATE] = (
        Template.read(Path(given[WORKER_INPUT])) if given is not None else Template.planned()
    )


class Node(Protocol):
    """What the hook of pytest-xdist reads of a process it starts (``WorkerController``)."""

    config: pytest.Config
    workerinput: dict[str, object]


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node: Node) -> None:
    """Hand each process of pytest-xdist the directory of the template of the run."""
    node.workerinput[WORKER_INPUT] = str(node.config.stash[TEMPLATE].directory)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Wait for the loading this process started, until its deadline; the run's process drops all.

    Neither waits past the deadline of the loading (``witness_template``): pytest-timeout bounds
    the tests, not this hook.
    """
    finished()
    if not hasattr(config, "workerinput"):
        dropped(config.stash[TEMPLATE], os.environ.get(TEST_DATABASE_VARIABLE))


def heavy(item: pytest.Item) -> bool:
    """Tell whether a test is marked ``heavy``: it loads a platform of its own, over a minute."""
    return item.get_closest_marker("heavy") is not None


def on_the_witness(item: pytest.Item) -> bool:
    """Tell whether a test is given a copy of the template of the witness."""
    names = cast("list[str]", getattr(item, "fixturenames", []))
    return any(name in names for name in ON_THE_WITNESS)


def processes(config: pytest.Config) -> int:
    """Count the processes of pytest-xdist the run spreads its tests over: 1 without it.

    The controller and each of its processes read the same number (``-n``), hence compute the same
    order. ``auto`` is resolved by the controller before it collects, and handed to the others.
    """
    number = getattr(config.option, "numprocesses", None)
    return number if isinstance(number, int) and number > 0 else 1


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep the part of ``--shard``, the tests on the witness last; start loading the template.

    Under ``--shard i/N``, the tests at the positions that are i modulo N, from 1. The order of the
    collection is the same in every process of pytest-xdist, which compare what they collected:
    each keeps the same part. One in N, rather than N runs of files, spreads the files that load the
    witness, the longest, over all the parts; the heavy tests are counted apart, to spread evenly.

    The heavy tests start at the heads of the slices of the processes, the tests given a copy of the
    template of the witness after the others, while it loads (``sharding``): the first process to
    see one starts the loading, unless the run only collects.
    """
    shard = cast("str | None", config.getoption("shard"))
    if shard is not None:
        part, _, parts = shard.partition("/")
        if not (part.isdigit() and parts.isdigit() and 1 <= int(part) <= int(parts)):
            message = f"--shard must be i/N, 1 <= i <= N, not {shard!r}"
            raise pytest.UsageError(message)
        kept, left = part_of(items, int(part), int(parts), heavy)
        config.hook.pytest_deselected(items=left)
        items[:] = kept
    items[:] = in_order(items, on_the_witness, heavy, processes(config))
    if (
        any(on_the_witness(item) for item in items)
        and os.environ.get(TEST_DATABASE_VARIABLE)
        and not config.option.collectonly
    ):
        start(config.stash[TEMPLATE])


@pytest.fixture(autouse=True)
def pinned_year(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hold the clocks of the services that read a year or a day at the year of ``YEAR``.

    Before every test, and before the fixtures a test asks for, which set the clocks they want over
    these ones: no fixture calls ``pin_year`` in an order that would undo it (#3739).
    """
    pin_year(monkeypatch)


@pytest.fixture(autouse=True)
def installation_time_zone() -> Iterator[None]:
    """Give each test a process whose installation is in universal time, read from no database.

    The entry points of the processes name the database their time zone is read from (US-2200); a
    test reaches the core without them, and may name another source (``TIME_ZONE.read_from``),
    forgotten when it ends, whether it passed or failed: the time zone is restored after it too, so
    that a test that stops before its end leaves nothing to the tests that follow (#3613).
    """
    TIME_ZONE.read_from(lambda: DELIVERED_TIME_ZONE)
    yield
    TIME_ZONE.read_from(lambda: DELIVERED_TIME_ZONE)


@pytest.fixture
def platform_environment(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Give the process the secrets a service of the test platform is started with."""
    for name, value in {**PLATFORM_SECRETS, **PLATFORM_ADDRESSES}.items():
        monkeypatch.setenv(name, value)
    return PLATFORM_SECRETS


@pytest.fixture
def platform_settings(platform_environment: dict[str, str]) -> ServiceSettings:
    """Read the settings of the API of the test platform, secrets included."""
    settings = load_service_settings()
    assert (
        settings.database_url.get_secret_value() == platform_environment["WATERFALL_DATABASE_URL"]
    )
    return settings


@pytest.fixture
def services(platform_settings: ServiceSettings) -> Iterator[Services]:
    """Give the services of the API of the test platform, which reach nothing until asked to."""
    database = Database(create_database_engine(platform_settings.database_url.get_secret_value()))
    keycloak = Keycloak(platform_settings)
    administration = KeycloakAdmin(keycloak, platform_settings)
    yield Services(database, keycloak, administration, *nowhere())
    keycloak.close()
    database.dispose()


@pytest.fixture
def realm() -> Iterator[TestRealm]:
    """Serve one key of the realm of test, then stop."""
    served = TestRealm()
    served.add_key(KEY)
    yield served
    served.stop()


@pytest.fixture
def realm_settings(platform_settings: ServiceSettings, realm: TestRealm) -> ServiceSettings:
    """Give the settings of the API, Keycloak being the realm of test."""
    return platform_settings.model_copy(update={"keycloak_address": realm.address})


@pytest.fixture
def keycloak(realm_settings: ServiceSettings) -> Iterator[Keycloak]:
    """Give the client of the realm of test."""
    client = Keycloak(realm_settings)
    yield client
    client.close()


@pytest.fixture
def api(
    contract: OpenAPI, database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> ContractClient:
    """Give a client of the application on the database of test and the realm of test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    app = create_app(Services(database, keycloak, administration, *nowhere()))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def logs() -> Iterator[Logs]:
    """Capture the logs in memory, the secrets of the test platform masked, then restore.

    The secrets are read in an environment given for that alone and then forgotten: the fixture
    leaves none in the process, where a ``served_settings()`` of the Keycloak tests would read the
    false secret of the service account, which Keycloak refuses (#935).
    """
    with pytest.MonkeyPatch.context() as patch:
        for name, value in {**PLATFORM_SECRETS, **PLATFORM_ADDRESSES}.items():
            patch.setenv(name, value)
        secrets = load_service_settings().secret_values()
    with captured_logs(secrets) as logs:
        yield logs


@pytest.fixture(scope="session")
def contract() -> OpenAPI:
    """Read the interface contract, once.

    A refusal answers in ``application/problem+json``, JSON that openapi-core does not read by
    itself: without this, no refusal could be checked against its schema. A binary body, a string
    for the contract, is read as the text of its bytes by ``ContractClient`` (``support``).
    """
    config = Config(extra_media_type_deserializers={"application/problem+json": json.loads})
    return OpenAPI.from_file_path(str(CONTRACT), config=config)


@pytest.fixture
def client(contract: OpenAPI, services: Services) -> ContractClient:
    """Build a client on the application."""
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def empty_engine(database_url: str) -> Iterator[Engine]:
    """Give an engine on a database of its own, without a table."""
    with scratch_database(database_url) as engine:
        yield engine


@pytest.fixture(scope="session")
def process_database_url() -> Iterator[str]:
    """Create, for this process, a database of the PostgreSQL server the tests are given, migrated.

    ``WATERFALL_TEST_DATABASE_URL`` designates a server and a superuser, who may create databases
    and roles. Without it the tests that need a database fail and say so: PostgreSQL is the
    database of the platform, and no other stands in for it.
    """
    address = os.environ.get(TEST_DATABASE_VARIABLE)
    if not address:
        pytest.fail(
            f"{TEST_DATABASE_VARIABLE} is not set: give it the URL of a PostgreSQL server "
            "whose role is a superuser (the guide, 'Tests', says how)",
            pytrace=False,
        )
    name = f"waterfall_test_{uuid4().hex}"
    server = create_database_engine(address).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = engine_url(address).set(database=name).render_as_string(hide_password=False)
    engine = create_database_engine(url)
    upgrade(engine)
    engine.dispose()
    yield url
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        connection.execute(text(f'DROP ROLE IF EXISTS "{service_role(engine_url(url))}"'))
    server.dispose()


@pytest.fixture(scope="session")
def process_service_database_url(process_database_url: str) -> Iterator[str]:
    """Give the address of the database of this process as the service reaches it.

    By a role made for this process, that may sign in, member of the role of the service of the
    database and holding nothing else: what the tables do not grant the service, the tests cannot
    do either.
    """
    name, password = f"waterfall_test_{uuid4().hex}", uuid4().hex
    service = service_role(engine_url(process_database_url))
    server = create_database_engine(process_database_url).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    with server.connect() as connection:
        connection.execute(
            text(f'CREATE ROLE "{name}" LOGIN PASSWORD \'{password}\' IN ROLE "{service}"')
        )
    url = engine_url(process_database_url).set(username=name, password=password)
    yield url.render_as_string(hide_password=False)
    with server.connect() as connection:
        connection.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = :name"),
            {"name": name},
        )
        connection.execute(text(f'DROP ROLE "{name}"'))
    server.dispose()


@pytest.fixture
def database_url(request: pytest.FixtureRequest, process_database_url: str) -> Iterator[str]:
    """Give the address of the database of the test, as the superuser.

    That of the process (``process_database_url``), but for a test on the witness (``witness``,
    ``witness_logged``): a copy of the template of the witness of the run, its own, dropped after it
    (``witness_template``).
    """
    if not any(name in request.fixturenames for name in ON_THE_WITNESS):
        yield process_database_url
        return
    template = request.config.stash[TEMPLATE]
    built(template)
    with cloned(template, process_database_url) as url:
        yield url


@pytest.fixture
def service_database_url(
    request: pytest.FixtureRequest,
    database_url: str,
    process_database_url: str,
    process_service_database_url: str,
) -> str:
    """Give the address of the database of the test as the service reaches it.

    On a copy of the template of the witness, by the role that signs in on its copies, member of the
    role of the service of the template alone, whose rights the copy keeps.
    """
    if database_url == process_database_url:
        return process_service_database_url
    return request.config.stash[TEMPLATE].as_service(database_url)


@pytest.fixture(scope="session")
def backup_role(process_database_url: str) -> Iterator[tuple[str, str]]:
    """Create, for this run, a role of the backup as the platform does (#895): its name, password.

    A member of ``pg_read_all_data``, which reads every table of every database of the server and
    can neither write nor turn a trigger off; it owns nothing.
    """
    name, password = f"waterfall_test_backup_{uuid4().hex}", uuid4().hex
    server = create_database_engine(process_database_url).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    with server.connect() as connection:
        connection.execute(
            text(f"CREATE ROLE \"{name}\" LOGIN PASSWORD '{password}' IN ROLE pg_read_all_data")
        )
    yield name, password
    with server.connect() as connection:
        connection.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = :name"),
            {"name": name},
        )
        connection.execute(text(f'DROP ROLE "{name}"'))
    server.dispose()


@pytest.fixture
def database(
    database_url: str, process_database_url: str, service_database_url: str
) -> Iterator[Database]:
    """Give the migrated database of the test as the service sees it, emptied afterwards.

    A copy of the template of the witness goes with the test (``database_url``). The database of
    the process is emptied of every row: those of every table the code declares are deleted by the
    owner, the journal of audit included — its triggers, which refuse any deletion, are off for
    that transaction alone, what only a superuser may do, and the service never. A table the
    migrations fill — the catalogue of permissions — keeps its rows, as an installation does, and a
    schedule is written back at its shipped values (``empty_database``).

    The partitions a project brings with it (WF-DAT-0050) outlive its rows, and a creation refuses
    a project that has its partitions: dropped first, project after project, a transaction each,
    so that no transaction holds the locks of them all (#4051).
    """
    db = Database(create_database_engine(service_database_url))
    yield db
    db.dispose()
    if database_url != process_database_url:
        return
    owner = create_database_engine(database_url)
    drop_every_partition(owner)
    with owner.begin() as connection:
        # The guards of the journal and of the revised tables off for this transaction alone.
        unguarded(connection)
        empty_database(connection)
    owner.dispose()


@pytest.fixture
def owner(database_url: str) -> Iterator[Engine]:
    """Give an engine of the owner of the tables, on the database the service sees.

    What the service may not do — delete an account, change the journal — a test does around it,
    through the owner.
    """
    engine = create_database_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(database: Database) -> Iterator[Session]:
    """Give a session whose work is rolled back at the end of the test."""
    with Session(database.engine) as opened:
        yield opened
        opened.rollback()


TEST_REDIS_VARIABLE = "WATERFALL_TEST_REDIS_URL"
# The databases a Redis has by default (`databases` in its configuration).
REDIS_DATABASES = 16


@pytest.fixture(scope="session")
def redis_url(worker_id: str) -> str:
    """Give the Redis of the tests, which they alone use; without it, a test that needs it fails.

    The tests run on several processes (pytest-xdist), each a session of its own: each takes the
    database of Redis that follows the one given by its rank, so that the queue every installation
    uses (``platform_queue``) is never emptied by one under another's feet.
    """
    address = os.environ.get(TEST_REDIS_VARIABLE)
    if not address:
        pytest.fail(
            f"{TEST_REDIS_VARIABLE} is not set: give it the URL of a Redis the tests may write to "
            "(the guide, 'Tests', says how)",
            pytrace=False,
        )
    if worker_id == "master":
        return address
    parts = urlsplit(address)
    index = int(parts.path.strip("/") or 0) + int(worker_id.removeprefix("gw"))
    if index >= REDIS_DATABASES:
        pytest.fail(
            f"worker {worker_id} would take database {index} of Redis, which has "
            f"{REDIS_DATABASES}: run fewer workers (-n)",
            pytrace=False,
        )
    return urlunsplit(parts._replace(path=f"/{index}"))


@pytest.fixture
def queue(redis_url: str) -> Iterator[TaskQueue]:
    """Give a queue of tasks on the Redis of the tests, in a stream of its own, deleted after.

    It waits for Redis as the worker's does, which the tests run on it. The stream of the
    restorations beside it is deleted with it.
    """
    opened = TaskQueue.connect(redis_url, f"waterfall:test:{uuid4().hex}", timeout=WORKER_TIMEOUT)
    yield opened
    opened.client.delete(opened.stream, opened.stream + RESTORES)
    opened.close()


@pytest.fixture
def platform_queue(redis_url: str) -> Iterator[TaskQueue]:
    """Give the queue every installation uses, on the Redis of the tests, emptied around a test."""
    opened = TaskQueue.connect(redis_url, timeout=WORKER_TIMEOUT)
    opened.client.delete(opened.stream)
    yield opened
    opened.client.delete(opened.stream)
    opened.close()


# How many processes run the tests at most, each on a database of Redis of its own (``Makefile``,
# ``--maxprocesses``).
REDIS_WORKERS = 8


@pytest.fixture
def emptied_queue(redis_url: str, worker_id: str) -> Iterator[TaskQueue]:
    """Give a queue on a database of the Redis of the tests that no worker takes, emptied after.

    The workers take the databases that follow the one given, eight at most: the eighth after
    the worker's own is the test's, whichever worker it runs on, and ``FLUSHDB`` empties nothing
    another test reads. That holds for eight processes at most, as the ``Makefile`` runs them
    (``--maxprocesses``): beyond, the database emptied could be a worker's own, so the test fails
    rather than empty it.
    """
    rank = int(worker_id.removeprefix("gw")) if worker_id != "master" else 0
    if rank >= REDIS_WORKERS:
        pytest.fail(
            f"worker {worker_id} would empty the database of another worker: this test is for "
            f"{REDIS_WORKERS} processes at most (-n {REDIS_WORKERS} or fewer)",
            pytrace=False,
        )
    parts = urlsplit(redis_url)
    index = (int(parts.path.strip("/") or 0) + REDIS_WORKERS) % REDIS_DATABASES
    opened = TaskQueue.connect(urlunsplit(parts._replace(path=f"/{index}")), timeout=WORKER_TIMEOUT)
    yield opened
    emptied(opened)
    opened.close()


@pytest.fixture
def service_environment(service_database_url: str, redis_url: str) -> dict[str, str]:
    """Give a process of the platform the database of the tests, as the service, and their Redis."""
    return {"WATERFALL_DATABASE_URL": service_database_url, "WATERFALL_REDIS_URL": redis_url}


TEST_STORAGE_VARIABLE = "WATERFALL_TEST_STORAGE_URL"


def _bucket_of_tests() -> Iterator[Bucket]:
    """Create a bucket on the object storage of the tests, emptied and deleted after its use."""
    address = os.environ.get(TEST_STORAGE_VARIABLE)
    if not address:
        pytest.fail(
            f"{TEST_STORAGE_VARIABLE} is not set: give it the URL of an object storage and of a "
            "key that may create buckets (the guide, 'Tests', says how)",
            pytrace=False,
        )
    parts = urlsplit(address)
    endpoint = f"{parts.scheme}://{parts.hostname}:{parts.port}"
    name = f"waterfall-test-{uuid4().hex}"
    bucket = Bucket.connect(name, endpoint, "us-east-1", parts.username or "", parts.password or "")
    bucket.client.create_bucket(Bucket=name)
    yield bucket
    for listed in bucket.client.list_objects_v2(Bucket=name).get("Contents", []):
        bucket.client.delete_object(Bucket=name, Key=listed.get("Key", ""))
    bucket.client.delete_bucket(Bucket=name)


@pytest.fixture(scope="session")
def backups_bucket() -> Iterator[Bucket]:
    """Give a bucket of its own on the object storage of the tests, emptied and deleted after them.

    ``WATERFALL_TEST_STORAGE_URL`` designates the storage and the key of the tests, as
    ``http://<key>:<secret>@<host>:<port>``; without it, a test that needs the storage fails and
    says so: no other stands in for it. The bucket is shared by the tests of a worker.
    """
    yield from _bucket_of_tests()


@pytest.fixture
def private_bucket() -> Iterator[Bucket]:
    """Give a bucket for one test alone, for an assertion on all of what a bucket holds."""
    yield from _bucket_of_tests()


@pytest.fixture
def installation(
    database_url: str, backup_role: tuple[str, str], backups_bucket: Bucket
) -> Iterator[Installation]:
    """Give an installation of its own, dropped after the test (``installations``)."""
    yield from installed(database_url, backup_role, backups_bucket)


@pytest.fixture
def take(installation: Installation, queue: TaskQueue) -> Take:
    """Give a taker of backups: a backup deposited as a request does, then run by a worker."""
    return taker(installation, queue)


@pytest.fixture
def installation_api(
    installation: Installation,
    queue: TaskQueue,
    contract: OpenAPI,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
) -> ContractClient:
    """Serve the API on an installation, as the role of the service, the maintenance in it."""
    services = Services(
        installation.database,
        keycloak,
        KeycloakAdmin(keycloak, realm_settings),
        queue,
        installation.bucket,
        Maintenance.of(installation.database, queue),
    )
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def witness(database: Database) -> Database:
    """Give the database of the test, a copy of the template of the witness of the run; its own.

    The template is the database installed as the bootstrap does, the witness loaded by the command
    (``witness_template``): the row of the installation and the reference the bootstrap writes — the
    settings, the units, the mapping, the default calendar, the provision —, as the owner of the
    tables, then the witness as the service (#2143): the slices that set what the bootstrap wrote
    have it to set. Dropped after the test (``database_url``). A test that reads what the command
    says asks for ``witness_logged``, one that changes how the command loads it for
    ``witness_loaded``.
    """
    return database


@pytest.fixture
def witness_logged(database: Database, request: pytest.FixtureRequest, logs: Logs) -> Database:
    """Give the witness and, in ``logs``, the records the command wrote when it loaded it.

    Those of the loading of the template: the command, the description and the platform are the
    same for every test, so are its records, which say it loaded the witness — a loading that says
    otherwise fails, and the template with it.
    """
    logs.stream.write(built(request.config.stash[TEMPLATE]))
    return database


@pytest.fixture
def witness_loaded(database: Database, owner: Engine, service_database_url: str) -> Database:
    """Give the database the witness was loaded on by the command in this very test.

    For a test that changes how the command loads it, a filler registered for instance: one that
    only reads what the command says asks for ``witness_logged``. Its loading is never shared: a
    modified one would be the witness the other tests are given.
    """
    install(owner)
    settings = WitnessSettings(
        database_url=SecretStr(service_database_url), witness_path=str(WITNESS)
    )
    assert load_witness(settings) == 0
    return database


@pytest.fixture
def reference_sessions(database: Database, realm: TestRealm) -> ReferenceSessions:
    """Give a maker of the three sessions of a part of the reference, each its own account.

    The part is named as its permissions are (``cost_settings``): without any permission of the
    reference, with the permission to read it, with those to read and to change it.
    """

    def holding(*permissions: str) -> dict[str, str]:
        account = raw_account(email=f"{uuid4().hex}@example.org")
        held = role(database, f"Rôle {uuid4().hex}", permissions=permissions)
        with database.transaction() as session:
            session.execute(insert(UserAccount).values(**account))
            session.execute(
                insert(UserAccessRole).values(user_account_id=account["id"], access_role_id=held)
            )
        return bearer(realm.token(str(account["idp_subject"]), KEY))

    def sessions(part: str) -> PartSessions:
        assert part in REFERENCE_PARTS, part
        read, write = f"{part}.read", f"{part}.write"
        return PartSessions(holding(), holding(read), holding(read, write))

    return sessions


@pytest.fixture(scope="session")
def provider_url(process_database_url: str) -> Iterator[str]:
    """Create, for this run, a database that stands for the identity provider's, with a realm."""
    name = f"waterfall_test_idp_{uuid4().hex}"
    server = create_database_engine(process_database_url).execution_options(
        isolation_level="AUTOCOMMIT"
    )
    with server.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = engine_url(process_database_url).set(database=name).render_as_string(hide_password=False)
    provider = create_database_engine(url)
    with provider.begin() as connection:
        stand_in_realm(connection)
    provider.dispose()
    yield url
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    server.dispose()


@pytest.fixture
def databases(database_url: str, provider_url: str, backup_role: tuple[str, str]) -> dict[str, str]:
    """Give the two databases of the test as the role of the backup reaches them, by backup name."""
    return {
        "waterfall": as_backup(database_url, backup_role),
        "identity_provider": as_backup(provider_url, backup_role),
    }


@pytest.fixture
def run(database: Database, queue: TaskQueue) -> Run:
    """Give a runner: it deposits a backup the platform asks for, which a worker then takes."""

    def backup(taking: BackupTask) -> UUID:
        task_id = deposit(database, queue, "backup")
        assert worker_of(database, queue, taking).step()
        return task_id

    return backup
