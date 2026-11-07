# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The attachment of an account to a node of the organisation (US-0840, WF-ADM-0030).

An administrator attaches an account to a node, changes it or withdraws it; the account is read
with its node and the label of it as it is today; the table of the accounts is filtered and sorted
on it. The attachment gives no right, and a change of it is inscribed in the journal of audit as a
field of the account (#1740).
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from realm import KEY, TestRealm
from sqlalchemy import select
from support import ContractClient, bearer

import waterfall
from waterfall.api.contract.models import AuditParams
from waterfall.core.resource_settings.interface import (
    NodeWrite,
    create_node,
    set_activation,
)
from waterfall.core.users.interface import (
    Identity,
    IdentityChange,
    change_account,
    create_local_account,
    read_account,
)
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Iterator

    from waterfall.platform.database import Database

USERS = "/api/v1/users"
ME = "/api/v1/me"
SUBJECT = "6c2d4e1f-3a5b-4c7d-8e9f-0a1b2c3d4e5f"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
DAY = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
ACT = Act(CALLER, DAY)


@pytest.fixture(autouse=True)
def correlated() -> Iterator[None]:
    """Run each test under a correlation, as a request is: the journal refuses an action without."""
    with logging_context(correlation_id="attachment-of-an-account"):
        yield


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write the account of the caller, who consults and changes the accounts; give her header."""
    held = role(database, "Gestion des comptes", permissions=("users.read", "users.write"))
    account(
        database,
        "Martin",
        "Camille",
        roles=(held,),
        id=CALLER,
        idp_subject=SUBJECT,
        email="camille.martin@example.org",
    )
    return bearer(realm.token(SUBJECT, KEY))


def node(database: Database, code: str, label: str, parent: UUID | None = None) -> UUID:
    """Create a node of the organisation, by the module that owns the tree; give its identifier."""
    with database.transaction() as session:
        return create_node(session, NodeWrite(code, label, parent), Act(None, DAY)).node_id


def deactivate(database: Database, node_id: UUID) -> None:
    """Deactivate a node, by the module that owns the tree."""
    with database.transaction() as session:
        set_activation(session, node_id, is_active=False, lock_version=0, act=Act(None, DAY))


def attach(api: ContractClient, headers: dict[str, str], user_id: UUID, **sent: object) -> Any:
    """Change an account by the API, at the version it is read at."""
    version = api.get(f"{USERS}/{user_id}", headers=headers).json()["lock_version"]
    return api.patch(f"{USERS}/{user_id}", headers=headers, json={"lock_version": version, **sent})


def table(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Read the table of the accounts and give the names of those it keeps, in order."""
    response = api.get(f"{USERS}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return [f"{each['last_name']} {each['first_name']}" for each in response.json()["items"]]


@pytest.mark.requirement("WF-ADM-0030-A")
def test_an_account_is_attached_to_a_node_changed_and_withdrawn_by_the_api(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # « updateUser écrit org_node_id » : the node and its label are read back, by the answer, by
    # ``getUser`` and by the table; the version advances at each change.
    bureau = node(database, "BE", "Bureau d'études")
    atelier = node(database, "AT", "Atelier", bureau)
    jeanne = account(database, "Montgolfier", "Jeanne")
    given = attach(api, headers, jeanne, org_node_id=str(bureau))
    assert given.status_code == 200, given.text
    assert (given.json()["org_node_id"], given.json()["org_node_label"]) == (
        str(bureau),
        "Bureau d'études",
    )
    assert given.json()["lock_version"] == 1
    changed = attach(api, headers, jeanne, org_node_id=str(atelier))
    assert (changed.json()["org_node_label"], changed.json()["lock_version"]) == ("Atelier", 2)
    read = api.get(f"{USERS}/{jeanne}", headers=headers).json()
    assert (read["org_node_id"], read["org_node_label"]) == (str(atelier), "Atelier")
    listed = api.get(f"{USERS}?search=montgolfier", headers=headers).json()["items"][0]
    assert (listed["org_node_id"], listed["org_node_label"]) == (str(atelier), "Atelier")
    withdrawn = attach(api, headers, jeanne, org_node_id=None)
    assert (withdrawn.json()["org_node_id"], withdrawn.json()["org_node_label"]) == (None, None)
    assert withdrawn.json()["lock_version"] == 3


@pytest.mark.requirement("WF-ADM-0030-A")
def test_a_change_that_does_not_send_the_attachment_keeps_it_and_one_that_repeats_it_writes_nothing(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    bureau = node(database, "BE", "Bureau d'études")
    jeanne = account(database, "Montgolfier", "Jeanne", org_node_id=bureau)
    kept = attach(api, headers, jeanne, first_name="Jeanne")
    assert kept.status_code == 200
    assert (kept.json()["org_node_id"], kept.json()["lock_version"]) == (str(bureau), 0)
    repeated = attach(api, headers, jeanne, org_node_id=str(bureau))
    assert (repeated.json()["org_node_id"], repeated.json()["lock_version"]) == (str(bureau), 0)
    nothing = attach(api, headers, account(database, "Roux", "Inès"), org_node_id=None)
    assert (nothing.json()["org_node_id"], nothing.json()["lock_version"]) == (None, 0)


@pytest.mark.requirement("WF-ADM-0030-A")
def test_a_node_unknown_or_deactivated_is_refused_for_an_account_not_yet_attached_to_it(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # 422 on /org_node_id, as at the creation of a role: UNKNOWN_ORG_NODE, and
    # INACTIVE_REFERENCE_OBJECT for a node the reference has deactivated.
    off = node(database, "OFF", "Éteint")
    deactivate(database, off)
    jeanne = account(database, "Montgolfier", "Jeanne")
    for sent, code in ((uuid4(), "UNKNOWN_ORG_NODE"), (off, "INACTIVE_REFERENCE_OBJECT")):
        refused = attach(api, headers, jeanne, org_node_id=str(sent))
        assert refused.status_code == 422
        assert refused.json()["fields"] == [{"pointer": "/org_node_id", "code": code}]
    unchanged = api.get(f"{USERS}/{jeanne}", headers=headers).json()
    assert (unchanged["org_node_id"], unchanged["lock_version"]) == (None, 0)


@pytest.mark.requirement("WF-ADM-0030-A")
def test_an_account_attached_to_a_node_since_deactivated_keeps_it_and_shows_its_label(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    # The label is resolved at the reading, active or deactivated; the node held, sent again with
    # the form of the account, is no new attachment and is not refused.
    off = node(database, "OFF", "Éteint")
    jeanne = account(database, "Montgolfier", "Jeanne", org_node_id=off)
    deactivate(database, off)
    read = api.get(f"{USERS}/{jeanne}", headers=headers).json()
    assert (read["org_node_id"], read["org_node_label"]) == (str(off), "Éteint")
    again = attach(api, headers, jeanne, first_name="Jeanne", org_node_id=str(off))
    assert again.status_code == 200
    assert again.json()["org_node_label"] == "Éteint"
    me_listing = api.get(f"{USERS}?search=jeanne", headers=headers).json()["items"][0]
    assert me_listing["org_node_label"] == "Éteint"


@pytest.mark.requirement("WF-ADM-0030-A")
def test_the_account_of_the_caller_is_read_with_its_node_and_its_label(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    bureau = node(database, "BE", "Bureau d'études")
    account(database, "Moreau", "Alix", idp_subject="kc-alix", org_node_id=bureau)
    read = api.get(ME, headers=bearer(realm.token("kc-alix", KEY)))
    assert read.status_code == 200, read.text
    assert (read.json()["org_node_id"], read.json()["org_node_label"]) == (
        str(bureau),
        "Bureau d'études",
    )


@pytest.mark.requirement("WF-ADM-0030-A")
def test_an_account_attached_to_a_node_has_no_access_more_and_the_withdrawal_changes_none(
    api: ContractClient, database: Database, headers: dict[str, str], realm: TestRealm
) -> None:
    # « Un utilisateur rattaché à un nœud ne dispose d'aucun accès supplémentaire. » and
    # « Le retrait du rattachement ne modifie aucune habilitation. » : the effective permissions
    # are those of its roles, and an action refused before the attachment is refused after it and
    # after its withdrawal.
    estimating = role(database, "Chiffreur", permissions=("estimate.read",))
    bureau = node(database, "BE", "Bureau d'études")
    chiffreuse = account(
        database, "Roux", "Inès", roles=(estimating,), idp_subject="kc-ines", email="i@example.org"
    )
    herself = bearer(realm.token("kc-ines", KEY))

    def state() -> tuple[list[str], int]:
        return (
            api.get(ME, headers=herself).json()["permissions"],
            api.get(USERS, headers=herself).status_code,
        )

    before = state()
    assert before == (["estimate.read"], 404)
    assert attach(api, headers, chiffreuse, org_node_id=str(bureau)).status_code == 200
    assert state() == before
    assert attach(api, headers, chiffreuse, org_node_id=None).status_code == 200
    assert state() == before


@pytest.mark.requirement("WF-ADM-0030-A")
def test_the_evaluation_of_an_action_never_reads_the_attachment() -> None:
    # What the test above constates, the source says: the module that evaluates an action does
    # not name the node of an account.
    module = Path(waterfall.__file__).parent / "core" / "access_roles"
    sources = {path.name: path.read_text("utf-8") for path in module.glob("*.py")}
    assert sources
    assert [name for name, text in sources.items() if "org_node" in text] == []


@pytest.mark.requirement("WF-ADM-0030-A")
def test_the_table_of_the_accounts_is_filtered_on_the_node_and_its_descendants(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    direction = node(database, "DT", "Direction technique")
    bureau = node(database, "BE", "Bureau d'études", direction)
    atelier = node(database, "AT", "Atelier", bureau)
    achats = node(database, "AC", "Achats", direction)
    account(database, "Aubry", "Ana", org_node_id=direction)
    account(database, "Blanc", "Bob", org_node_id=atelier)
    account(database, "Cabot", "Cam", org_node_id=achats)
    account(database, "Dubois", "Dan")
    assert table(api, headers, f"?org_node_id={direction}") == [
        "Aubry Ana",
        "Blanc Bob",
        "Cabot Cam",
    ]
    assert table(api, headers, f"?org_node_id={bureau}") == ["Blanc Bob"]
    assert table(api, headers, f"?org_node_id={atelier}") == ["Blanc Bob"]
    assert table(api, headers, f"?org_node_id={uuid4()}") == []
    response = api.get(f"{USERS}?org_node_id={direction}&limit=1&offset=1", headers=headers)
    assert (len(response.json()["items"]), response.json()["meta"]["total"]) == (1, 3)


@pytest.mark.requirement("WF-ADM-0030-A")
def test_the_table_of_the_accounts_is_sorted_by_the_label_of_the_node_those_without_after(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    zeta = node(database, "Z", "Zeta")
    alpha = node(database, "A", "Alpha")
    account(database, "Aubry", "Ana", org_node_id=zeta)
    account(database, "Blanc", "Bob", org_node_id=alpha)
    account(database, "Cabot", "Cam")
    account(database, "Dubois", "Dan", org_node_id=alpha)
    # The caller, Camille Martin, has none either: the accounts without a node close the order, by
    # name, the first in the descending one.
    assert table(api, headers, "?sort_by=org_node") == [
        "Blanc Bob",
        "Dubois Dan",
        "Aubry Ana",
        "Cabot Cam",
        "Martin Camille",
    ]
    assert table(api, headers, "?sort_by=org_node&sort_order=desc") == [
        "Cabot Cam",
        "Martin Camille",
        "Aubry Ana",
        "Blanc Bob",
        "Dubois Dan",
    ]


# The journal of audit (#1740).


def attached(database: Database, node_id: UUID | None = None) -> UUID:
    """Write an account around the service, attached to a node or to none; give it."""
    return account(database, "Montgolfier", "Jeanne", org_node_id=node_id)


def inscriptions(database: Database, user_id: UUID) -> list[list[str]]:
    """Give the fields of each ``user_update`` inscribed for an account, in the order written."""
    with database.transaction() as session:
        entries = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.object_id == user_id, AuditEntry.action == "user_update")
            .order_by(AuditEntry.id)
        )
        return [list(AuditParams.model_validate(each.params).fields or []) for each in entries]


def modify(database: Database, user_id: UUID, sent: IdentityChange) -> int:
    """Change an account by the function the route calls, at the version it holds; give the next."""
    with database.transaction() as session:
        version = read_account(session, user_id).lock_version
    with database.transaction() as session:
        return change_account(session, user_id, sent, version, ACT).lock_version


@pytest.mark.requirement("WF-ADM-0030-A")
@pytest.mark.usefixtures("headers")
def test_a_attachment_given_changed_or_withdrawn_is_inscribed_as_a_field_of_the_account(
    database: Database,
) -> None:
    # #1740: ``org_node_id`` in ``fields`` of ``user_update``, whatever the change does to it.
    first = node(database, "A", "Alpha")
    second = node(database, "B", "Beta")
    jeanne = attached(database)
    modify(database, jeanne, IdentityChange(org_node_id=first))
    modify(database, jeanne, IdentityChange(org_node_id=second))
    modify(database, jeanne, IdentityChange(detaches=True))
    assert inscriptions(database, jeanne) == [["org_node_id"]] * 3


@pytest.mark.requirement("WF-ADM-0030-A")
@pytest.mark.usefixtures("headers")
def test_the_node_already_held_sent_again_inscribes_and_writes_nothing(database: Database) -> None:
    first = node(database, "A", "Alpha")
    jeanne = attached(database, first)
    assert modify(database, jeanne, IdentityChange(org_node_id=first)) == 0
    assert modify(database, account(database, "Roux", "Inès"), IdentityChange(detaches=True)) == 0
    assert modify(database, jeanne, IdentityChange()) == 0
    assert inscriptions(database, jeanne) == []


@pytest.mark.requirement("WF-ADM-0030-A")
@pytest.mark.usefixtures("headers")
def test_a_name_and_a_node_changed_together_are_inscribed_in_the_order_of_the_account(
    database: Database,
) -> None:
    # The order the account is written in: the name, the first name, the address, the node.
    first = node(database, "A", "Alpha")
    jeanne = attached(database)
    sent = IdentityChange(
        last_name="Durand", first_name="Jeanne-Marie", email="jm@example.org", org_node_id=first
    )
    modify(database, jeanne, sent)
    renamed = IdentityChange(first_name="Marie", detaches=True)
    modify(database, jeanne, renamed)
    assert inscriptions(database, jeanne) == [
        ["last_name", "first_name", "email", "org_node_id"],
        ["first_name", "org_node_id"],
    ]


@pytest.mark.requirement("WF-ADM-0030-A")
def test_a_change_of_the_attachment_by_the_api_is_inscribed_by_the_caller(
    api: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    bureau = node(database, "BE", "Bureau d'études")
    jeanne = attached(database)
    assert attach(api, headers, jeanne, org_node_id=str(bureau)).status_code == 200
    assert attach(api, headers, jeanne, org_node_id=str(bureau)).status_code == 200
    assert inscriptions(database, jeanne) == [["org_node_id"]]
    with database.transaction() as session:
        entry = session.scalars(select(AuditEntry).where(AuditEntry.object_id == jeanne)).one()
        assert entry.actor_user_id == CALLER


# The creation of an account attached to a node.


@pytest.mark.requirement("WF-ADM-0030-A")
@pytest.mark.usefixtures("headers")
def test_an_account_is_created_attached_to_an_active_node_and_refused_for_any_other(
    database: Database,
) -> None:
    bureau = node(database, "BE", "Bureau d'études")
    off = node(database, "OFF", "Éteint")
    deactivate(database, off)
    with database.transaction() as session:
        created = create_local_account(
            session, Identity("Montgolfier", "Jeanne", "jeanne@example.org", bureau), "kc-1", ACT
        )
    assert (created.org_node_id, created.org_node_label) == (bureau, "Bureau d'études")
    for sent, code in ((uuid4(), "UNKNOWN_ORG_NODE"), (off, "INACTIVE_REFERENCE_OBJECT")):
        identity = Identity("Roux", "Inès", f"{code}@example.org".lower(), sent)
        with pytest.raises(UnprocessableError) as refused, database.transaction() as session:
            create_local_account(session, identity, f"kc-{code}", ACT)
        assert [(each.pointer, each.code) for each in refused.value.fields] == [
            ("/org_node_id", code)
        ]
