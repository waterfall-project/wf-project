# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The project managers in the journal, the contributors stamped: migration 0056 (US-2980/L1).

The migration stamps the contributors already there, admits the three actions and the contributor
as an object, and lets the label of a contributor be forgotten with its account; its descent
refuses them again, and fails while the journal holds one. Its upgrade leaves its indexes valid and
its checks validated, runs again over an index a stopped run left invalid, and lets the journal be
written behind a reading of it that lasts.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from project_rows import insert_project
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import DBAPIError
from support import RefusalClock, raw_account

from waterfall.core.users.tables import UserAccount
from waterfall.migrations.runner import downgrade, upgrade
from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Connection, Engine

MOMENT = datetime(2026, 11, 19, tzinfo=UTC)
CLOCK = text("SELECT clock_timestamp()")
VERSION = text("SELECT version_num FROM alembic_version")


def an_account(connection: Connection, *, anonymized: bool = False) -> UUID:
    """Write an account, named or anonymised, and give its identifier."""
    columns: dict[str, object] = (
        {
            "first_name": None,
            "last_name": None,
            "email": None,
            "state": "deactivated",
            "anonymized_at": MOMENT,
        }
        if anonymized
        else {"email": f"{uuid4().hex}@example.org"}
    )
    row = raw_account(**columns)
    connection.execute(insert(UserAccount).values(**row))
    return UUID(str(row["id"]))


def an_entry(connection: Connection, action: str, kind: str, object_id: UUID) -> UUID:
    """Inscribe a line of the journal, labelled, and give its identifier."""
    entry = uuid4()
    connection.execute(
        insert(AuditEntry).values(
            id=entry,
            occurred_at=MOMENT,
            action=action,
            object_kind=kind,
            object_id=object_id,
            object_label="Inès Roux",
            params={},
            correlation_id="managers",
        )
    )
    return entry


@pytest.mark.requirement("WF-DAT-0070-A")
def test_a_contributor_there_before_the_migration_is_dated_by_it_and_written_by_the_platform(
    empty_engine: Engine,
) -> None:
    # The columns of audit of a contributor (#3988): a line inscribed before them is dated by the
    # migration, its authors null — the platform —, no one knowing who wrote it.
    upgrade(empty_engine, "0055")
    project = uuid4()
    with empty_engine.begin() as connection:
        user = an_account(connection)
        connection.execute(insert_project(id=project))
        connection.execute(
            text(
                "INSERT INTO contributor (project_id, user_account_id, kind) "
                "VALUES (:project, :user, 'project_manager')"
            ),
            {"project": project, "user": user},
        )
    with empty_engine.connect() as connection:
        before = connection.scalar(CLOCK)
    upgrade(empty_engine, "0056")
    with empty_engine.connect() as connection:
        after = connection.scalar(CLOCK)
        row = (
            connection.execute(
                text(
                    "SELECT kind, created_at, created_by, updated_at, updated_by FROM contributor "
                    "WHERE project_id = :project AND user_account_id = :user"
                ),
                {"project": project, "user": user},
            )
            .mappings()
            .one()
        )
    assert before is not None
    assert after is not None
    assert row["kind"] == "project_manager"
    assert before <= row["created_at"] <= after
    assert row["updated_at"] == row["created_at"]
    assert (row["created_by"], row["updated_by"]) == (None, None)


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize(
    ("action", "kind", "refused"),
    [
        ("project_manager_add", "project", "action_known"),
        ("project_manager_remove", "project", "action_known"),
        ("project_manager_change", "project", "action_known"),
        ("project_exit", "contributor", "object_kind_known"),
    ],
)
def test_the_descent_fails_while_the_journal_holds_a_project_manager_or_a_contributor(
    empty_engine: Engine, action: str, kind: str, refused: str
) -> None:
    # The journal is never deleted nor rewritten: a descent that refused again what it holds would
    # make it lie; it fails, and the schema stays at 0056 with the line.
    upgrade(empty_engine, "0056")
    with empty_engine.begin() as connection:
        an_entry(connection, action, kind, an_account(connection))
    with pytest.raises(DBAPIError, match=refused):
        downgrade(empty_engine, "0055")
    with empty_engine.connect() as connection:
        assert connection.scalar(VERSION) == "0056"
        assert connection.scalar(select(func.count()).select_from(AuditEntry)) == 1
        columns = connection.scalars(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'contributor' AND column_name LIKE '%\\_by'"
            )
        )
        assert sorted(columns) == ["created_by", "updated_by"]


def forget(connection: Connection, entry: UUID) -> None:
    """Make null the label of a line of the journal, as the anonymisation of its account does."""
    connection.execute(update(AuditEntry).where(AuditEntry.id == entry).values(object_label=None))


def labels(engine: Engine) -> dict[str, str | None]:
    """Read the label of each line of the journal, by the nature of its object."""
    with engine.connect() as connection:
        rows = connection.execute(select(AuditEntry.object_kind, AuditEntry.object_label)).all()
    return {row.object_kind: row.object_label for row in rows}


@pytest.mark.requirement("WF-SEC-0030-A")
def test_after_the_descent_the_triggers_refuse_again_to_forget_the_label_of_a_contributor(
    empty_engine: Engine,
) -> None:
    # At 0056 the label of a contributor whose account is anonymised may be forgotten
    # (WF-ADM-0060, test_contributors); after the descent the triggers of 0011 forget the label of
    # an account alone. The checks of 0055 refuse a contributor before any trigger: they are
    # dropped here, so that the triggers alone answer, for an account and for a contributor.
    upgrade(empty_engine, "0056")
    downgrade(empty_engine, "0055")
    with empty_engine.begin() as connection:
        for name in ("object_kind_known", "object_labeled"):
            connection.execute(
                text(f"ALTER TABLE audit_entry DROP CONSTRAINT ck_audit_entry_{name}")
            )
        account = an_account(connection, anonymized=True)
        user = an_entry(connection, "user_anonymize", "user", account)
        contributor = an_entry(connection, "project_exit", "contributor", account)
    with empty_engine.begin() as connection:
        forget(connection, user)
    with pytest.raises(DBAPIError, match="refused"), empty_engine.begin() as connection:
        forget(connection, contributor)
    assert labels(empty_engine) == {"user": None, "contributor": "Inès Roux"}


INDEXES = (
    "ix_audit_entry_action_rank",
    "ix_audit_entry_actor_latest",
    "ix_audit_entry_object_kind_rank",
    "ix_audit_entry_project_latest",
)
CHECKS = ("action_known", "object_kind_known", "object_labeled")
# The indexes of the journal, valid or not, and their definition.
JOURNAL_INDEXES = text(
    "SELECT c.relname, i.indisvalid, pg_get_indexdef(i.indexrelid) FROM pg_index AS i "
    "JOIN pg_class AS c ON c.oid = i.indexrelid WHERE i.indrelid = 'audit_entry'::regclass"
)
# The checks of the journal, validated or not.
JOURNAL_CHECKS = text(
    "SELECT conname, convalidated FROM pg_constraint "
    "WHERE conrelid = 'audit_entry'::regclass AND contype = 'c'"
)


def indexes(engine: Engine) -> dict[str, tuple[bool, str]]:
    """Read each index of the journal: valid or not, and its definition."""
    with engine.connect() as connection:
        rows = connection.execute(JOURNAL_INDEXES).all()
    return {row[0]: (row[1], row[2]) for row in rows}


def assert_upgraded_whole(engine: Engine) -> None:
    """Check the four indexes of 0056 valid, none left under the name of a step, the checks held."""
    found = indexes(engine)
    assert {name: found[name][0] for name in INDEXES} == dict.fromkeys(INDEXES, True)
    assert [name for name in found if name.endswith("_next")] == []
    assert "project_manager_add" in found["ix_audit_entry_action_rank"][1]
    assert "contributor" in found["ix_audit_entry_object_kind_rank"][1]
    with engine.connect() as connection:
        checks = {row[0]: row[1] for row in connection.execute(JOURNAL_CHECKS)}
        assert connection.scalar(VERSION) == "0056"
    assert {f"ck_audit_entry_{name}": checks[f"ck_audit_entry_{name}"] for name in CHECKS} == {
        f"ck_audit_entry_{name}": True for name in CHECKS
    }


@pytest.mark.requirement("WF-DAT-0140-A")
def test_on_a_journal_written_the_upgrade_leaves_its_indexes_valid_and_its_checks_validated(
    empty_engine: Engine,
) -> None:
    # The indexes are created ``CONCURRENTLY`` and the checks posed ``NOT VALID``, then validated
    # apart: on a journal that holds lines, each ends valid, the ranks under their own name.
    upgrade(empty_engine, "0055")
    with empty_engine.begin() as connection:
        account = an_account(connection)
        an_entry(connection, "user_create", "user", account)
        an_entry(connection, "user_update", "user", account)
        an_entry(connection, "project_create", "project", uuid4())
    upgrade(empty_engine, "0056")
    assert_upgraded_whole(empty_engine)
    with empty_engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(AuditEntry)) == 3


@pytest.mark.requirement("WF-DAT-0140-A")
def test_over_a_rank_a_stopped_run_left_invalid_the_upgrade_runs_again_whole(
    empty_engine: Engine,
) -> None:
    # A creation ``CONCURRENTLY`` that fails leaves its index invalid (``indisvalid`` false), under
    # the name the upgrade creates the rank in its new order: a unique index of two lines of the
    # same action fails so. The upgrade run again drops it first, and ends as a first one does.
    upgrade(empty_engine, "0055")
    with empty_engine.begin() as connection:
        account = an_account(connection)
        an_entry(connection, "user_update", "user", account)
        an_entry(connection, "user_update", "user", account)
    stopped = text(
        "CREATE UNIQUE INDEX CONCURRENTLY ix_audit_entry_action_rank_next ON audit_entry (action)"
    )
    with (
        pytest.raises(DBAPIError, match="unique"),
        empty_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection,
    ):
        connection.execute(stopped)
    assert indexes(empty_engine)["ix_audit_entry_action_rank_next"][0] is False
    upgrade(empty_engine, "0056")
    assert_upgraded_whole(empty_engine)


# A demand of the exclusive lock of the journal that waits, not granted.
QUEUED_FOR_THE_JOURNAL = text(
    "SELECT count(*) FROM pg_locks WHERE relation = 'audit_entry'::regclass "
    "AND mode = 'AccessExclusiveLock' AND NOT granted"
)
# Past ``LOCK_WAIT`` (half a second) the demand gives way; the margin is the load of the machine.
WRITE_BOUND_SECONDS = 3


def until(engine: Engine, seen: Callable[[Connection], bool], what: str) -> None:
    """Read the catalogue until ``seen`` holds, thirty seconds at most."""
    deadline = time.monotonic() + 30
    with engine.connect() as watching:
        while time.monotonic() < deadline:
            if seen(watching):
                return
            watching.rollback()
            time.sleep(0.01)
    pytest.fail(f"never seen: {what}")


@pytest.mark.requirement("WF-DAT-0140-A")
def test_behind_a_reading_of_the_journal_that_lasts_the_upgrade_lets_the_journal_be_written(
    empty_engine: Engine,
) -> None:
    # A reading of the journal stays open, as a backup does; the upgrade queues for the exclusive
    # lock behind it. A write of the journal that comes after waits ``LOCK_WAIT`` at most, not the
    # end of the reading: it ends within its bound, while the upgrade is still waiting. Once the
    # reading ends, the upgrade ends.
    upgrade(empty_engine, "0055")
    with empty_engine.begin() as connection:
        an_entry(connection, "project_create", "project", uuid4())
    with ThreadPoolExecutor(1) as pool:
        with empty_engine.connect() as reading, reading.begin():
            reading.execute(select(AuditEntry.id)).all()
            migrating = pool.submit(upgrade, empty_engine, "0056")
            until(
                empty_engine,
                lambda watching: watching.scalar(QUEUED_FOR_THE_JOURNAL) == 1,
                "the upgrade queued for the journal",
            )
            started = time.monotonic()
            with empty_engine.begin() as writing:
                writing.execute(text("SET LOCAL lock_timeout = '10s'"))
                an_entry(writing, "project_create", "project", uuid4())
            waited = time.monotonic() - started
            assert not migrating.done()
        migrating.result(timeout=60)
    assert waited < WRITE_BOUND_SECONDS
    assert_upgraded_whole(empty_engine)


@pytest.mark.story("US-2850")
def test_a_refused_lock_of_the_upgrade_is_written_to_the_log_with_its_table_and_its_step(
    empty_engine: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    # #5096: behind a reading that stays open, the upgrade waits; each refusal says where.
    upgrade(empty_engine, "0055")
    caplog.set_level("WARNING")
    with ThreadPoolExecutor(1) as pool:
        with empty_engine.connect() as reading, reading.begin():
            reading.execute(select(AuditEntry.id)).all()
            migrating = pool.submit(upgrade, empty_engine, "0056")
            until(
                empty_engine,
                lambda _watching: any("lock refused" in each for each in caplog.messages),
                "a refused lock written to the log",
            )
        migrating.result(timeout=60)
    refused = [each for each in caplog.records if "lock refused" in each.getMessage()]
    assert refused[0].levelname == "WARNING"
    assert "audit_entry" in refused[0].getMessage()
    assert "widen the checks" in refused[0].getMessage()


@pytest.mark.story("US-2850")
@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_journal_refused_thirteen_times_over_a_clock_of_a_second_a_try_gives_two_warnings(
    empty_engine: Engine, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Give the first refusal, then the one past ten seconds with the count of those between.

    #5151. The clock is the test's, one second a try, so that the limit is proved whatever the
    speed of the machine: thirteen refusals cover thirteen seconds, which is more than the two
    seconds of the criterion (a journal held two seconds gives at most two lines) and crosses the
    ten-second limit once. Over the real time, the former code, a line per refusal, passed that
    criterion too: a refusal took a second and a half, too long for the test to tell them apart.
    """
    clock = RefusalClock(monkeypatch, ("0056_audit_project_managers.py",), stop_after=13)
    upgrade(empty_engine, "0055")
    caplog.set_level("WARNING")
    with ThreadPoolExecutor(1) as pool:
        with empty_engine.connect() as reading, reading.begin():
            reading.execute(select(AuditEntry.id)).all()
            migrating = pool.submit(upgrade, empty_engine, "0056")
            assert clock.reached.wait(60)
        clock.gate.set()
        migrating.result(timeout=60)
    refused = [each for each in caplog.messages if "lock refused" in each]
    assert len(refused) == 2
    assert "refused 1 time(s)" in refused[0]
    assert "refused 10 time(s)" in refused[1]
