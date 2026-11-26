# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The template of the witness: a copy of its own for each test, a loading that fails or freezes.

A detail of how the tests run (``witness_template``), which covers no requirement: none is cited.
The loadings that fail, freeze or die are commands of a few lines in place of the loader, given the
deadline of a test; only the deadline of the loader itself takes the real one.
"""

import signal
import sys
import time
from typing import TYPE_CHECKING

import pytest
from loading_watcher import EXIT, NOT_STARTED
from project_rows import unguarded
from sqlalchemy import Engine, delete, func, select, text
from witness_template import (
    ENDED,
    LOADING_TIMEOUT,
    TEMPLATE,
    TOOK,
    Template,
    built,
    cloned,
    dropped,
    quoted,
    recorded,
    said_loaded,
    start,
    took,
)

from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database, create_database_engine

if TYPE_CHECKING:
    from collections.abc import Iterator

    from waterfall.platform.settings import WitnessSettings

# A loader that says why it fails, then fails.
FAILING = (sys.executable, "-c", "print('the loader broke'); raise SystemExit(1)")
# A loader that says it sleeps, then sleeps past any deadline of these tests.
FROZEN = (sys.executable, "-c", "import time; print('asleep', flush=True); time.sleep(600)")
# A loader that is killed from outside, having said nothing (the memory of a runner, an operator).
KILLED = (sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)")
# A loader that the system ends at its deadline, having said nothing (``SIGALRM``, as the real one).
ALARMED = (
    sys.executable,
    "-c",
    "import signal; signal.signal(signal.SIGALRM, signal.SIG_DFL); signal.alarm(1); signal.pause()",
)
# A loader that ends at once, having loaded nothing.
IDLE = (sys.executable, "-c", "")
# A loader that says how long it took and that it wrote its records, then fails all the same.
ENDED_THEN_FAILING = (
    sys.executable,
    "-c",
    f"print('{TOOK} 3 s'); print('{ENDED}'); raise SystemExit(1)",
)


@pytest.fixture
def planned() -> Iterator[Template]:
    """Give a template of its own, apart from that of the run, its directory removed after."""
    template = Template.planned()
    yield template
    dropped(template, None)


def server(address: str) -> Engine:
    """Give the server of ``address``, as its superuser, outside any transaction."""
    return create_database_engine(address).execution_options(isolation_level="AUTOCOMMIT")


def left(template: Template, address: str) -> tuple[list[str], list[str]]:
    """Give the databases and the roles of the server that bear the name of the template."""
    engine = server(address)
    with engine.connect() as connection:
        databases = connection.scalars(
            text("SELECT datname FROM pg_database WHERE starts_with(datname::text, :name)"),
            {"name": template.name},
        ).all()
        roles = connection.scalars(
            text("SELECT rolname FROM pg_roles WHERE starts_with(rolname::text, :name)"),
            {"name": template.name},
        ).all()
    engine.dispose()
    return list(databases), list(roles)


def silent(_settings: WitnessSettings) -> int:
    """End as the command that loads the witness does when it succeeds, without saying it did."""
    return 0


def unpinned(_patch: pytest.MonkeyPatch) -> None:
    """Pin no clock: the ones ``pinned_year`` set stay in place."""


def accounts(engine: Engine) -> int:
    """Count the accounts of a database."""
    with engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(UserAccount)) or 0


def emptied(engine: Engine) -> None:
    """Delete every account of a database, the keys that name them off, as its owner."""
    with engine.begin() as connection:
        unguarded(connection)
        connection.execute(delete(UserAccount))


@pytest.mark.parametrize("turn", [1, 2])
def test_each_test_on_the_witness_finds_what_another_destroyed(
    turn: int, witness: Database, owner: Engine
) -> None:
    """Each of the two tests empties a table of the witness: the other finds it whole all along."""
    assert witness.engine.url.database == owner.url.database, turn
    assert accounts(owner) > 0
    emptied(owner)
    assert accounts(owner) == 0


@pytest.mark.usefixtures("witness")
def test_a_copy_of_the_template_is_its_own_and_is_dropped_after(
    request: pytest.FixtureRequest, owner: Engine, process_database_url: str
) -> None:
    """A copy made after a test changed its own has the witness whole, and is gone once done."""
    template = request.config.stash[TEMPLATE]
    whole = accounts(owner)
    emptied(owner)
    with cloned(template, process_database_url) as address:
        copy = create_database_engine(address)
        assert accounts(copy) == whole > 0
        copy.dispose()
        name = copy.url.database
        assert name in left(template, process_database_url)[0]
    assert name not in left(template, process_database_url)[0]
    assert owner.url.database in left(template, process_database_url)[0]


def test_a_loading_that_fails_fails_the_test_that_waits_with_what_it_said(
    planned: Template,
) -> None:
    """The test that waits for a loading that failed fails, given what the loading said."""
    loading = start(planned, FAILING)
    assert loading is not None
    with pytest.raises(pytest.fail.Exception, match=r"was not loaded; the loading said:\n.*broke"):
        built(planned)
    assert loading.ended() == 1
    assert start(planned, FAILING) is None, "a template is loaded once, failed or not"


def test_a_loader_that_does_not_start_fails_the_test_that_waits_with_the_reason(
    planned: Template,
) -> None:
    """A loader the system cannot run is written in the log, and fails the test that waits."""
    loading = start(planned, ["/nonexistent"])
    assert loading is not None
    with pytest.raises(pytest.fail.Exception, match=r"the loader did not start: .*nonexistent"):
        built(planned)
    assert loading.ended() == NOT_STARTED


def test_a_loading_killed_without_a_word_says_so_to_the_test_that_waits(
    planned: Template,
) -> None:
    """The message is never empty: a loading killed before its deadline is named by its signal."""
    loading = start(planned, KILLED)
    assert loading is not None
    with pytest.raises(pytest.fail.Exception, match=r"(?s)was not loaded; .*killed \(SIGKILL\)"):
        built(planned)
    assert loading.ended() == -signal.SIGKILL


def test_a_loading_ended_by_its_alarm_says_it_lasted_past_its_deadline(
    planned: Template,
) -> None:
    """The loading the system ended at its deadline, silent, is named by its signal (SIGALRM)."""
    loading = start(planned, ALARMED, timeout=1)
    assert loading is not None
    assert loading.process.wait(timeout=30) == -signal.SIGALRM
    with pytest.raises(pytest.fail.Exception, match=r"ended by the system at its deadline"):
        built(planned)
    assert (planned.directory / EXIT).read_text("utf-8") == str(-signal.SIGALRM)
    assert sorted(each.name for each in planned.directory.glob(f"{EXIT}*")) == [EXIT]


@pytest.mark.parametrize("written", ["", "not a status"], ids=["empty", "unreadable"])
def test_the_end_of_a_loading_whose_exit_is_not_a_status_is_said_without_failing(
    planned: Template, written: str
) -> None:
    """The ``exit`` the watcher did not finish, read at the deadline, names no status, no error."""
    loading = start(planned, IDLE)
    assert loading is not None
    assert loading.ended() == 0
    (planned.directory / EXIT).write_text(written, encoding="utf-8")
    with pytest.raises(pytest.fail.Exception, match=r"(?s)was not loaded; .*did not say"):
        built(planned)


def test_a_loading_that_said_it_ended_is_not_given_a_cause_when_it_fails(
    planned: Template,
) -> None:
    """A log that says the loading wrote its records is given as it is: it names no cause."""
    loading = start(planned, ENDED_THEN_FAILING)
    assert loading is not None
    with pytest.raises(pytest.fail.Exception, match=ENDED) as failed:
        built(planned)
    assert "[the loading" not in str(failed.value)
    assert loading.ended() == 1


def test_the_duration_the_loading_said_is_given_to_the_end_of_the_run(
    planned: Template,
) -> None:
    """The line by which the loading says how long it took is read back; none before it runs."""
    assert took(planned) is None
    loading = start(planned, ENDED_THEN_FAILING)
    assert loading is not None
    assert loading.ended() == 1
    assert took(planned) == f"{TOOK} 3 s"


def test_a_loading_past_its_deadline_fails_the_test_that_waits_and_is_killed(
    planned: Template,
) -> None:
    """A loading that freezes fails the test by its deadline, with what it said, then is killed."""
    began = time.monotonic()
    loading = start(planned, FROZEN, timeout=2)
    assert loading is not None
    with pytest.raises(pytest.fail.Exception, match="by its deadline; the loading said:\nasleep"):
        built(planned)
    assert time.monotonic() - began < 30
    assert loading.ended() == -signal.SIGKILL
    assert time.monotonic() - began < 30


def test_the_loader_ends_itself_at_its_deadline(
    planned: Template, process_database_url: str
) -> None:
    """The real loader ends at its deadline though no one kills it, writing no record.

    As when the process that started it is gone: the end of the run then drops what it left.
    """
    loading = start(planned, timeout=1)
    assert loading is not None
    assert loading.process.wait(timeout=LOADING_TIMEOUT) == -signal.SIGALRM
    assert not (planned.directory / "records").exists()
    dropped(planned, process_database_url)
    assert left(planned, process_database_url) == ([], [])


def test_dropping_after_a_dead_loading_removes_the_template_its_copies_and_roles(
    planned: Template, process_database_url: str
) -> None:
    """The end of a run drops what a loading that died left: databases, roles, directory."""
    engine = server(process_database_url)
    with engine.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {quoted(engine, planned.name)}"))
        connection.execute(text(f"CREATE DATABASE {quoted(engine, f'{planned.name}_left')}"))
        connection.execute(text(f'CREATE ROLE "{planned.service}"'))
        connection.execute(text(f'CREATE ROLE "{planned.signing}" IN ROLE "{planned.service}"'))
    engine.dispose()
    loading = start(planned, FAILING)
    assert loading is not None
    assert loading.ended() == 1
    assert left(planned, process_database_url) != ([], [])
    dropped(planned, process_database_url)
    assert left(planned, process_database_url) == ([], [])
    assert not planned.directory.exists()


def test_a_loading_whose_command_does_not_say_it_loaded_writes_no_record(
    planned: Template, process_database_url: str
) -> None:
    """A command that ends without saying it loaded the witness fails the loading: no records.

    The loading pins no clock of its own here: the ones ``pinned_year`` set are already in place.
    """
    loading = start(planned, IDLE)
    assert loading is not None
    assert loading.ended() == 0
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("witness_template.load_witness", silent)
        patch.setattr("witness_template.pin_year", unpinned)
        with pytest.raises(RuntimeError, match="the command ended with 0"):
            recorded(planned, process_database_url)
    assert not (planned.directory / "records").exists()
    dropped(planned, process_database_url)
    assert left(planned, process_database_url) == ([], [])


@pytest.mark.parametrize(
    ("records", "loaded"),
    [
        ('{"event": "witness.started"}\n{"event": "witness.loaded", "projects": 12}\n', True),
        ('{"event": "witness.started"}\nnot a record\n["witness.loaded"]\n', False),
        ("", False),
    ],
)
def test_the_records_say_whether_the_command_loaded_the_witness(
    records: str, *, loaded: bool
) -> None:
    """Only the record of the event ``witness.loaded`` says the command loaded the witness."""
    assert said_loaded(records) is loaded
