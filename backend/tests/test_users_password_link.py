# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The link that sets the password of an account, asked for through the API (US-0350).

The caller, Camille Martin, may consult and change the accounts. Keycloak is the realm of test,
which serves keys and nothing of the administration API: what the API refuses before asking the
extension for a link is tried here; the link itself, made by the extension, and its inscription in
the journal, against the platform (``test_keycloak_sign_in.py``).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, anonymized_account, role
from fastapi.testclient import TestClient
from realm import KEY, TestRealm
from sqlalchemy import func, select
from support import ContractClient, Logs, Watching, bearer, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.interface import inscribe_password_link
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.errors import ConflictError
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.keycloak_admin import InvitationFailure
    from waterfall.platform.settings import ServiceSettings

USERS = "/api/v1/users"
CAMILLE = "6c2d4e1f-3a5b-4c7d-8e9f-0a1b2c3d4e5f"
NOON = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


@pytest.fixture
def watching(keycloak: Keycloak, realm_settings: ServiceSettings, database: Database) -> Watching:
    """Give the administration client of the API, which notes each call to Keycloak."""
    return Watching(keycloak, realm_settings, database)


@pytest.fixture
def client(
    contract: OpenAPI, database: Database, keycloak: Keycloak, watching: Watching
) -> ContractClient:
    """Give a client of the API whose administration client is watched."""
    app = create_app(Services(database, keycloak, watching, *nowhere()))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def caller(database: Database, realm: TestRealm, *permissions: str) -> dict[str, str]:
    """Write Camille Martin's account with a role of ``permissions``; give her token's header."""
    held = role(database, "Gestion des comptes", permissions=permissions)
    account(database, "Martin", "Camille", roles=(held,), idp_subject=CAMILLE)
    return bearer(realm.token(CAMILLE, KEY))


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Let the caller consult and change the accounts."""
    return caller(database, realm, "users.read", "users.write")


def link_of(client: ContractClient, headers: dict[str, str], user_id: UUID) -> Any:
    """Ask the API for the password link of an account."""
    return client.post(f"{USERS}/{user_id}/password-link", headers=headers)


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


type Traces = Callable[[], tuple[list[tuple[str, int]], int]]


@pytest.fixture
def traces(watching: Watching, database: Database) -> Traces:
    """Give what a request left: the calls to Keycloak, and the number of inscriptions."""

    def read() -> tuple[list[tuple[str, int]], int]:
        with database.transaction() as session:
            count = session.scalar(select(func.count()).select_from(AuditEntry))
        return watching.held, count or 0

    return read


@pytest.mark.parametrize(
    "case",
    [
        ("directory", "active", "is_local_account"),
        ("identity_provider", "active", "is_local_account"),
        ("local", "deactivated", "is_active_account"),
        # Lacking both, it is refused by the first.
        ("directory", "deactivated", "is_local_account"),
    ],
    ids=["of the directory", "of an external provider", "deactivated", "both"],
)
@pytest.mark.requirement("WF-ADM-0140-A")
def test_an_account_that_is_not_local_or_is_deactivated_has_no_link(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    traces: Traces,
    case: tuple[str, str, str],
) -> None:
    # « Un compte importé n'a pas d'écran de mot de passe » : it authenticates with its directory,
    # and Waterfall gives it no link that would set one. The provider is not even asked.
    origin, state, condition = case
    user_id = account(database, "Montgolfier", "Jeanne", origin=origin, state=state)
    response = link_of(client, headers, user_id)
    assert refusal(response) == (409, "STATE_FORBIDS_OPERATION", {"missing_condition": condition})
    assert traces() == ([], 0)


def invitation_of(client: ContractClient, headers: dict[str, str], user_id: UUID) -> Any:
    """Ask the API to send again the invitation of an account."""
    return client.post(f"{USERS}/{user_id}/invitation", headers=headers)


@pytest.mark.parametrize(
    "case",
    [
        (link_of, "local", "is_not_anonymized"),
        (invitation_of, "local", "is_not_anonymized"),
        (link_of, "directory", "is_local_account"),
        (invitation_of, "directory", "is_local_account"),
    ],
    ids=["link", "invitation", "link of the directory", "invitation of the directory"],
)
@pytest.mark.requirement("WF-ADM-0060-A")
def test_an_anonymized_account_has_neither_link_nor_invitation_and_is_refused_as_such(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    traces: Traces,
    case: tuple[Callable[[ContractClient, dict[str, str], UUID], Any], str, str],
) -> None:
    # « sa réactivation est refusée » : the anonymisation is irreversible, so the refusal of a
    # local account anonymised names it, not its deactivation, which it implies; one that is not
    # local lacks that first. Nothing is asked of the provider, nor inscribed.
    ask, origin, condition = case
    user_id = anonymized_account(database, origin=origin)
    response = ask(client, headers, user_id)
    assert refusal(response) == (409, "STATE_FORBIDS_OPERATION", {"missing_condition": condition})
    assert traces() == ([], 0)


@pytest.mark.parametrize(
    "case",
    [
        ("directory", "active", "is_local_account"),
        ("local", "deactivated", "is_active_account"),
        # Lacking both, it is refused by the first.
        ("directory", "deactivated", "is_local_account"),
    ],
    ids=["not local", "deactivated", "both"],
)
@pytest.mark.requirement("WF-ADM-0140-A")
def test_an_account_that_is_not_local_or_is_deactivated_has_no_invitation(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    traces: Traces,
    case: tuple[str, str, str],
) -> None:
    # As for its link: no mail leaves for an account that authenticates elsewhere or may not sign
    # in.
    origin, state, condition = case
    user_id = account(database, "Montgolfier", "Jeanne", origin=origin, state=state)
    response = invitation_of(client, headers, user_id)
    assert refusal(response) == (409, "STATE_FORBIDS_OPERATION", {"missing_condition": condition})
    assert traces() == ([], 0)


@pytest.mark.requirement("WF-ADM-0060-A")
def test_a_link_made_for_an_account_anonymized_meanwhile_is_neither_inscribed_nor_given(
    database: Database, session: Session
) -> None:
    user_id = anonymized_account(database)
    with logging_context(correlation_id="link"), pytest.raises(ConflictError) as refused:
        inscribe_password_link(session, user_id, Act(None, NOON))
    assert refused.value.params == {"missing_condition": "is_not_anonymized"}
    assert session.scalars(select(AuditEntry)).all() == []


def test_an_account_that_does_not_exist_has_no_link(
    client: ContractClient, headers: dict[str, str], traces: Traces
) -> None:
    response = link_of(client, headers, uuid4())
    assert refusal(response)[:2] == (404, "NOT_FOUND")
    assert traces() == ([], 0)


@pytest.mark.parametrize(
    "case",
    [(("users.read",), 403), (("users.write",), 404)],
    ids=["without changing the accounts", "without consulting them"],
)
def test_a_link_is_given_only_to_who_may_change_the_accounts(
    client: ContractClient,
    database: Database,
    realm: TestRealm,
    traces: Traces,
    case: tuple[tuple[str, ...], int],
) -> None:
    permissions, status = case
    user_id = account(database, "Montgolfier", "Jeanne")
    response = link_of(client, caller(database, realm, *permissions), user_id)
    assert response.status_code == status
    assert traces() == ([], 0)


def test_a_link_keycloak_could_not_make_is_neither_given_nor_inscribed(
    client: ContractClient, database: Database, headers: dict[str, str], traces: Traces
) -> None:
    # The realm of test serves no extension: Keycloak fails, asked with no connection held (#669).
    user_id = account(database, "Montgolfier", "Jeanne")
    response = link_of(client, headers, user_id)
    assert refusal(response) == (
        503,
        "COMPONENT_UNAVAILABLE",
        {"component": "identity_provider"},
    )
    assert traces() == ([("make_password_link", 0)], 0)


def test_a_link_made_is_inscribed_by_its_author_without_anything_of_the_link(
    database: Database, session: Session
) -> None:
    author = account(database, "Martin", "Camille")
    user_id = account(database, "Montgolfier", "Jeanne")
    with logging_context(correlation_id="link"):
        inscribe_password_link(session, user_id, Act(author, NOON))
    entry = session.scalars(select(AuditEntry)).one()
    assert (entry.action, entry.object_id, entry.object_label) == (
        "password_link_create",
        user_id,
        "Jeanne Montgolfier",
    )
    assert (entry.actor_user_id, entry.actor_display_name, entry.occurred_at, entry.params) == (
        author,
        "Camille Martin",
        NOON,
        {},
    )


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_made_for_an_account_deactivated_meanwhile_is_neither_inscribed_nor_given(
    database: Database, session: Session
) -> None:
    # The account is read again under a lock once the provider made the link (#669).
    user_id = account(database, "Montgolfier", "Jeanne", state="deactivated")
    with logging_context(correlation_id="link"), pytest.raises(ConflictError) as refused:
        inscribe_password_link(session, user_id, Act(None, NOON))
    assert refused.value.params == {"missing_condition": "is_active_account"}
    assert session.scalars(select(AuditEntry)).all() == []


class Inviting(Watching):
    """The administration client whose mail leaves, or fails, as told; it asks Keycloak for none.

    Each sending notes the entries the journal held at that moment, and ``Watching`` the
    connections lent by the pool: the order of the steps is read from them.
    """

    def __init__(self, keycloak: Keycloak, settings: ServiceSettings, database: Database) -> None:
        """Tell the outcome of the sendings, none by default; nothing is sent yet."""
        super().__init__(keycloak, settings, database)
        self.outcome: InvitationFailure | None = None
        self.entries_seen: list[int] = []
        self.subjects: list[str] = []
        self._journal = database

    def send_invitation(self, subject: str) -> InvitationFailure | None:
        """Note, then give the outcome told."""
        self._note("send_invitation")
        self.subjects.append(subject)
        self.entries_seen.append(len(journal(self._journal)))
        return self.outcome


@pytest.fixture
def inviting(keycloak: Keycloak, realm_settings: ServiceSettings, database: Database) -> Inviting:
    """Give the administration client whose sendings are told."""
    return Inviting(keycloak, realm_settings, database)


@pytest.fixture
def inviting_client(
    contract: OpenAPI, database: Database, keycloak: Keycloak, inviting: Inviting
) -> ContractClient:
    """Give a client of the API whose administration client sends no real mail."""
    app = create_app(Services(database, keycloak, inviting, *nowhere()))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def journal(database: Database) -> list[AuditEntry]:
    """Give the entries of the journal."""
    with database.transaction() as session:
        entries = session.scalars(select(AuditEntry)).all()
        session.expunge_all()
    return list(entries)


@pytest.mark.requirement("WF-ADM-0140-A")
@pytest.mark.requirement("WF-EXP-0040-A")
def test_an_invitation_sent_again_is_answered_empty_and_inscribed_once_after_its_sending(
    inviting_client: ContractClient,
    database: Database,
    headers: dict[str, str],
    inviting: Inviting,
) -> None:
    user_id = account(database, "Montgolfier", "Jeanne")
    response = invitation_of(inviting_client, headers, user_id)
    assert (response.status_code, response.content) == (204, b"")
    # Read under a lock, sent with no connection held and nothing inscribed yet, then inscribed.
    assert inviting.held == [("send_invitation", 0)]
    assert inviting.entries_seen == [0]
    assert len(inviting.subjects) == 1
    (entry,) = journal(database)
    assert (entry.action, entry.object_id, entry.params) == ("password_link_create", user_id, {})
    assert entry.actor_display_name == "Camille Martin"
    assert entry.actor_user_id is not None


@pytest.mark.requirement("WF-ADM-0140-A")
def test_an_invitation_of_an_account_the_provider_holds_as_no_local_one_is_refused_as_its_link(
    inviting_client: ContractClient,
    database: Database,
    headers: dict[str, str],
    inviting: Inviting,
    logs: Logs,
) -> None:
    # #2226: a local account the provider has linked since to an identity of an external provider.
    # Waterfall still holds it as local; the extension refuses it as not local. The invitation is
    # refused as its link is (createPasswordSetupLink), nothing inscribed, and the log says no
    # invitation failed.
    inviting.outcome = "not_local"
    user_id = account(database, "Montgolfier", "Jeanne")
    response = invitation_of(inviting_client, headers, user_id)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "is_local_account"},
    )
    assert inviting.held == [("send_invitation", 0)]
    assert journal(database) == []
    assert logs.named("account.invitation_not_sent") == []
    assert logs.named("account.invitation_sent") == []


@pytest.mark.parametrize("outcome", ["not_sent", "no_mail_server", "provider_unavailable"])
@pytest.mark.requirement("WF-ADM-0140-A")
@pytest.mark.requirement("WF-EXP-0040-A")
def test_an_invitation_that_did_not_leave_is_never_presented_as_sent_nor_inscribed(
    inviting_client: ContractClient,
    database: Database,
    headers: dict[str, str],
    inviting: Inviting,
    outcome: InvitationFailure,
) -> None:
    inviting.outcome = outcome
    user_id = account(database, "Montgolfier", "Jeanne")
    response = invitation_of(inviting_client, headers, user_id)
    assert refusal(response) == (
        503,
        "COMPONENT_UNAVAILABLE",
        {"component": "identity_provider"},
    )
    assert inviting.held == [("send_invitation", 0)]
    assert journal(database) == []
