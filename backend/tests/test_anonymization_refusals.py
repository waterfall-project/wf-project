# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What ``waterfall-restore anonymize`` refuses, and what it says of the realm (US-2960).

On the copy of ``anonymization_copy``: a copy it is not told is one, a realm the provider does not
hold, ``master``, a realm besides the two known, an installation administrator it would not keep, a
setting that lacks — each stops it, nothing changed —; an administrator kept the realm lacks is
said.
"""

from typing import TYPE_CHECKING

import pytest
from anonymization_copy import (
    ELSEWHERE,
    OTHER,
    OTHER_REALM,
    REALM,
    Person,
    anonymize_copy,
    mail_server,
    name_copy,
    provider_person,
    session_in,
    stand_in,
)
from anonymization_support import found, held_by_table
from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from waterfall.core.access_roles.interface import administrators
from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.users.interface import read_installation_administrator
from waterfall.core.users.tables import UserAccount
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.restore import anonymization
from waterfall.restore import main as restore_main

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

    from waterfall.platform.database import Database


@pytest.fixture
def provider(database_url: str) -> Iterator[Engine]:
    """Give a database that stands for the identity provider's, the realm and ``master``."""
    with stand_in(database_url) as engine:
        yield engine


@pytest.fixture
def copy(witness: Database, owner: Engine, provider: Engine) -> list[Person]:
    """Name the persons of the copy in both databases; give every name and address it holds."""
    return name_copy(witness, owner, provider)


@pytest.mark.story("US-2960")
def test_a_realm_the_provider_does_not_hold_stops_it_before_anything_changes(
    copy: list[Person],
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: a realm misnamed in the settings would leave the persons of the provider
    # named: the command stops, and changes nothing in either base.
    assert copy
    before = (held_by_table(owner), held_by_table(provider))
    assert anonymize_copy(monkeypatch, database_url, provider, realm="misnamed") == 1
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
@pytest.mark.parametrize("arguments", [(), ("--yes",), (anonymization.CONFIRMATION, "--again")])
def test_unless_told_the_databases_are_a_copy_it_changes_nothing(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
) -> None:
    # Proper to US-2960: the service of the restoration holds the databases of the production too;
    # run there by mistake, the command would anonymise the production for good. It changes
    # nothing unless told, in so many words, that they are a copy's (2).
    before = (held_by_table(owner), held_by_table(provider))
    assert anonymize_copy(monkeypatch, database_url, provider, arguments=arguments) == 2
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
def test_unless_told_the_databases_are_a_copy_it_says_how_to_tell_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960: refused, the command says the argument that tells it, before it reads
    # any setting.
    assert restore_main.main([anonymization.COMMAND]) == 2
    assert anonymization.CONFIRMATION in capsys.readouterr().err


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
def test_the_realm_of_the_administration_of_keycloak_is_refused(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960: ``master`` holds the administrators of Keycloak, no installation's
    # persons; disabling them would leave Keycloak without a way to be administered. Named in the
    # settings, it stops the command at start, nothing changed (2).
    before = (held_by_table(owner), held_by_table(provider))
    assert anonymize_copy(monkeypatch, database_url, provider, realm="master") == 2
    assert "WATERFALL_KEYCLOAK_REALM: " in capsys.readouterr().err
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
def test_an_administrator_kept_the_realm_does_not_hold_is_counted_and_said(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960 (#5089): an administrator kept whose person the realm of the copy no
    # longer holds is updated nowhere in Keycloak, and could not sign in; the command counts the
    # administrators kept it updated there, and says on its output the one it lacks, rather than
    # leave ``waterfall-api install`` refuse it later, far from the cause.
    with Session(owner) as session:
        held = administrators(session)
        installation = session.get(Installation, THE_ROW)
        assert installation is not None
        installer = read_installation_administrator(session, installation.installed_at)
        assert installer is not None
        (lacking,) = session.execute(
            select(UserAccount.id, UserAccount.idp_subject).where(
                UserAccount.id.in_(held), UserAccount.id != installer.user_id
            )
        ).all()
    with provider.begin() as connection:
        connection.execute(text("DELETE FROM user_entity WHERE id = :id"), {"id": lacking[1]})
    capsys.readouterr()
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
    lines = capsys.readouterr().out.splitlines()
    with Session(owner) as session:
        email = session.scalars(select(UserAccount.email).where(UserAccount.id == lacking[0])).one()
    absent = anonymization.ABSENT_NOTE.format(realm=REALM)
    assert [line for line in lines[1:-1] if line.endswith(absent)] == [f"{email}{absent}"]
    assert lines[-1] == (
        f"waterfall-restore {anonymization.COMMAND}: {len(held) - 1} of {len(held)} "
        f"administrators kept updated in the realm {REALM} of Keycloak"
    )


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
def test_a_realm_besides_the_installation_and_master_stops_it_before_anything_changes(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960 (#5088): the command anonymises the realm of the installation and
    # ``master`` alone; a realm of its own in the base of Keycloak would keep the names and the
    # addresses of its persons. The command refuses the copy, says which realm and what to do, and
    # writes nothing in either base — not the migrations, not the accounts, not Keycloak.
    with provider.begin() as connection:
        connection.execute(
            text("INSERT INTO realm VALUES (:id, :name)"), {"id": OTHER_REALM, "name": OTHER}
        )
        provider_person(connection, OTHER_REALM, ELSEWHERE)
        mail_server(connection, OTHER_REALM)
    before = (held_by_table(owner), held_by_table(provider))
    capsys.readouterr()
    assert anonymize_copy(monkeypatch, database_url, provider) == 1
    error = capsys.readouterr().err
    assert f"realms besides {REALM} and master" in error
    assert OTHER in error
    assert (held_by_table(owner), held_by_table(provider)) == before
    assert set(found(provider, set(ELSEWHERE))) >= {"public.user_entity.email"}


@pytest.fixture(params=["deactivated", "without_role"])
def installer_not_kept(request: pytest.FixtureRequest, copy: list[Person], owner: Engine) -> None:
    """Take from the installation administrator of the copy its activity, or its roles."""
    assert copy
    with owner.begin() as connection:
        installed_at = connection.execute(
            select(Installation.installed_at).where(Installation.id == THE_ROW)
        ).scalar_one()
        with session_in(connection) as session:
            installer = read_installation_administrator(session, installed_at)
        assert installer is not None
        if request.param == "deactivated":
            connection.execute(
                update(UserAccount)
                .where(UserAccount.id == installer.user_id)
                .values(state="deactivated")
            )
        else:
            connection.execute(
                delete(UserAccessRole).where(UserAccessRole.user_account_id == installer.user_id)
            )
    with Session(owner) as session:
        held = administrators(session)
    assert held
    assert installer.user_id not in held


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("installer_not_kept")
def test_an_installation_administrator_the_copy_would_not_keep_stops_it_before_anything_changes(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960 (#4068): an installation administrator deactivated, or without its roles,
    # in the backup would be anonymised, which the bootstrap refuses; the others kept would have
    # no link, and nobody would enter the copy. Another administrator active, the command stops
    # before it writes anything in either base, and says why and what to do.
    before = (held_by_table(owner), held_by_table(provider))
    capsys.readouterr()
    assert anonymize_copy(monkeypatch, database_url, provider) == 1
    error = capsys.readouterr().err
    assert "installation administrator" in error
    assert "restore a backup where it holds them" in error
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
def test_without_its_databases_the_command_stops_naming_them(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proper to US-2960: a setting that lacks stops it at start, named, rather than anonymise one
    # base and not the other.
    monkeypatch.delenv("WATERFALL_DATABASE_URL", raising=False)
    monkeypatch.delenv("WATERFALL_KEYCLOAK_DATABASE_URL", raising=False)
    assert restore_main.main([anonymization.COMMAND, anonymization.CONFIRMATION]) == 2
    error = capsys.readouterr().err
    assert "WATERFALL_DATABASE_URL: is missing" in error
    assert "WATERFALL_KEYCLOAK_DATABASE_URL: is missing" in error
