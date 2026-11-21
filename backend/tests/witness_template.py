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
"""

import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast
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
    from collections.abc import Generator

    from sqlalchemy import Engine

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
# The end of what the loading said, given with the failure of a test that waited for it.
_TAIL = 4000


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


# The loadings this process started, awaited at its end (``finished``).
_STARTED_HERE: list[subprocess.Popen[bytes]] = []
# The records of the loading, by the directory of the template, once it has ended.
_RECORDS_READ: dict[Path, str] = {}


def start(template: Template) -> None:
    """Start the loading of the template, unless a process of the run has already started it.

    The process that loads holds the exclusive lock of ``build.lock`` from before it starts: taken
    here, then handed to it, it is released when it ends, however it ends.
    """
    with _locked(template.directory / _START_LOCK, fcntl.LOCK_EX):
        started = template.directory / _STARTED
        if started.exists():
            return
        descriptor = os.open(template.directory / _BUILD_LOCK, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            with (template.directory / _LOG).open("wb") as log:
                loading = subprocess.Popen(
                    [sys.executable, __file__, str(template.directory)],
                    pass_fds=(descriptor,),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            _STARTED_HERE.append(loading)
        finally:
            os.close(descriptor)
        started.touch()


def built(template: Template) -> str:
    """Wait for the template, started if no process has started it yet; give the loading's records.

    A loading that failed fails the test that waits for it, with what it said.
    """
    held = _RECORDS_READ.get(template.directory)
    if held is not None:
        return held
    start(template)
    with _locked(template.directory / _BUILD_LOCK, fcntl.LOCK_SH):
        pass
    records = template.directory / _RECORDS
    if not records.exists():
        said = (template.directory / _LOG).read_text("utf-8", errors="replace")[-_TAIL:]
        pytest.fail(f"the template of the witness was not loaded; the loading said:\n{said}")
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
            connection.execute(text(f'CREATE DATABASE "{name}" TEMPLATE "{template.name}"'))
        try:
            yield template.owned(address, name)
        finally:
            with server.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    finally:
        server.dispose()


def finished() -> None:
    """Wait for the loadings this process started: one ends with the run that needs it."""
    while _STARTED_HERE:
        _STARTED_HERE.pop().wait()


def dropped(template: Template, address: str | None) -> None:
    """Drop the template, its copies a test left, its roles and its directory, the loading ended."""
    if address is not None and (template.directory / _STARTED).exists():
        with _locked(template.directory / _BUILD_LOCK, fcntl.LOCK_SH):
            pass
        server = _server(address)
        with server.connect() as connection:
            found = connection.scalars(
                text("SELECT datname FROM pg_database WHERE starts_with(datname::text, :name)"),
                {"name": template.name},
            ).all()
            # The copies first: the roles go with the last of the rights they hold.
            for name in sorted(found, key=lambda each: each == template.name):
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{template.signing}"'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{template.service}"'))
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
            connection.execute(text(f'CREATE DATABASE "{template.name}"'))
        owner = create_database_engine(template.owned(address, template.name))
        upgrade(owner)
        with server.connect() as connection:
            connection.execute(
                text(
                    f"CREATE ROLE \"{template.signing}\" LOGIN PASSWORD '{template.password}' "
                    f'IN ROLE "{template.service}"'
                )
            )
        service = template.as_service(template.owned(address, template.name))
        settings = WitnessSettings(database_url=SecretStr(service), witness_path=str(WITNESS))
        with pytest.MonkeyPatch.context() as patch, recorded_logs() as records:
            pin_year(patch)
            TIME_ZONE.read_from(lambda: DELIVERED_TIME_ZONE)
            install(owner)
            status = load_witness(settings)
        owner.dispose()
        said = records.getvalue()
        if status != 0 or not said_loaded(said):
            message = f"the command ended with {status}, saying:\n{said}"
            raise RuntimeError(message)
        with server.connect() as connection:
            connection.execute(
                text(f'ALTER DATABASE "{template.name}" WITH ALLOW_CONNECTIONS false')
            )
    finally:
        server.dispose()
    return said


def main() -> None:
    """Load the template whose directory is given, and write its records there once it is loaded.

    Warnings are errors, as in the tests (``filterwarnings``). The records are written whole or not
    at all: a test that finds none says the loading failed.
    """
    warnings.simplefilter("error")
    template = Template.read(Path(sys.argv[1]))
    said = load(template, os.environ[TEST_DATABASE_VARIABLE])
    written = template.directory / f"{_RECORDS}.part"
    written.write_text(said, encoding="utf-8")
    written.replace(template.directory / _RECORDS)


if __name__ == "__main__":
    main()
