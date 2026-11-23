# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The witness loaded once by a run of the tests, in a template that each test on it copies.

Loading the witness goes through the rules of every module: some thirty thousand statements, two
minutes and more on a runner of the chain, for twelve projects and their 768 partitions (#4653).
Loaded by each process, then laid again and its partitions dropped around each test, it took a
third of the tests' time. It is now loaded once by a run, by a process of its own that the first
process whose tests ask for it starts as soon as they are collected, into a database of the
server no one connects to afterwards: the template. Each test that asks for it is given a database
of its own created from the template (``CREATE DATABASE … TEMPLATE``), dropped after it. What a
test reads is what the command wrote — rows, identifiers drawn in order, the partitions of the
projects, the state of the sequences —, and a project of the witness created again is refused as
on the platform the command loaded.

The run — the controller of pytest-xdist, or the process alone — names the template and the role
that signs in on its copies, writes them in a directory of its own, and drops them all at its end.
The loading holds an exclusive lock on ``build.lock`` (``flock``), handed to it by the process
that starts it: a test that waits for the template takes a shared one, which it gets once the
loading has ended, whether it succeeded or died, then reads its records, or what it said before
it failed.

The loading has a deadline, written when it starts (``started``): a test that waits for it past
the deadline fails with what the loading said, the loading is ended by the system then
(``SIGALRM``), and the process that started it kills it if it still runs when that process ends.
Neither a test nor the end of pytest waits for a loading that froze: the part of the chain fails,
a test named, rather than being cancelled by the deadline of its job.

The loader runs under a watcher of its own (``--watch``), which holds the lock in its place, writes
how the loader ended (``exit``: its status, or minus the signal that ended it) and ends as it did: a
test that waits reads there whether the loading failed, was ended at its deadline or was killed. The
loader writes how long it took, which the end of the run says (``took``).
"""

import fcntl
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import warnings
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, cast
from uuid import uuid4

import pytest
from estimate_support import pin_year
from installed_reference import install
from pydantic import SecretStr
from sqlalchemy import text
from support import WITNESS, recorded_logs

from waterfall.migrations.runner import upgrade
from waterfall.platform.database import create_database_engine, engine_url
from waterfall.platform.installation import DELIVERED_TIME_ZONE, TIME_ZONE
from waterfall.platform.settings import WitnessSettings
from waterfall.witness.main import load_witness

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from sqlalchemy import Connection, Engine

# The server and the superuser the tests are given (the guide, "Tests").
TEST_DATABASE_VARIABLE = "WATERFALL_TEST_DATABASE_URL"
# The key under which the controller of pytest-xdist hands its workers the template's directory.
WORKER_INPUT = "waterfall_witness_template"

_SETTINGS = "template.json"
_START_LOCK = "start.lock"
_STARTED = "started"
_BUILD_LOCK = "build.lock"
_RECORDS = "records"
_LOG = "loading.log"
_EXIT = "exit"
# The argument that runs this module as the watcher of the loader that follows it.
_WATCH = "--watch"
# What the loading writes in its log when it has loaded and recorded the template: a log that lacks
# it is that of a loading that did not end so, which the watcher's ``exit`` names.
ENDED = "the loading wrote its records"
# What the loading writes before, followed by its duration in seconds.
TOOK = "the loading took"
# The end of what the loading said, given with the failure of a test that waited for it.
_TAIL = 4000
# The seconds a loading may last. It took 134 to 290 seconds on a runner of the chain, loaded by
# each of the four processes of a part at once (#4657), a runner up to twice as slow as another. The
# own estimate of a risk is born whole, copied from the main structure at each revision (EP-30,
# US-3070/L3): the loading took 74 seconds and takes 170 on a workstation, and on a runner of the
# chain it went past the 420 seconds it was given (run 45181091842, the loading ended by its alarm
# without a word). 780 seconds leave it, at the ratio of a runner to a workstation (two to four),
# the margin of the slowest; under the fifteen minutes of a test (``timeout``, pyproject.toml), so
# that the test that waits fails with what the loading said, rather than by its own timeout.
LOADING_TIMEOUT = 780
# The seconds the end of a run waits past the deadline, for the process that started the loading to
# kill it, before it drops the template whatever still holds it.
_GRACE = 60
# The seconds the loading waits for the sessions on the template to end, before it closes it.
_ALONE = 30
# The seconds between two tries of the lock of the loading.
_POLL = 0.2


@dataclass(frozen=True)
class Template:
    """The template of a run: its directory, the name of its database, the password of its role."""

    directory: Path
    name: str
    password: str

    @classmethod
    def planned(cls) -> Template:
        """Name the template of a new run, in a directory of its own, where its workers read it."""
        directory = Path(tempfile.mkdtemp(prefix="waterfall-witness-"))
        template = cls(directory, f"waterfall_witness_{uuid4().hex[:16]}", uuid4().hex)
        settings = {"name": template.name, "password": template.password}
        (directory / _SETTINGS).write_text(json.dumps(settings), encoding="utf-8")
        return template

    @classmethod
    def read(cls, directory: Path) -> Template:
        """Read the template the run named, from its directory."""
        settings = cast("dict[str, str]", json.loads((directory / _SETTINGS).read_text("utf-8")))
        return cls(directory, settings["name"], settings["password"])

    @property
    def service(self) -> str:
        """Name the role of the service of the template, which its migrations create (0002)."""
        return f"{self.name}_service"

    @property
    def signing(self) -> str:
        """Name the role that signs in on the template's copies, member of its service's role alone.

        A copy keeps the rights its tables grant the role of the service of the template: the role
        of the service a copy would be named after (``<database>_service``) does not exist.
        """
        return f"{self.name}_signing"

    def owned(self, address: str, database: str) -> str:
        """Give the address of a database of the server, as the superuser of ``address``."""
        return engine_url(address).set(database=database).render_as_string(hide_password=False)

    def as_service(self, address: str) -> str:
        """Give the address of a copy of the template as the service reaches it."""
        url = engine_url(address).set(username=self.signing, password=self.password)
        return url.render_as_string(hide_password=False)


# The template of the run, as each process reads it (``pytest_configure``, conftest.py).
TEMPLATE = pytest.StashKey[Template]()


@contextmanager
def _locked(path: Path, operation: int) -> Generator[None]:
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, operation)
        yield
    finally:
        os.close(descriptor)


def _server(address: str) -> Engine:
    return create_database_engine(address).execution_options(isolation_level="AUTOCOMMIT")


def quoted(server: Engine, name: str) -> str:
    """Quote a name of the server as an identifier, whatever it holds."""
    return server.dialect.identifier_preparer.quote_identifier(name)


@dataclass(frozen=True)
class Loading:
    """A loading this process started, and the hour (``time.time``) past which it is killed."""

    process: subprocess.Popen[bytes]
    deadline: float

    def ended(self) -> int:
        """Wait for the loading until its deadline, kill it if it still runs; give how it ended.

        Killed, with its watcher, whose group it is in, it releases the lock of the loading: the
        tests that wait for it, and the end of the run, go on.
        """
        try:
            return self.process.wait(timeout=max(0.0, self.deadline - time.time()))
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                os.killpg(self.process.pid, signal.SIGKILL)
            return self.process.wait()


# The loadings this process started, awaited at its end (``finished``).
_STARTED_HERE: list[Loading] = []
# The records of the loading, by the directory of the template, once it has ended.
_RECORDS_READ: dict[Path, str] = {}
# The command that loads the template, given its directory: this module.
LOADER = (sys.executable, __file__)
# The command that watches the loader given after it: this module too.
_WATCHER = (sys.executable, __file__, _WATCH)


def start(
    template: Template, loader: Sequence[str] = LOADER, timeout: float = LOADING_TIMEOUT
) -> Loading | None:
    """Start the loading of the template, unless a process of the run has already started it.

    ``loader`` is the command that loads, given the directory of the template after it; ``timeout``
    the seconds it may last, its deadline written before it starts. Its watcher holds the exclusive
    lock of ``build.lock`` from before it starts: taken here, then handed to it, it is released when
    it ends, however it ends, once it has written how the loader ended. The watcher leads a group of
    its own, which the loader joins: killed, the group goes whole.
    """
    with _locked(template.directory / _START_LOCK, fcntl.LOCK_EX):
        started = template.directory / _STARTED
        if started.exists():
            return None
        deadline = time.time() + timeout
        started.write_text(json.dumps({"deadline": deadline}), encoding="utf-8")
        descriptor = os.open(template.directory / _BUILD_LOCK, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            with (template.directory / _LOG).open("wb") as log:
                try:
                    process = subprocess.Popen(
                        [*_WATCHER, *loader, str(template.directory)],
                        pass_fds=(descriptor,),
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                except OSError as error:
                    log.write(f"the loader did not start: {error}\n".encode())
                    raise
        finally:
            os.close(descriptor)
        loading = Loading(process, deadline)
        _STARTED_HERE.append(loading)
        return loading


def deadline_of(template: Template) -> float:
    """Give the hour (``time.time``) past which the loading of the template, started, has ended."""
    started = cast(
        "dict[str, float]", json.loads((template.directory / _STARTED).read_text("utf-8"))
    )
    return started["deadline"]


def _awaited(template: Template, until: float) -> bool:
    """Wait for the end of the loading, until the hour ``until``; tell whether it has ended."""
    descriptor = os.open(template.directory / _BUILD_LOCK, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                if time.time() >= until:
                    return False
                time.sleep(_POLL)
            else:
                return True
    finally:
        os.close(descriptor)


def _said(template: Template) -> str:
    """Give the end of what the loading said, and how it ended when it did not say so itself."""
    said = (template.directory / _LOG).read_text("utf-8", errors="replace")[-_TAIL:]
    if ENDED in said:
        return said
    return f"{said}\n[the loading {_how(template)}]"


def _how(template: Template) -> str:
    """Say how the loading ended, as its watcher wrote it; or that it had not ended."""
    written = template.directory / _EXIT
    if not written.exists():
        # The watcher writes before it releases the lock: without it, the loading still runs, or
        # was killed with its watcher by the process that started it.
        return "had not ended, or was killed with its watcher (SIGKILL)"
    status = int(written.read_text("utf-8"))
    if status == -signal.SIGALRM:
        return "was ended by the system at its deadline (SIGALRM): it lasted past LOADING_TIMEOUT"
    if status == -signal.SIGKILL:
        return "was killed (SIGKILL), saying nothing"
    if status < 0:
        return f"was ended by the signal {signal.Signals(-status).name}"
    return f"ended with the status {status}, no records"


def took(template: Template) -> str | None:
    """Give what the loading said of its duration, none if it did not say it (or did not run)."""
    log = template.directory / _LOG
    if not log.exists():
        return None
    said = log.read_text("utf-8", errors="replace")
    return next((line for line in said.splitlines() if line.startswith(TOOK)), None)


def built(template: Template) -> str:
    """Wait for the template, started if no process has started it yet; give the loading's records.

    A loading that failed, or has not ended by its deadline, fails the test that waits for it, with
    what it said.
    """
    held = _RECORDS_READ.get(template.directory)
    if held is not None:
        return held
    start(template)
    if not _awaited(template, deadline_of(template)):
        pytest.fail(
            "the template of the witness was not loaded by its deadline; the loading said:\n"
            + _said(template)
        )
    records = template.directory / _RECORDS
    if not records.exists():
        pytest.fail(
            f"the template of the witness was not loaded; the loading said:\n{_said(template)}"
        )
    held = records.read_text("utf-8")
    _RECORDS_READ[template.directory] = held
    return held


@contextmanager
def cloned(template: Template, address: str) -> Generator[str]:
    """Give the address of a new copy of the template, as the superuser; drop it after.

    No one is connected to the template, which refuses connections: PostgreSQL copies a database
    only then. The copy is dropped whoever is still connected to it (``FORCE``).
    """
    name = f"{template.name}_{uuid4().hex[:12]}"
    server = _server(address)
    try:
        with server.connect() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE {quoted(server, name)} "
                    f"TEMPLATE {quoted(server, template.name)}"
                )
            )
        try:
            yield template.owned(address, name)
        finally:
            with server.connect() as connection:
                connection.execute(text(f"DROP DATABASE {quoted(server, name)} WITH (FORCE)"))
    finally:
        server.dispose()


def finished() -> None:
    """Wait for the loadings this process started, until their deadline: one ends with the run."""
    while _STARTED_HERE:
        _STARTED_HERE.pop().ended()


def dropped(template: Template, address: str | None) -> None:
    """Drop the template, its copies a test left, its roles and its directory, the loading ended.

    A loading still running a while past its deadline — the process that started it gone without
    killing it — is not waited for further: its connections go with the databases (``FORCE``).
    """
    if address is not None and (template.directory / _STARTED).exists():
        _awaited(template, deadline_of(template) + _GRACE)
        server = _server(address)
        with server.connect() as connection:
            found = connection.scalars(
                text("SELECT datname FROM pg_database WHERE starts_with(datname::text, :name)"),
                {"name": template.name},
            ).all()
            # The copies first: the roles go with the last of the rights they hold.
            for name in sorted(found, key=lambda each: each == template.name):
                connection.execute(text(f"DROP DATABASE {quoted(server, name)} WITH (FORCE)"))
            for role in (template.signing, template.service):
                connection.execute(text(f"DROP ROLE IF EXISTS {quoted(server, role)}"))
        server.dispose()
    shutil.rmtree(template.directory, ignore_errors=True)


def said_loaded(records: str) -> bool:
    """Tell whether records hold the one that says the command loaded the witness."""
    for line in records.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and cast("dict[str, object]", record).get("event") == (
            "witness.loaded"
        ):
            return True
    return False


def _alone(connection: Connection, name: str) -> None:
    """Wait until no session is left on the database ``name``, which a copy of it requires.

    The engines are disposed, but the server ends a session a moment after its client closed it.
    """
    until = time.monotonic() + _ALONE
    while connection.scalar(
        text("SELECT count(*) FROM pg_stat_activity WHERE datname = :name"), {"name": name}
    ):
        if time.monotonic() >= until:
            message = f"sessions are still open on the template {name} after {_ALONE} seconds"
            raise RuntimeError(message)
        time.sleep(_POLL)


def load(template: Template, address: str) -> str:
    """Create the template, migrated, installed, the witness loaded; give the command's records.

    The row of the installation and the reference the bootstrap writes as the owner of the tables,
    then the witness as the service (#2143), as the fixture ``witness`` did in each process; the
    clocks pinned to the year of the tests and the time zone of the installation universal, as
    every test has them (``pinned_year``, ``installation_time_zone``).
    """
    server = _server(address)
    try:
        with server.connect() as connection:
            connection.execute(text(f"CREATE DATABASE {quoted(server, template.name)}"))
        owner = create_database_engine(template.owned(address, template.name))
        try:
            upgrade(owner)
            with server.connect() as connection:
                connection.execute(
                    text(
                        f"CREATE ROLE {quoted(server, template.signing)} "
                        f"LOGIN PASSWORD '{template.password}' "
                        f"IN ROLE {quoted(server, template.service)}"
                    )
                )
            service = template.as_service(template.owned(address, template.name))
            settings = WitnessSettings(database_url=SecretStr(service), witness_path=str(WITNESS))
            with pytest.MonkeyPatch.context() as patch, recorded_logs() as records:
                pin_year(patch)
                TIME_ZONE.read_from(lambda: DELIVERED_TIME_ZONE)
                install(owner)
                status = load_witness(settings)
        finally:
            owner.dispose()
        said = records.getvalue()
        if status != 0 or not said_loaded(said):
            message = f"the command ended with {status}, saying:\n{said}"
            raise RuntimeError(message)
        with server.connect() as connection:
            _alone(connection, template.name)
            connection.execute(
                text(f"ALTER DATABASE {quoted(server, template.name)} WITH ALLOW_CONNECTIONS false")
            )
    finally:
        server.dispose()
    return said


def recorded(template: Template, address: str) -> None:
    """Load the template, then write the records of its loading in its directory.

    The records are written whole or not at all: a test that finds none says the loading failed.
    """
    said = load(template, address)
    written = template.directory / f"{_RECORDS}.part"
    written.write_text(said, encoding="utf-8")
    written.replace(template.directory / _RECORDS)


def watch(loader: Sequence[str]) -> NoReturn:
    """Run the loader, write how it ended in the directory of the template, then end as it did.

    ``loader`` ends with that directory. The watcher holds the lock of the loading, which the loader
    is not handed: it is released once ``exit`` is written. A loader that cannot start is said in
    the log, its status 127, as a shell says it.
    """
    directory = Path(loader[-1])
    try:
        status = subprocess.call(loader, stdin=subprocess.DEVNULL)
    except OSError as error:
        sys.stdout.write(f"the loader did not start: {error}\n")
        sys.stdout.flush()
        status = 127
    (directory / _EXIT).write_text(str(status), encoding="utf-8")
    if status < 0:
        if -status != signal.SIGKILL:
            signal.signal(-status, signal.SIG_DFL)
        os.kill(os.getpid(), -status)
    raise SystemExit(status)


def main() -> None:
    """Load the template whose directory is given, and write its records there once it is loaded.

    Or, given ``--watch`` and a loader, watch it (``watch``). Warnings are errors, as in the tests
    (``filterwarnings``). Past its deadline the process is ended by the system (``SIGALRM``, whose
    default action ends it wherever it stands), even when the process that started it is gone. It
    says how long it took: the end of the run says it again (``took``).
    """
    if sys.argv[1] == _WATCH:
        watch(sys.argv[2:])
    warnings.simplefilter("error")
    template = Template.read(Path(sys.argv[1]))
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(max(1, math.ceil(deadline_of(template) - time.time())))
    sys.stdout.write(f"the loading started, its deadline {deadline_of(template):.0f}\n")
    sys.stdout.flush()
    began = time.monotonic()
    recorded(template, os.environ[TEST_DATABASE_VARIABLE])
    sys.stdout.write(f"{TOOK} {time.monotonic() - began:.0f} s\n{ENDED}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
