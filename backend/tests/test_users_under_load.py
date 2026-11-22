# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The administration of the accounts under load: a large directory, two administrators at once.

The reading of the accounts holds the lock of the rule of the last administrator for all its writes,
committed together (WF-ARC-0090): a write of the administration asked meanwhile waits for it. That
wait is measured here on five hundred persons of the directory, the effective of table 13, which the
test engenders in the directory the provider lists — the reading asks nothing of Keycloak once it
holds the lock, and what it holds it for is all in the database —, then bounded: a write that waits
longer than ``ADMINISTRATION_WAIT`` is refused (503), having written nothing (#924). Two
administrators who change each the account of the other queue on the same lock, and receive a
refusal of the rule, never a deadlock answered 500 (#930).
"""

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import psycopg
import pytest
import test_users_provider_reading
from access_rows import ADMINISTRATION, role
from fastapi.testclient import TestClient
from realm import KEY, TestRealm
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from support import ContractClient, Watching, bearer, nowhere, wait_for_a_lock
from task_handlers import deposit
from test_users_provider_reading import ADMINISTRATORS_WAITED_FOR, held

from waterfall.api import users as users_api
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles import administrators
from waterfall.core.access_roles.administrators import ADMINISTRATION_WAIT
from waterfall.core.access_roles.interface import Act, lock_administrators
from waterfall.core.resource_settings.interface import NodeWrite, create_node
from waterfall.core.users.interface import latest_report
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import (
    InvitationFailure,
    LocalIdentity,
    ProviderAccount,
    RealmAccount,
)
from waterfall.worker import identity_sync
from waterfall.worker.identity_sync import IdentitySync
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from collections.abc import Callable

    from httpx2 import Response
    from openapi_core import OpenAPI
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

correlation = test_users_provider_reading.correlation

# The effective of the accounts of table 13 (§4.6.2).
EFFECTIVE = 500
NOON = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
# The bound of the waits of the administration a test of the refusal sets, not to wait ten seconds.
SHORT_WAIT = timedelta(milliseconds=300)


class Provider(Watching):
    """The administration client of the API and of the worker, as a provider that does as asked.

    The realm of test serves no administration API. This one lists the persons of its directory
    and reads them, creates the accounts asked, takes an identity, removes an account and closes
    its sessions, noting each call with the connections lent.
    """

    def __init__(self, keycloak: Keycloak, settings: ServiceSettings, database: Database) -> None:
        """Watch the pool of ``database``; the directory is empty, nothing is removed yet."""
        super().__init__(keycloak, settings, database)
        self.directory: dict[str, RealmAccount] = {}
        self.removed: list[str] = []

    def synchronize_directories(self) -> int:
        """Say every directory read again."""
        return 0

    def list_accounts(self) -> list[RealmAccount]:
        """List the accounts of the directory."""
        self._note("list_accounts")
        return list(self.directory.values())

    def read_account(self, subject: str) -> ProviderAccount | None:
        """Read an account of the directory, or ``None`` if it holds none of that subject."""
        self._note("read_account")
        found = self.directory.get(subject)
        if found is None:
            return None
        return ProviderAccount(
            found.subject,
            found.last_name,
            found.first_name,
            found.email,
            is_federated=found.is_federated,
            is_relayed=False,
        )

    def create_account(self, identity: LocalIdentity) -> str | None:
        """Hold the account under a subject of its own."""
        self._note("create_account")
        del identity
        return f"kc-{uuid4()}"

    def send_invitation(self, subject: str) -> InvitationFailure | None:
        """Say the invitation sent."""
        del subject

    def change_identity(self, subject: str, identity: LocalIdentity) -> bool:
        """Take the identity."""
        self._note("change_identity")
        del subject, identity
        return True

    def remove_account(self, subject: str) -> None:
        """Note the account removed."""
        self._note("remove_account")
        self.removed.append(subject)

    def close_sessions(self, subject: str) -> None:
        """Close nothing: the realm of test holds no session."""
        self._note("close_sessions")
        del subject


@dataclass(frozen=True, slots=True)
class Stage:
    """The platform of a test: its database, the API, the provider of both, the realm of tokens."""

    database: Database
    api: ContractClient
    provider: Provider
    realm: TestRealm

    def headers(self, row: dict[str, Any]) -> dict[str, str]:
        """Give the header of a token of the account."""
        return bearer(self.realm.token(str(row["idp_subject"]), KEY))


@pytest.fixture
def stage(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    realm: TestRealm,
) -> Stage:
    """Give the platform of a test, whose provider does as it is asked."""
    provider = Provider(keycloak, realm_settings, database)
    app = create_app(Services(database, keycloak, provider, *nowhere()))
    api = ContractClient(TestClient(app, raise_server_exceptions=False), contract)
    return Stage(database, api, provider, realm)


def listed(row: dict[str, Any], *, is_federated: bool) -> RealmAccount:
    """Describe an account as the provider lists it, as Waterfall holds it."""
    return RealmAccount(
        str(row["idp_subject"]),
        str(row["last_name"]),
        str(row["first_name"]),
        str(row["email"]),
        is_federated=is_federated,
        created_at=NOON,
    )


def engendered(count: int) -> dict[str, RealmAccount]:
    """Engender persons of the directory, each of her subject, her names and her address."""
    persons = (
        RealmAccount(
            f"kc-annuaire-{rank:04d}",
            f"Annuaire{rank:04d}",
            "Personne",
            f"personne.{rank:04d}@annuaire.test",
            is_federated=True,
            created_at=NOON,
        )
        for rank in range(count)
    )
    return {person.subject: person for person in persons}


def administrator(database: Database, *rows: dict[str, Any]) -> None:
    """Give the accounts the administration, as one role they hold together."""
    holders = tuple(row["id"] for row in rows)
    permissions = (*ADMINISTRATION, "users.read", "access_roles.read")
    role(database, f"Administration {uuid4().hex[:6]}", permissions=permissions, holders=holders)


def read_by_the_worker(
    database: Database, queue: TaskQueue, provider: Provider, meanwhile: Callable[[], None]
) -> float:
    """Have a worker read the accounts; run ``meanwhile`` once it holds the lock; give how long.

    How long from then until the reading is committed: the wait of whatever queued behind it.
    """
    started: list[float] = []
    followed = identity_sync.follow

    def follow_then(session: Session, person: ProviderAccount, at: datetime) -> object:
        if not started:
            started.append(time.perf_counter())
            meanwhile()
        return followed(session, person, at)

    task_id = deposit(database, queue)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(identity_sync, "follow", follow_then)
        reading = IdentitySync(provider)
        assert Worker(database, queue, {"identity_sync": reading}, "worker").run_task(task_id)
    return time.perf_counter() - started[0]


@pytest.mark.story("US-3020")
def test_a_change_of_an_account_waits_for_a_reading_of_five_hundred_persons_within_the_bound(
    stage: Stage, queue: TaskQueue
) -> None:
    # #924, measured: the reading of five hundred persons of the directory holds the lock of the
    # rule while it creates their accounts, then while it deactivates them all, the directory
    # emptied. An administrator who attaches an account meanwhile waits for each, and passes
    # within the bound, the reading of the effective of table 13 refusing no write.
    database, provider = stage.database, stage.provider
    with database.transaction() as session:
        camille = held(session, last_name="Martin", first_name="Camille", origin="local")
        paul = held(session, last_name="Durand", first_name="Paul", email="paul@example.org")
        node = create_node(session, NodeWrite("DIR", "Direction", None), Act(None, NOON)).node_id
    administrator(database, camille)
    headers = stage.headers(camille)
    kept = {
        camille["idp_subject"]: listed(camille, is_federated=False),
        paul["idp_subject"]: listed(paul, is_federated=True),
    }
    path = f"/api/v1/users/{paul['id']}"
    bound = ADMINISTRATION_WAIT.total_seconds()

    def reading_while_attaching(attached: str | None, version: int) -> tuple[int, float, float]:
        answers: list[tuple[int, float]] = []

        def attach() -> None:
            sent = {"org_node_id": attached, "lock_version": version}
            asked = time.perf_counter()
            status = stage.api.patch(path, headers=headers, json=sent).status_code
            answers.append((status, time.perf_counter() - asked))

        concurrent = threading.Thread(target=attach)

        def meanwhile() -> None:
            concurrent.start()
            wait_for_a_lock(database)

        held_for = read_by_the_worker(database, queue, provider, meanwhile)
        concurrent.join(bound + 5)
        assert not concurrent.is_alive()
        ((status, waited),) = answers
        return status, waited, held_for

    provider.directory = {**kept, **engendered(EFFECTIVE)}
    status, waited, held_for = reading_while_attaching(str(node), 0)
    assert status == 200
    assert waited < bound
    assert held_for < bound
    with database.transaction() as session:
        report = latest_report(session)
        assert report is not None
        assert report.created == EFFECTIVE
        assert session.get_one(UserAccount, paul["id"]).org_node_id == node

    provider.directory = kept
    status, waited, held_for = reading_while_attaching(None, 1)
    assert status == 200
    assert waited < bound
    assert held_for < bound
    with database.transaction() as session:
        report = latest_report(session)
        assert report is not None
        assert report.deactivated == EFFECTIVE
        active = select(func.count()).where(UserAccount.state == "active")
        assert session.scalar(active) == 2
        assert session.get_one(UserAccount, paul["id"]).org_node_id is None


# Each write of the administration that waits for the lock of the rule: the method, the path and
# the body, ``{account}`` the account written, ``{role}`` a role it holds.
BOUNDED_ROUTES: dict[str, tuple[str, str, dict[str, Any] | None]] = {
    "updateUser": ("PATCH", "/users/{account}", {"org_node_id": None, "lock_version": 0}),
    "anonymizeUser": ("POST", "/users/{account}/anonymization", {"lock_version": 0}),
    "createPasswordSetupLink": ("POST", "/users/{account}/password-link", None),
    "resendInvitation": ("POST", "/users/{account}/invitation", None),
    "createUser": (
        "POST",
        "/users",
        {"last_name": "Nouveau", "first_name": "Louis", "email": "louis@example.org"},
    ),
    "setUserActivation": (
        "PUT",
        "/users/{account}/activation",
        {"is_active": False, "lock_version": 0},
    ),
    "setUserAccessRoles": (
        "PUT",
        "/users/{account}/access-roles",
        {"access_role_ids": [], "lock_version": 0},
    ),
    "updateAccessRole": (
        "PATCH",
        "/access-roles/{role}",
        {"label": "Planification", "permissions": [], "lock_version": 0},
    ),
    "deleteAccessRole": ("DELETE", "/access-roles/{role}?lock_version=0", None),
}


@pytest.mark.story("US-3020")
@pytest.mark.parametrize("operation", list(BOUNDED_ROUTES))
def test_a_write_of_the_administration_that_waits_beyond_the_bound_is_refused_and_writes_nothing(
    stage: Stage, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    # #924, bounded: a reading of a directory larger than the bound allows holds the lock of the
    # rule; a write of the administration asked meanwhile waits the bound, then is refused, the
    # database named (503) — nothing written, and an account the provider created withdrawn.
    monkeypatch.setattr(administrators, "ADMINISTRATION_WAIT", SHORT_WAIT)
    database, provider = stage.database, stage.provider
    with database.transaction() as session:
        camille = held(session, last_name="Martin", first_name="Camille")
        paul = held(session, last_name="Durand", first_name="Paul", email="paul@example.org")
    administrator(database, camille)
    planning = role(
        database, "Planification", permissions=("planning.read",), holders=(paul["id"],)
    )
    method, template, body = BOUNDED_ROUTES[operation]
    path = f"/api/v1{template.format(account=paul['id'], role=planning)}"
    answers: list[tuple[Response, float]] = []

    def ask() -> None:
        asked = time.perf_counter()
        answer = stage.api.request(method, path, headers=stage.headers(camille), json=body)
        answers.append((answer, time.perf_counter() - asked))

    concurrent = threading.Thread(target=ask)
    with database.transaction() as holding:
        lock_administrators(holding)
        concurrent.start()
        # Answered while the lock is held still: a wait without a bound would hold the request.
        concurrent.join(SHORT_WAIT.total_seconds() + 5)
        assert not concurrent.is_alive(), "the request still waits"
    ((answer, waited),) = answers
    assert (answer.status_code, answer.json()["code"], answer.json()["params"]) == (
        503,
        "COMPONENT_UNAVAILABLE",
        {"component": "database"},
    )
    assert SHORT_WAIT.total_seconds() <= waited < ADMINISTRATION_WAIT.total_seconds()
    with database.transaction() as session:
        accounts = session.scalars(select(UserAccount).order_by(UserAccount.last_name)).all()
        assert [(each.last_name, each.lock_version, each.state) for each in accounts] == [
            ("Durand", 0, "active"),
            ("Martin", 0, "active"),
        ]
        assert session.scalars(select(AuditEntry.id)).all() == []
    created = [call for call, _ in provider.held if call == "create_account"]
    assert len(provider.removed) == len(created) == (operation == "createUser")


@pytest.mark.story("US-3020")
def test_an_error_of_the_database_but_a_lock_not_obtained_stays_the_error_nobody_expected(
    stage: Stage, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #924: the lock not obtained within the bound alone is answered 503; the database that fails
    # otherwise is the internal error it was (500), which says nothing of it.
    statement = "SELECT set_config('lock_timeout', '10000ms', true)"
    closed = psycopg.OperationalError("closed")

    def failing(session: Session) -> None:
        del session
        raise OperationalError(statement, {}, closed)

    monkeypatch.setattr(users_api, "bound_administration_waits", failing)
    with stage.database.transaction() as session:
        camille = held(session, last_name="Martin", first_name="Camille")
    administrator(stage.database, camille)
    sent = {"org_node_id": None, "lock_version": 0}
    path = f"/api/v1/users/{camille['id']}"
    answer = stage.api.patch(path, headers=stage.headers(camille), json=sent)
    assert (answer.status_code, answer.json()["code"]) == (500, "INTERNAL_ERROR")
    assert "closed" not in answer.text


def queued(
    database: Database, asked: list[Callable[[], tuple[int, dict[str, Any]]]]
) -> list[tuple[int, dict[str, Any]]]:
    """Ask the requests together while the lock of the rule is held, then release it; give answers.

    Each waits for the lock before any row of an account; released, they pass one after another.
    """
    answers: list[tuple[int, dict[str, Any]]] = []

    def run(ask: Callable[[], tuple[int, dict[str, Any]]]) -> None:
        answers.append(ask())

    threads = [threading.Thread(target=run, args=(ask,)) for ask in asked]
    with database.transaction() as holding:
        lock_administrators(holding)
        for thread in threads:
            thread.start()
        deadline = time.monotonic() + 10
        with database.engine.connect() as watching:
            while watching.scalar(ADMINISTRATORS_WAITED_FOR) != len(threads):
                assert time.monotonic() < deadline, "the requests do not all wait for the lock"
                watching.rollback()
                time.sleep(0.05)
    for thread in threads:
        thread.join(15)
        assert not thread.is_alive()
    return answers


def answered(
    api: ContractClient, method: str, path: str, **kwargs: Any
) -> Callable[[], tuple[int, dict[str, Any]]]:
    """Give a request to ask later, which gives its status and its body."""

    def ask() -> tuple[int, dict[str, Any]]:
        response = api.request(method, path, **kwargs)
        return response.status_code, response.json()

    return ask


# Each change of an account by its administrator, the other administrator's: the method, the end
# of the path after the account, the body — of the node and of the role a test makes —, and the two
# answers, sorted.
CROSSED: dict[str, tuple[str, str, Callable[[UUID, UUID], dict[str, Any]], list[int]]] = {
    "updateUser": (
        "PATCH",
        "",
        lambda node, _: {"org_node_id": str(node), "lock_version": 0},
        [200, 200],
    ),
    "setUserActivation": (
        "PUT",
        "/activation",
        lambda _node, _role: {"is_active": False, "lock_version": 0},
        [200, 409],
    ),
    "setUserAccessRoles": (
        "PUT",
        "/access-roles",
        lambda _, planning: {"access_role_ids": [str(planning)], "lock_version": 0},
        [200, 409],
    ),
}


@pytest.mark.story("US-3020")
@pytest.mark.parametrize("operation", list(CROSSED))
def test_two_administrators_who_change_each_the_account_of_the_other_are_never_answered_500(
    stage: Stage, operation: str
) -> None:
    # #930: Camille changes the account of Dominique while Dominique changes hers. Each takes the
    # lock of the rule before the row of the account it changes, then reads its author's row: they
    # pass one after the other, and the second is judged on what the first left — a deactivation
    # or roles that would leave no administrator refused (409) —, never a deadlock (500).
    database = stage.database
    with database.transaction() as session:
        camille = held(session, last_name="Martin", first_name="Camille")
        dominique = held(session, last_name="Roux", first_name="Dominique", email="d@example.org")
        node = create_node(session, NodeWrite("DIR", "Direction", None), Act(None, NOON)).node_id
    administrator(database, camille, dominique)
    planning = role(database, "Planification", permissions=("planning.read",))
    method, ending, body, outcomes = CROSSED[operation]
    answers = queued(
        database,
        [
            answered(
                stage.api,
                method,
                f"/api/v1/users/{target['id']}{ending}",
                headers=stage.headers(author),
                json=body(node, planning),
            )
            for author, target in ((camille, dominique), (dominique, camille))
        ],
    )
    assert sorted(status for status, _ in answers) == outcomes
    with database.transaction() as session:
        authors = set(session.scalars(select(AuditEntry.actor_user_id)))
    assert len(authors) == outcomes.count(200)
    assert authors <= {camille["id"], dominique["id"]}


@pytest.mark.story("US-3020")
def test_an_account_created_at_the_address_another_administrator_gives_the_creator_is_refused_once(
    stage: Stage,
) -> None:
    # #930: Camille creates an account at an address while Dominique gives that address to the
    # local account of Camille. The creation holding no row before the lock of the rule, nor the
    # change before it, one of the two passes and the other is refused, the address taken (409),
    # never a deadlock (500); the account the provider created for a refused creation is withdrawn.
    address = "louise.neuve@example.org"
    database = stage.database
    with database.transaction() as session:
        camille = held(
            session, last_name="Martin", first_name="Camille", origin="local", email="c@example.org"
        )
        dominique = held(session, last_name="Roux", first_name="Dominique", email="d@example.org")
    administrator(database, camille, dominique)
    created = {"last_name": "Neuve", "first_name": "Louise", "email": address}
    changed = {"email": address, "lock_version": 0}
    answers = queued(
        database,
        [
            answered(
                stage.api, "POST", "/api/v1/users", headers=stage.headers(camille), json=created
            ),
            answered(
                stage.api,
                "PATCH",
                f"/api/v1/users/{camille['id']}",
                headers=stage.headers(dominique),
                json=changed,
            ),
        ],
    )
    statuses = sorted(status for status, _ in answers)
    assert statuses in ([200, 409], [201, 409])
    (refused,) = [problem for status, problem in answers if status == 409]
    assert refused["code"] == "ALREADY_EXISTS"
    with database.transaction() as session:
        holders = session.scalars(select(UserAccount.id).where(UserAccount.email == address)).all()
    assert len(holders) == 1
    assert len(stage.provider.removed) == (statuses == [200, 409])
