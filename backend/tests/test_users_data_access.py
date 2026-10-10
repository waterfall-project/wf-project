# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The accounts as the module stores them: identifiers, authors, moments, no deletion."""

import inspect
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from openapi_core import OpenAPI
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from support import PLATFORM_SECRETS

from waterfall.core.users import accounts, interface
from waterfall.core.users.accounts import NewAccount, Stamp, add_account, change_email
from waterfall.core.users.interface import read_account_label
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import NotFoundError, PreconditionFailedError
from waterfall.platform.identifiers import new_id

NOON = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
USERS = Path(accounts.__file__).parent


def born(
    session: Session, email: str = "claire.martin@example.org", author: UUID | None = None
) -> UserAccount:
    """Add an account and give it."""
    return add_account(
        session,
        NewAccount("Martin", "Claire", email, f"subject-{uuid4()}", "local"),
        Stamp(author, NOON),
    )


@pytest.mark.requirement("WF-DAT-0060-A")
def test_changing_the_address_of_an_account_leaves_the_rows_that_refer_to_it_as_they_are(
    session: Session,
) -> None:
    author = born(session, "author@example.org")
    written = born(session, "written@example.org", author.id)
    before = (written.created_by, written.updated_by, written.updated_at, written.lock_version)
    change_email(
        session, author.id, "new.author@example.org", author.lock_version, Stamp(None, NOON)
    )
    session.expire_all()
    after = session.get_one(UserAccount, written.id)
    assert (after.created_by, after.updated_by, after.updated_at, after.lock_version) == before
    assert session.get_one(UserAccount, author.id).email == "new.author@example.org"
    reader = read_account_label(session, after.created_by or uuid4())
    assert reader is not None
    assert (reader.user_id, reader.email) == (author.id, "new.author@example.org")


@pytest.mark.requirement("WF-DAT-0060-A")
def test_two_instances_inserting_at_the_same_moment_never_draw_the_same_identifier(
    database: Database,
) -> None:
    url = database.engine.url.render_as_string(hide_password=False)
    script = Path(__file__).parent / "insert_accounts.py"
    instances = [
        subprocess.Popen(
            [sys.executable, str(script), name, "40"],
            env={**PLATFORM_SECRETS, "WATERFALL_DATABASE_URL": url},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        for name in ("one", "two")
    ]
    for instance in instances:
        assert instance.stdout is not None
        assert instance.stdout.readline() == "ready\n"
    for instance in instances:
        assert instance.stdin is not None
        instance.stdin.write("go\n")
        instance.stdin.flush()
    drawn = [
        out for instance in instances for out in (instance.communicate(timeout=60)[0] or "").split()
    ]
    assert [instance.returncode for instance in instances] == [0, 0]
    assert len(drawn) == 80
    assert len(set(drawn)) == 80
    with database.engine.connect() as connection:
        stored = connection.execute(
            text("SELECT count(DISTINCT id) FROM user_account")
        ).scalar_one()
    assert stored == 80


@pytest.mark.requirement("WF-DAT-0060-A")
def test_an_identifier_is_a_version_7_uuid_that_sorts_with_time_and_is_never_repeated() -> None:
    first = new_id()
    time.sleep(0.01)
    later = [new_id() for _ in range(5000)]
    assert first.version == 7
    assert first < later[0]
    assert len({first, *later}) == 5001


@pytest.mark.requirement("WF-DAT-0060-A")
def test_the_identifier_of_an_account_is_written_by_the_service_not_by_the_database(
    database: Database,
) -> None:
    with database.engine.connect() as connection:
        column = connection.execute(
            text(
                "SELECT data_type, column_default FROM information_schema.columns "
                "WHERE table_name = 'user_account' AND column_name = 'id'"
            )
        ).one()
    assert tuple(column) == ("uuid", None)


def path_parameters(contract: OpenAPI) -> list[tuple[str, str | None, str | None]]:
    """List the path parameters of the contract: name, type and format."""
    found: list[tuple[str, str | None, str | None]] = []
    paths = contract.spec / "paths"
    with paths.open() as content:
        names = list(content)
    for path in names:
        item = paths / path
        for method in ("get", "put", "post", "patch", "delete"):
            if method not in item:
                continue
            operation = item / method
            with operation.open() as content:
                count = len(content.get("parameters", []))
            for index in range(count):
                with (operation / "parameters" / index).open() as parameter:
                    if parameter["in"] != "path":
                        continue
                    name = str(parameter["name"])
                with (operation / "parameters" / index / "schema").open() as schema:
                    found.append((name, schema.get("type"), schema.get("format")))
    return found


@pytest.mark.requirement("WF-DAT-0060-A")
def test_no_identifier_of_the_contract_is_a_sequential_number_in_its_url(
    contract: OpenAPI,
) -> None:
    parameters = path_parameters(contract)
    identifiers = [parameter for parameter in parameters if parameter[0].endswith("_id")]
    assert len(identifiers) > 100
    assert {(kind, form) for _, kind, form in identifiers} == {("string", "uuid")}


@pytest.mark.requirement("WF-DAT-0070-A")
def test_an_account_changed_by_an_administrator_carries_the_administrator_and_the_moment(
    session: Session,
) -> None:
    administrator = born(session, "administrator@example.org")
    person = born(session, "person@example.org")
    later = NOON + timedelta(hours=3)
    changed = change_email(
        session,
        person.id,
        "person.new@example.org",
        person.lock_version,
        Stamp(administrator.id, later),
    )
    assert (changed.updated_by, changed.updated_at) == (administrator.id, later)
    assert (changed.created_by, changed.created_at) == (None, NOON)
    assert changed.lock_version == 1


@pytest.mark.requirement("WF-DAT-0070-A")
def test_the_platform_is_the_author_of_a_row_by_a_null_author(session: Session) -> None:
    administrator = born(session, "administrator@example.org")
    account = add_account(
        session,
        NewAccount("Martin", "Claire", "claire.martin@example.org", f"subject-{uuid4()}", "local"),
        Stamp(administrator.id, NOON),
    )
    later = NOON + timedelta(hours=1)
    changed = change_email(
        session, account.id, "claire.new@example.org", account.lock_version, Stamp(None, later)
    )
    session.expire_all()
    stored = session.get_one(UserAccount, changed.id)
    assert stored.updated_by is None
    assert stored.updated_at == later
    assert stored.created_by == administrator.id


def test_a_change_made_on_a_version_that_is_not_the_current_one_is_refused(
    session: Session,
) -> None:
    account = born(session)
    change_email(session, account.id, "one@example.org", 0, Stamp(None, NOON))
    with pytest.raises(PreconditionFailedError) as refused:
        change_email(session, account.id, "two@example.org", 0, Stamp(None, NOON))
    assert (refused.value.code, refused.value.params) == (
        "STALE_LOCK_VERSION",
        {"expected_lock_version": 1},
    )
    assert session.get_one(UserAccount, account.id).email == "one@example.org"


def test_a_change_to_an_account_that_does_not_exist_is_a_missing_object(session: Session) -> None:
    with pytest.raises(NotFoundError):
        change_email(session, uuid4(), "x@example.org", 0, Stamp(None, NOON))


def test_the_label_of_an_account_says_whether_it_may_sign_in(session: Session) -> None:
    account = born(session)
    assert read_account_label(session, account.id) == interface.AccountLabel(
        account.id, "Martin", "Claire", "claire.martin@example.org", is_active=True
    )
    session.execute(text("UPDATE user_account SET state = 'deactivated'"))
    session.expire_all()
    label = read_account_label(session, account.id)
    assert label is not None
    assert label.is_active is False
    assert read_account_label(session, uuid4()) is None


@pytest.mark.requirement("WF-DAT-0100-A")
def test_the_moments_of_an_account_are_kept_in_universal_time_whatever_the_zone_written(
    session: Session,
) -> None:
    paris = timezone(timedelta(hours=2))
    account = add_account(
        session,
        NewAccount("Martin", "Claire", "claire@example.org", "s-1", "local"),
        Stamp(None, datetime(2026, 6, 30, 1, 30, tzinfo=paris)),
    )
    session.expire_all()
    stored = session.get_one(UserAccount, account.id)
    assert stored.created_at == datetime(2026, 6, 29, 23, 30, tzinfo=UTC)
    assert stored.created_at.utcoffset() == timedelta(0)
    assert stored.updated_at.utcoffset() == timedelta(0)


@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_moment_without_a_zone_is_refused(session: Session) -> None:
    naive = Stamp(None, datetime.fromisoformat("2026-06-30T01:30:00"))
    with pytest.raises(StatementError, match="without a time zone") as refused:
        add_account(session, NewAccount("Martin", "Claire", "c@example.org", "s-2", "local"), naive)
    assert isinstance(refused.value.orig, ValueError)


@pytest.mark.requirement("WF-DAT-0100-A")
def test_the_audit_columns_are_timestamps_with_a_time_zone_and_the_session_is_in_universal_time(
    database: Database,
) -> None:
    with database.engine.connect() as connection:
        types = connection.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'user_account' AND column_name IN ('created_at', 'updated_at')"
            )
        ).all()
        zone = connection.execute(text("SHOW timezone")).scalar_one()
    assert {tuple(row) for row in types} == {
        ("created_at", "timestamp with time zone"),
        ("updated_at", "timestamp with time zone"),
    }
    assert zone == "UTC"


@pytest.mark.requirement("WF-DAT-0100-A")
def test_the_clock_of_the_platform_is_in_universal_time() -> None:
    assert utc_now().utcoffset() == timedelta(0)


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_module_of_the_accounts_has_no_command_that_deletes_one() -> None:
    names = [
        name
        for module in (accounts, interface)
        for name, _ in inspect.getmembers(module, inspect.isfunction)
    ]
    assert names
    assert not [name for name in names if name.startswith(("delete", "remove", "purge", "drop"))]
    sources = "\n".join(path.read_text(encoding="utf-8") for path in USERS.glob("*.py"))
    assert "delete(" not in sources
    assert "DELETE" not in sources


@pytest.mark.requirement("WF-DAT-0080-A")
def test_an_account_that_other_rows_refer_to_cannot_be_removed_from_the_database(
    session: Session,
) -> None:
    author = born(session, "author@example.org")
    born(session, "written@example.org", author.id)
    session.flush()
    with pytest.raises(IntegrityError, match="fk_user_account_created_by_user_account"):
        session.execute(text("DELETE FROM user_account WHERE id = :id"), {"id": author.id})
