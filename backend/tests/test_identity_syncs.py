# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the accounts asked for through the API, and its report (US-0370).

A reading is deposited for the worker and the request answers at once (WF-ARC-0090); its report is
read apart; it names an account of Waterfall as it is shown when read, an account anonymised since
by no name (#920). Keycloak is the realm of test, which the reading never reaches here: what the
worker reads of Keycloak is tried against the platform (``test_keycloak_identity_sync.py``). What
the reading does once committed — the removal of the orphans, the identities given back to the
provider (#919) — is tried here against PostgreSQL: it runs once its transaction is committed,
never if what registered it is rolled back, and asks the provider with no connection held.
"""

import json
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import ContractClient, Logs, Watching, bearer, nowhere
from task_handlers import deposit, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.interface import (
    Skipped,
    SkippedAccount,
    SkippedPerson,
    SyncReport,
    latest_report,
    record_report,
)
from waterfall.core.users.tables import IdentitySyncReport, UserAccount
from waterfall.platform.database import Database, utc_now
from waterfall.platform.keycloak import Keycloak, unavailable
from waterfall.platform.keycloak_admin import KeycloakAdmin, LocalIdentity, ProviderAccount
from waterfall.platform.queue import TaskQueue
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.tasks import BackgroundTask, Task
from waterfall.worker.identity_sync import IdentitySync, after_commit, write_accounts
from waterfall.worker.runner import Worker

SYNCS = "/api/v1/identity-syncs"
LATEST = f"{SYNCS}/latest"
NIGHT = datetime(2026, 10, 12, 2, 0, tzinfo=UTC)

type Person = Callable[..., tuple[UUID, dict[str, str]]]


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the API that deposits in the queue of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    _, bucket = nowhere()
    app = create_app(Services(database, keycloak, administration, queue, bucket))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each holding a role of the permissions given, and its header."""

    def make(*permissions: str) -> tuple[UUID, dict[str, str]]:
        subject = f"subject-{uuid4()}"
        held = role(database, f"Rôle {uuid4().hex[:8]}", permissions=permissions)
        user_id = account(database, "Martin", uuid4().hex[:8], roles=(held,), idp_subject=subject)
        return user_id, bearer(realm.token(subject, KEY))

    return make


HUGO = SkippedPerson("kc-hugo", "Garnier", "Hugo", None, "EMAIL_MISSING")


def reported(
    database: Database, queue: TaskQueue, finished_at: datetime, created: int, kept: UUID
) -> UUID:
    """Keep the report of a reading the platform scheduled, ended at ``finished_at``."""
    task_id = deposit(database, queue)
    with database.transaction() as session:
        skipped: list[Skipped] = [SkippedAccount(kept, "LAST_ADMINISTRATOR"), HUGO]
        report = SyncReport(task_id, finished_at, created, 1, 0, 2, skipped, ["o@x.org"])
        record_report(session, report)
    return task_id


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_reading_asked_for_is_deposited_for_the_worker_and_answered_at_once(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir
    # exécuté. » : for the reading of the accounts, the answer is the task, queued, deposited.
    user_id, headers = person("users.write")
    asked = api.post(SYNCS, headers=headers)
    assert asked.status_code == 202, asked.text
    ref = asked.json()
    assert (ref["kind"], ref["status"], ref["progress"], ref["result_url"]) == (
        "identity_sync",
        "queued",
        0,
        None,
    )
    task_id = UUID(ref["task_id"])
    deposited = task(database, task_id)
    assert (deposited.status, deposited.requested_by) == ("queued", user_id)
    assert task_id in queue.waiting()
    # Once it succeeded, the task says where its report is read.
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == task_id)
            .values(status="succeeded", progress=100, finished_at=NIGHT)
        )
    done = api.get(f"/api/v1/tasks/{task_id}", headers=headers).json()
    assert (done["status"], done["result_url"]) == ("succeeded", LATEST)


def test_a_reading_is_asked_for_under_the_permission_to_change_the_accounts(
    api: ContractClient, person: Person
) -> None:
    _, headers = person("users.read")
    refused = api.post(SYNCS, headers=headers)
    assert (refused.status_code, refused.json()["params"]) == (
        403,
        {"missing_permission": "users.write"},
    )


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_report_of_two_readings_ended_together_is_always_the_same_one(
    database: Database, queue: TaskQueue
) -> None:
    # « Le dernier compte administrateur, retiré de l'annuaire, reste actif et la synchronisation
    # le signale. » : the report that tells it is the same each time it is read, whatever the
    # order the rows are kept in; of two readings ended at the same instant, the greater task wins.
    kept = account(database, "Bernard", "Dominique", origin="directory")
    tasks = [reported(database, queue, NIGHT, count, kept) for count in (1, 2, 3)]
    for _ in range(3):
        with database.transaction() as session:
            report = latest_report(session)
        assert report is not None
        assert report.task_id == max(tasks)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_report_read_is_that_of_the_latest_reading_ended(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # « Le dernier compte administrateur, retiré de l'annuaire, reste actif et la synchronisation
    # le signale. » : named as it is shown today; a person without an address, as the provider
    # holds her (#918).
    _, headers = person("users.read")
    assert api.get(LATEST, headers=headers).status_code == 404
    kept = account(database, "Bernard", "Dominique", origin="directory")
    reported(database, queue, NIGHT - timedelta(days=1), 3, kept)
    latest = reported(database, queue, NIGHT, 2, kept)
    response = api.get(LATEST, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "task_id": str(latest),
        "finished_at": "2026-10-12T02:00:00Z",
        "created": 2,
        "updated": 1,
        "deactivated": 0,
        "restored": 2,
        "skipped": [
            {
                "kind": "account",
                "user_id": str(kept),
                "subject": None,
                "last_name": "Bernard",
                "first_name": "Dominique",
                "email": "dominique.bernard@example.org",
                "code": "LAST_ADMINISTRATOR",
            },
            {
                "kind": "person",
                "user_id": None,
                "subject": "kc-hugo",
                "last_name": "Garnier",
                "first_name": "Hugo",
                "email": None,
                "code": "EMAIL_MISSING",
            },
        ],
        "removed": ["o@x.org"],
    }
    # The accounts not consulted, the report does not exist for the caller.
    _, outside = person("users.write")
    assert api.get(LATEST, headers=outside).status_code == 404


def anonymized(database: Database, user_id: UUID) -> None:
    """Anonymise an account around the service: no name, no address, deactivated."""
    with database.transaction() as session:
        session.execute(
            update(UserAccount)
            .where(UserAccount.id == user_id)
            .values(
                last_name=None,
                first_name=None,
                email=None,
                state="deactivated",
                anonymized_at=utc_now(),
            )
        )


@pytest.mark.requirement("WF-ADM-0060-A")
def test_an_account_the_report_names_and_anonymized_since_is_named_by_no_name(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # « Après anonymisation d'un compte désactivé, aucun écran — journal d'audit compris — ne
    # présente plus son nom ni son adresse » : the report kept none of them (#920).
    _, headers = person("users.read")
    kept = account(database, "Bernard", "Dominique", origin="directory")
    task_id = reported(database, queue, NIGHT, 0, kept)
    with database.transaction() as session:
        stored = session.scalars(
            select(IdentitySyncReport.skipped).where(IdentitySyncReport.task_id == task_id)
        ).one()
        assert stored[0] == {"kind": "account", "user_id": str(kept), "code": "LAST_ADMINISTRATOR"}
    anonymized(database, kept)
    response = api.get(LATEST, headers=headers)
    assert response.status_code == 200, response.text
    (named, _) = response.json()["skipped"]
    assert named == {
        "kind": "account",
        "user_id": str(kept),
        "subject": None,
        "last_name": None,
        "first_name": None,
        "email": None,
        "code": "LAST_ADMINISTRATOR",
    }
    assert "dominique" not in response.text.lower()


@pytest.mark.requirement("WF-ADM-0060-A")
def test_the_account_that_bears_the_address_of_a_person_left_is_named_as_it_reads_now(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # « Après anonymisation d'un compte désactivé, aucun écran — journal d'audit compris — ne
    # présente plus son nom ni son adresse » : a person relayed at the address of an account is
    # left without one (#707), and the report keeps her subject and that account's identifier, not
    # the address, which is the account's (#920).
    _, headers = person("users.read")
    holder = account(database, "Bernard", "Dominique", origin="directory")
    address = "dominique.bernard@example.org"
    relayed = ProviderAccount(
        "kc-7f3a",
        "Roux",
        "Camille",
        "Dominique.Bernard@example.org",
        is_federated=False,
        is_relayed=True,
    )
    task_id = deposit(database, queue)
    with database.transaction() as session:
        written = write_accounts(session, [relayed], [], NIGHT)
        record_report(session, SyncReport(task_id, NIGHT, 0, 0, 0, 0, written.skipped, []))
    entry = {"kind": "person", "user_id": str(holder), "subject": "kc-7f3a"}
    unnamed = {"last_name": None, "first_name": None, "email": None, "code": "ALREADY_EXISTS"}
    named = {"last_name": "Bernard", "first_name": "Dominique", "email": address}
    response = api.get(LATEST, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["skipped"] == [{**entry, **unnamed, **named}]
    anonymized(database, holder)
    response = api.get(LATEST, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["skipped"] == [{**entry, **unnamed}]
    assert address not in response.text.lower()
    with database.transaction() as session:
        stored = session.scalars(
            select(IdentitySyncReport.skipped).where(IdentitySyncReport.task_id == task_id)
        ).one()
    assert stored == [{**entry, **unnamed}]
    kept = json.dumps(stored).lower()
    assert all(personal not in kept for personal in (address, "roux", "camille"))


class Restoring(Watching):
    """The administration client, noting each identity given back, with the connections lent.

    The realm of test does not serve the administration API: the provider takes the identity
    back here, but refuses it to ``kc-taken``, whose address it holds for another account, and
    does not answer for ``kc-down``.
    """

    def __init__(self, keycloak: Keycloak, settings: ServiceSettings, database: Database) -> None:
        """Watch the pool of ``database``; nothing is given back yet."""
        super().__init__(keycloak, settings, database)
        self.given: list[tuple[str, LocalIdentity]] = []

    def change_identity(self, subject: str, identity: LocalIdentity) -> bool:
        """Note the identity given back, then take it, refuse it, or fail to answer."""
        self._note("change_identity")
        if subject == "kc-down":
            raise unavailable()
        self.given.append((subject, identity))
        return subject != "kc-taken"


def test_the_identity_of_a_local_account_is_given_back_as_it_is_read_with_no_connection_held(
    database: Database, keycloak: Keycloak, realm_settings: ServiceSettings, logs: Logs
) -> None:
    # Read again, in a transaction of its own, and given out of any (#669, #919): a change committed
    # since the reading is what the provider gets. One anonymised since is never given back
    # (WF-ADM-0060), and one the provider refuses or does not take is logged, the others given.
    for subject, last_name in (("kc-down", "Vidal"), ("kc-taken", "Roux"), ("kc-lucas", "Petit")):
        account(database, last_name, "Lou", idp_subject=subject)
    alix = account(database, "Moreau", "Alix", idp_subject="kc-alix")
    anonymized(database, alix)
    restoring = Restoring(keycloak, realm_settings, database)
    IdentitySync(restoring).restore(database.engine, ["kc-down", "kc-alix", "kc-taken", "kc-lucas"])
    assert restoring.given == [
        ("kc-taken", LocalIdentity("Roux", "Lou", "lou.roux@example.org")),
        ("kc-lucas", LocalIdentity("Petit", "Lou", "lou.petit@example.org")),
    ]
    assert restoring.held == [("change_identity", 0)] * 3
    assert [record["subject"] for record in logs.named("identity_sync.identity_not_restored")] == [
        "kc-down",
        "kc-taken",
    ]
    assert [record["subject"] for record in logs.named("identity_sync.identity_restored")] == [
        "kc-lucas"
    ]


class UndoneError(Exception):
    """What undoes the savepoint, or the transaction, of a test."""


def undone() -> None:
    """Undo the savepoint, or the transaction, this runs in."""
    raise UndoneError


@pytest.mark.requirement("WF-ARC-0090-A")
def test_what_waits_for_the_commit_is_dropped_with_the_savepoint_rolled_back(
    database: Database, queue: TaskQueue
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée » : a reading that fails
    # leaves the realm as it was too — what it registered in the savepoint of its run never runs,
    # though the worker commits the end of the task after.
    ran: list[str] = []
    with database.transaction() as session:
        with suppress(UndoneError), session.begin_nested():
            after_commit(session, lambda: ran.append("savepoint"))
            with session.begin_nested():
                after_commit(session, lambda: ran.append("within"))
            undone()
        after_commit(session, lambda: ran.append("root"))
    assert ran == ["root"]

    def failing(session: Session, _task: Task) -> None:
        after_commit(session, lambda: ran.append("task"))
        undone()

    task_id = deposit(database, queue)
    assert Worker(database, queue, {"identity_sync": failing}, "worker").run_task(task_id)
    assert task(database, task_id).status == "failed"
    assert ran == ["root"]


def test_what_waits_for_the_commit_runs_once_after_it_and_never_after_a_rollback(
    database: Database,
) -> None:
    ran: list[str] = []
    with database.transaction() as session:
        with session.begin_nested():
            after_commit(session, lambda: ran.append("released"))
        assert ran == []
        with suppress(UndoneError), session.begin_nested():
            undone()
    assert ran == ["released"]

    def rolled_back() -> None:
        with database.transaction() as session:
            after_commit(session, lambda: ran.append("root"))
            with session.begin_nested():
                after_commit(session, lambda: ran.append("savepoint"))
            undone()

    with pytest.raises(UndoneError):
        rolled_back()
    assert ran == ["released"]
