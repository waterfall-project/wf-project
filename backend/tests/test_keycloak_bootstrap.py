# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The bootstrap of a new installation, on the platform: ``waterfall-api install`` (US-0420).

It runs in the process of the tests, on a database of their own as the owner of its tables, and
against the Keycloak of the platform, whose realm it gives an administrator removed after each
test. The API that the administrator then reads is served in the process too, as in
``test_keycloak_sign_in.py``, whose helpers it takes. Run by ``make test-keycloak``, with the
variables of ``test_keycloak_platform.py`` and ``WATERFALL_INSTALLATION_CLIENT_SECRET``, the secret
the realm was applied with for the client of the bootstrap. The path the administrator follows in
the browser, from the link to the screens, is the front's (``frontend/e2e/service/``).
"""

import html
import io
import json
import logging
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx2
import pytest
import structlog
from openapi_core import OpenAPI
from pydantic import SecretStr
from sqlalchemy import Engine, func, insert, select, text, update
from support import CONTRACT, ContractClient, Logs
from test_keycloak_authentication import (
    ME,
    bearer,
    served_api,
    served_settings,
    service_admin,
    tokens_of,
)
from test_keycloak_platform import (
    ADDRESS_VARIABLE,
    BACKCHANNEL_VARIABLE,
    DIRECTORY_EMAIL,
    PASSWORD,
    REPLACED,
    SERVICE_CREDENTIAL_VARIABLE,
    SPENT,
    Browser,
    action_token,
    administering,
    required,
    set_by_link,
)
from test_keycloak_sign_in import realm_set
from test_migrations import HEAD, scratch_database

from waterfall import bootstrap
from waterfall.core.access_roles.tables import AccessRole, Permission
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database
from waterfall.platform.installation import Installation
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.logs import configure_logging
from waterfall.platform.settings import InstallationSettings

pytestmark = pytest.mark.keycloak

INSTALLATION_CREDENTIAL_VARIABLE = "WATERFALL_INSTALLATION_CLIENT_SECRET"
ACCESS_ROLES = "/api/v1/access-roles"
PERMISSIONS = "/api/v1/permissions"
# The example of the contract that gives the roles of an installation, the three predefined ones.
WITNESS = CONTRACT.parents[2] / "fixtures" / "api" / "access_roles.json"
# The expiry of a link valid until it is used: the last moment a token of Keycloak can say.
UNTIL_USED = 2**31 - 1


def settings_of(database_url: str, email: str, language: str = "fr") -> InstallationSettings:
    """Give the settings of a bootstrap of ``database_url``, as its owner, for ``email``."""
    return InstallationSettings.model_validate(
        {
            "database_url": database_url,
            "keycloak_address": required(ADDRESS_VARIABLE),
            "keycloak_backchannel": required(BACKCHANNEL_VARIABLE),
            "service_client_secret": required(SERVICE_CREDENTIAL_VARIABLE),
            "installation_client_secret": required(INSTALLATION_CREDENTIAL_VARIABLE),
            "admin_email": email,
            "default_language": language,
        }
    )


def installed(settings: InstallationSettings) -> tuple[int, str]:
    """Run the bootstrap; give what it returns and what it writes on its standard output."""
    out = io.StringIO()
    return bootstrap.install(settings, out), out.getvalue()


def variables_of(settings: InstallationSettings) -> dict[str, str]:
    """Give the variables of the environment that carry ``settings`` to the command."""
    return {
        f"WATERFALL_{name.upper()}": (
            value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        )
        for name, value in settings.model_dump(exclude_none=True).items()
    }


def link_of(settings: InstallationSettings) -> str:
    """Run the bootstrap, which must succeed and write a link alone; give the link."""
    status, out = installed(settings)
    assert status == 0
    link = out.removesuffix("\n")
    assert out == f"{link}\n"
    assert "\n" not in link
    return link


def realm_accounts(admin: httpx2.Client, email: str) -> list[dict[str, Any]]:
    """Read the accounts of the realm that hold ``email``."""
    found = admin.get("/users", params={"email": email, "exact": "true"})
    assert found.status_code == 200, found.text
    return list(found.json())


@pytest.fixture
def logs() -> Iterator[Logs]:
    """Capture the logs in memory, then restore them.

    The fixture of ``conftest.py`` would give the process the secrets of a platform of test,
    which the Keycloak of the platform refuses.
    """
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    stream = io.StringIO()
    configure_logging("DEBUG", stream)
    yield Logs(stream)
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()


def realm_language() -> str | None:
    """Read the language of the realm, that of an account that chose none."""
    with administering() as realm:
        return realm.get("").json().get("defaultLocale")


@pytest.fixture(autouse=True)
def kept_language() -> Iterator[None]:
    """Give the realm back its language after the test: a bootstrap gives it its own (#873)."""
    kept = realm_language()
    yield
    with administering() as realm:
        restored = realm.put("", json={"defaultLocale": kept})
        assert restored.status_code == 204, restored.text


@pytest.fixture
def admin() -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the service account, as the API does."""
    with service_admin(served_settings()) as client:
        yield client


@pytest.fixture
def address(admin: httpx2.Client, database: Database) -> Iterator[str]:
    """Give the address of an administrator no account holds; remove its account from the realm.

    The database of the test is emptied after, of the installation the test made.
    """
    del database
    email = f"administrateur.{uuid4().hex[:12]}@waterfall.test"
    yield email
    for account in realm_accounts(admin, email):
        admin.delete(f"/users/{account['id']}")


@pytest.fixture
def api(contract: OpenAPI, database: Database) -> Iterator[ContractClient]:
    """Give a client of the API on the database of the test and the Keycloak of the platform."""
    keycloak = Keycloak(served_settings())
    yield served_api(contract, database, keycloak)
    keycloak.close()


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.requirement("WF-ADM-0010-A")
def test_after_installation_the_administrator_sets_its_password_signs_in_and_finds_the_roles(
    api: ContractClient, database: Database, database_url: str, address: str
) -> None:
    # « Après installation, un administrateur fixe son mot de passe par le lien produit, se
    # connecte, porte le rôle « administrateur », et trouve les trois rôles prédéfinis et le
    # catalogue des permissions. » And WF-ADM-0010-A : « Sur une installation neuve, les trois
    # rôles existent et leurs permissions couvrent les usages des exigences citées. »
    link = link_of(settings_of(database_url, address))
    _, done = set_by_link(link, PASSWORD)
    assert done.status_code == 200, done.text
    headers = bearer(tokens_of(address, PASSWORD))
    me = api.get(ME, headers=headers).json()
    assert (me["email"], me["origin"], me["access_role_labels"]) == (
        address,
        "local",
        ["Administrateur"],
    )
    roles = api.get(ACCESS_ROLES, headers=headers).json()
    witness = json.loads(WITNESS.read_text(encoding="utf-8"))["value"]
    assert {role["label"]: set(role["permissions"]) for role in roles} == {
        role["label"]: set(role["permissions"]) for role in witness if role["is_predefined"]
    }
    assert all(role["is_predefined"] for role in roles)
    administrator = next(role for role in roles if role["label"] == "Administrateur")
    assert set(me["permissions"]) == set(administrator["permissions"])
    catalogue = api.get(PERMISSIONS, headers=headers).json()
    with database.transaction() as session:
        assert len(catalogue) == session.scalar(select(func.count()).select_from(Permission))
    # The link is spent: opened again, it says so.
    used = Browser().get(link)
    assert (used.status_code, SPENT in html.unescape(used.text)) == (400, True)


@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_second_installation_creates_nothing_and_replaces_the_link_until_a_password_is_set(
    admin: httpx2.Client, database: Database, database_url: str, address: str
) -> None:
    # « Une seconde exécution de l'installation ne crée ni compte, ni calendrier, ni nature
    # supplémentaire ; elle produit un nouveau lien, qui remplace le précédent, tant que
    # l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » The calendar and
    # the nature arrive with EP-05.
    settings = settings_of(database_url, address)
    first = link_of(settings)
    created = counts(admin, database, address)
    assert created == (1, 3, 1, 1)
    second = link_of(settings)
    assert second != first
    assert counts(admin, database, address) == created
    replaced = Browser().get(first)
    assert (replaced.status_code, REPLACED in html.unescape(replaced.text)) == (400, True)
    _, done = set_by_link(second, PASSWORD)
    assert done.status_code == 200, done.text
    assert installed(settings) == (0, "")
    assert counts(admin, database, address) == created


@pytest.mark.requirement("WF-EXP-0020-A")
def test_an_administrator_given_a_password_another_way_is_given_no_link_and_its_link_serves_no_more(
    admin: httpx2.Client, database: Database, database_url: str, address: str, logs: Logs
) -> None:
    # « … tant que l'administrateur n'a pas fixé son mot de passe, et aucun lien ensuite. » Set
    # here by the console, not by the link: the extension refuses a new link (#884), and the link
    # made before no longer opens the form.
    settings = settings_of(database_url, address)
    link = link_of(settings)
    with database.transaction() as session:
        subject = session.scalars(select(UserAccount.idp_subject)).one()
    given = admin.put(
        f"/users/{subject}/reset-password",
        json={"type": "password", "value": PASSWORD, "temporary": False},
    )
    assert given.status_code == 204, given.text
    assert installed(settings) == (0, "")
    assert len(logs.named("installation.no_link")) == 1
    with database.transaction() as session:
        made = session.scalars(
            select(AuditEntry.action).where(AuditEntry.action == "password_link_create")
        ).all()
    assert made == ["password_link_create"]
    spent = Browser().get(link)
    assert (spent.status_code, SPENT in html.unescape(spent.text)) == (400, True)


def test_two_installations_run_at_once_make_one(
    admin: httpx2.Client, database: Database, owner: Engine, database_url: str, address: str
) -> None:
    # The advisory lock keeps two bootstraps apart, run at once in two processes: the second waits
    # for the first, finds the installation made, and replaces its link. Without it, both would
    # find none and install, and the second would fail on the row of the first. The test holds
    # the lock itself until both wait on it, so that they do run at once: without a lock in the
    # code, none ever waits, and the test fails at the end of its delay.
    command = [
        sys.executable,
        "-c",
        "import sys; from waterfall.bootstrap import main; sys.exit(main(['install']))",
    ]
    environment = os.environ | variables_of(settings_of(database_url, address))
    # A key of 64 bits is held as two halves of 32: the high one is 0 for this one.
    waiting = text(
        "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted "
        "AND database = (SELECT oid FROM pg_database WHERE datname = current_database()) "
        "AND classid = 0 AND objid = :key AND objsubid = 1"
    ).bindparams(key=bootstrap.INSTALL_LOCK)
    with owner.connect() as holder:
        holder.execute(select(func.pg_advisory_lock(bootstrap.INSTALL_LOCK)))
        holder.commit()
        runs = [
            subprocess.Popen(
                command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            for _ in range(2)
        ]
        try:
            deadline = time.monotonic() + 60
            with owner.connect() as watcher:
                while watcher.execute(waiting).scalar_one() < 2:
                    watcher.rollback()
                    assert time.monotonic() < deadline, "the bootstraps never waited on the lock"
                    assert all(run.poll() is None for run in runs), "a bootstrap ended unlocked"
                    time.sleep(0.1)
        except BaseException:
            for run in runs:
                run.kill()
                run.communicate()
            raise
        finally:
            holder.rollback()
            holder.execute(select(func.pg_advisory_unlock(bootstrap.INSTALL_LOCK)))
            holder.commit()
    written = [run.communicate(timeout=180) for run in runs]
    assert [run.returncode for run in runs] == [0, 0], [err for _, err in written]
    links = [out.removesuffix("\n") for out, _ in written]
    assert all(link and "\n" not in link for link in links), links
    assert counts(admin, database, address) == (1, 3, 1, 1)
    # The link of the first is replaced by that of the second, whichever came first.
    # The other opens, at the page that asks to confirm it.
    opened = [Browser().get(link) for link in links]
    assert sorted(REPLACED in html.unescape(page.text) for page in opened) == [False, True]
    assert sorted(page.status_code for page in opened) == [200, 400]


@pytest.mark.requirement("WF-EXP-0020-A")
def test_the_link_of_the_installation_is_accepted_more_than_an_hour_after_it_was_made(
    database_url: str, address: str
) -> None:
    # « Le lien produit à l'installation est accepté plus d'une heure après sa production. » The
    # hour of the links the realm makes is a second here: the link of the installation does not
    # keep it, its token saying no other end than the farthest a token of Keycloak can say.
    with realm_set(actionTokenGeneratedByAdminLifespan=1):
        link = link_of(settings_of(database_url, address))
        assert action_token(link)["exp"] == UNTIL_USED
        time.sleep(2.1)
        _, done = set_by_link(link, PASSWORD)
    assert done.status_code == 200, done.text
    tokens_of(address, PASSWORD)


@pytest.mark.requirement("WF-EXP-0020-A")
def test_the_installation_applies_the_migrations_and_labels_its_roles_in_its_language(
    database_url: str, address: str, logs: Logs
) -> None:
    # Proper to the story: the bootstrap applies the migrations — the catalogue with them —,
    # creates the three predefined roles, the local administrator in the provider and in
    # Waterfall, and the default language of the installation; the labels of the roles are in
    # that language (WF-EXP-0020). Its inscriptions carry the platform and its correlation (#701).
    with scratch_database(database_url, "waterfall_bootstrap") as empty:
        owner = empty.url.render_as_string(hide_password=False)
        link = link_of(settings_of(owner, address, language="en"))
        with empty.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            language = connection.scalar(select(Installation.default_language))
            catalogue = connection.scalar(select(func.count()).select_from(Permission))
            labels = set(connection.scalars(select(AccessRole.label)))
            held = connection.execute(
                select(UserAccount.email, UserAccount.origin, UserAccount.created_by)
            ).all()
            entries = connection.execute(
                select(AuditEntry.action, AuditEntry.actor_user_id, AuditEntry.correlation_id)
            ).all()
    assert (revision, language) == (HEAD, "en")
    assert catalogue
    assert labels == {"Administrator", "Project manager", "Manager"}
    assert held == [(address, "local", None)]
    assert sorted(action for action, _, _ in entries) == [
        "access_role_create",
        "access_role_create",
        "access_role_create",
        "password_link_create",
        "user_access_roles_set",
        "user_create",
    ]
    assert {actor for _, actor, _ in entries} == {None}
    (correlation,) = {correlation for _, _, correlation in entries}
    assert [record["correlation_id"] for record in logs.named("installation.link_made")] == [
        correlation
    ]
    # The link reaches neither the journal nor the logs.
    token = link.split("key=", 1)[1]
    assert token not in logs.text


def test_a_second_installation_for_another_address_says_it_ignores_it(
    database_url: str, address: str, logs: Logs
) -> None:
    # The administrator is that of the installation made: another address, given since, makes no
    # second one, and the logs say it is ignored — without it.
    link_of(settings_of(database_url, address))
    other = f"autre.{address}"
    link_of(settings_of(database_url, other))
    (ignored,) = logs.named("installation.admin_email_ignored")
    assert ignored["level"] == "warning"
    assert other not in logs.text
    # The same address, in other letters, is the administrator's.
    link_of(settings_of(database_url, address.upper()))
    assert len(logs.named("installation.admin_email_ignored")) == 1


def test_the_installation_gives_the_realm_its_language_at_each_run(
    database_url: str, address: str
) -> None:
    # #873: an account that chose no language reads the pages and the mails of the realm in the
    # language of the installation (WF-INTF-0160, « à défaut la langue par défaut de
    # l'installation »), which the bootstrap gives the realm.
    settings = settings_of(database_url, address, language="en")
    link_of(settings)
    assert realm_language() == "en"
    # Taken back by the realm, it is given again at the next run: the language of the installation
    # made, not that of the settings now.
    with administering() as realm:
        assert realm.put("", json={"defaultLocale": "fr"}).status_code == 204
    link_of(settings.model_copy(update={"default_language": "fr"}))
    assert realm_language() == "en"


def counts(admin: httpx2.Client, database: Database, email: str) -> tuple[int, int, int, int]:
    """Count the accounts, the roles and the installations made, and the accounts of the realm."""
    with database.transaction() as session:
        return (
            session.scalar(select(func.count()).select_from(UserAccount)) or 0,
            session.scalar(select(func.count()).select_from(AccessRole)) or 0,
            session.scalar(select(func.count()).select_from(Installation)) or 0,
            len(realm_accounts(admin, email)),
        )


def refused(settings: InstallationSettings, logs: Logs) -> str:
    """Run a bootstrap the platform refuses, which writes nothing; give the reason it logs."""
    assert installed(settings) == (1, "")
    (record,) = logs.named("installation.refused")
    return str(record["reason"])


@pytest.mark.usefixtures("database")
def test_an_address_that_is_none_is_refused_before_anything_is_created(
    admin: httpx2.Client, database_url: str, logs: Logs
) -> None:
    assert refused(settings_of(database_url, "not an address"), logs) == (
        "admin_email_not_an_address"
    )
    assert realm_accounts(admin, "not an address") == []


@pytest.mark.usefixtures("database")
def test_an_address_held_by_a_person_of_the_directory_is_refused(
    database_url: str, logs: Logs
) -> None:
    assert refused(settings_of(database_url, DIRECTORY_EMAIL), logs) == (
        "admin_email_held_in_identity_provider"
    )


def test_a_run_broken_once_the_provider_created_the_account_is_taken_up(
    admin: httpx2.Client, database: Database, database_url: str, address: str
) -> None:
    # The provider created the account, then the run stopped before its transaction: the next run
    # takes the account up, rather than refuse an address the realm holds.
    made = admin.post(
        "/users",
        json={
            "username": address,
            "email": address,
            "firstName": "Waterfall",
            "lastName": "Administrateur",
            "enabled": True,
        },
    )
    assert made.status_code == 201, made.text
    subject = made.headers["Location"].rsplit("/", 1)[-1]
    link_of(settings_of(database_url, address))
    with database.transaction() as session:
        assert session.scalars(select(UserAccount.idp_subject)).all() == [subject]


def test_an_installation_without_its_administrator_is_refused(
    owner: Engine, database_url: str, address: str, logs: Logs
) -> None:
    with owner.begin() as connection:
        connection.execute(
            insert(Installation).values(
                id=1,
                default_language="fr",
                avatar_max_bytes=1,
                external_backup_max_bytes=1,
                installed_at=func.now(),
            )
        )
    assert refused(settings_of(database_url, address), logs) == "no_administrator"


def test_a_deactivated_administrator_is_given_no_link(
    owner: Engine, database_url: str, address: str, logs: Logs
) -> None:
    settings = settings_of(database_url, address)
    link_of(settings)
    with owner.begin() as connection:
        connection.execute(update(UserAccount).values(state="deactivated"))
    assert refused(settings, logs) == "STATE_FORBIDS_OPERATION"
    (record,) = logs.named("installation.refused")
    assert record["params"] == {"missing_condition": "is_active_account"}


def test_an_administrator_the_realm_relays_since_is_given_no_link(
    admin: httpx2.Client, owner: Engine, database_url: str, address: str, logs: Logs
) -> None:
    # Local for Waterfall, but linked since to an external provider in the realm: the extension
    # refuses its link, and so does the bootstrap.
    settings = settings_of(database_url, address)
    link_of(settings)
    with owner.connect() as connection:
        subject = connection.scalar(select(UserAccount.idp_subject))
    linked = admin.post(
        f"/users/{subject}/federated-identity/external",
        json={"identityProvider": "external", "userId": uuid4().hex, "userName": address},
    )
    assert linked.status_code == 204, linked.text
    assert refused(settings, logs) == "administrator_not_local"


def test_an_administrator_the_realm_no_longer_holds_is_refused(
    admin: httpx2.Client, owner: Engine, database_url: str, address: str, logs: Logs
) -> None:
    # Removed from the realm in its console since the installation: said by its reason, not
    # traced as a failure.
    settings = settings_of(database_url, address)
    link_of(settings)
    with owner.connect() as connection:
        subject = connection.scalar(select(UserAccount.idp_subject))
    assert admin.delete(f"/users/{subject}").status_code == 204
    assert refused(settings, logs) == "administrator_not_in_provider"
    assert logs.named("installation.failed") == []


def test_a_keycloak_that_does_not_answer_stops_the_installation(
    database_url: str, address: str, logs: Logs
) -> None:
    unreachable = settings_of(database_url, address).model_copy(
        update={"keycloak_backchannel": "http://127.0.0.1:9/auth"}
    )
    assert refused(unreachable, logs) == "COMPONENT_UNAVAILABLE"


def test_a_failure_the_installation_does_not_expect_is_said_as_such(
    database_url: str, address: str, logs: Logs
) -> None:
    # The secret of the client of the bootstrap is not the one the realm was applied with: a
    # defect of the platform, which the logs trace.
    wrong = settings_of(database_url, address).model_copy(
        update={"installation_client_secret": SecretStr("not-the-secret")}
    )
    assert installed(wrong) == (1, "")
    (failed,) = logs.named("installation.failed")
    assert "IdentityProviderError" in failed["exception"]


@pytest.mark.usefixtures("logs")
def test_the_command_bootstraps_and_writes_the_link_alone(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database_url: str,
    address: str,
) -> None:
    # Its logs on the error output, which the fixture of the logs gives back after the test.
    for name, value in variables_of(settings_of(database_url, address)).items():
        monkeypatch.setenv(name, value)
    assert bootstrap.main(["install"]) == 0
    written = capsys.readouterr()
    assert written.out.startswith(f"{required(ADDRESS_VARIABLE).rstrip('/')}/realms/waterfall/")
    assert written.out.count("\n") == 1
    assert "installation.link_made" in written.err
    assert written.out.strip() not in written.err
