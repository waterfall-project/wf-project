# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the projects of the witness (US-0920/L1; WF-QUA-0040), loaded and read.

``load-witness`` writes, after the reference, the local accounts of the four contributors of the
witness and PRJ-002 and PRJ-001 with their client, under the identifiers the examples of the
contract impose; the states, the codes and the revisions are the chronology's (US-0990).
"""

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from projects_support import PROJECTS, READING, person
from pydantic import SecretStr
from sqlalchemy import select
from support import WITNESS

from waterfall.core.projects.tables import Project, ProjectStateTransition
from waterfall.core.users.tables import UserAccount
from waterfall.platform.settings import WitnessSettings
from waterfall.witness.main import load_witness

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient, Logs

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

PRJ_001 = UUID("01926f3a-7c00-7000-8000-000000000001")
PRJ_002 = UUID("01926f3a-7c00-7000-8000-000000000002")
# The contributors of the witness: Camille Martin, Alix Moreau (deactivated), Lucas Petit, Inès
# Roux.
CONTRIBUTORS = {
    UUID("01926f3a-7c00-7000-8000-000000000301"): True,
    UUID("01926f3a-7c00-7000-8000-000000000303"): False,
    UUID("01926f3a-7c00-7000-8000-000000000305"): True,
    UUID("01926f3a-7c00-7000-8000-000000000306"): True,
}


def example(name: str) -> dict[str, Any]:
    """Read the value of an example of the contract."""
    return json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))["value"]


def test_the_witness_loads_the_local_accounts_of_its_contributors_under_its_identifiers(
    witness: Database,
) -> None:
    named = {user["user_id"]: user for user in example("users")["items"]}
    with witness.transaction() as session:
        accounts = session.scalars(
            select(UserAccount).where(UserAccount.id.in_(CONTRIBUTORS))
        ).all()
    assert {account.id: account.state == "active" for account in accounts} == CONTRIBUTORS
    for account in accounts:
        expected = named[str(account.id)]
        assert (account.first_name, account.last_name, account.email) == (
            expected["first_name"],
            expected["last_name"],
            expected["email"],
        )
        # Local to Waterfall: no identity provider ever knows them, and they never sign in.
        assert account.origin == "local"
        assert account.idp_subject == f"witness-{account.id}"


def test_the_witness_loads_the_two_projects_with_their_client_the_first_moved_by_its_revision(
    witness: Database,
) -> None:
    items = {item["project_id"]: item for item in example("projects")["items"]}
    with witness.transaction() as session:
        projects = {row.id: row for row in session.scalars(select(Project))}
        transitions = session.scalars(select(ProjectStateTransition)).all()
    assert set(projects) == {PRJ_001, PRJ_002}
    for identifier, row in projects.items():
        expected = items[str(identifier)]
        assert (row.label, row.client, row.description) == (
            expected["label"],
            expected["client"],
            expected["description"],
        )
        # The chronology opens a revision of PRJ-001, which moves it to Pricing (US-0980/L1).
        state = "pricing" if identifier == PRJ_001 else "created"
        assert (row.state, row.code, row.created_by) == (state, None, None)
    assert projects[PRJ_001].client == "Papeteries de la Vienne"
    assert projects[PRJ_002].client is None
    # Each project is born from no state, by the platform; the opening of the revision of PRJ-001
    # moves it to Pricing, by the platform too.
    assert sorted(
        (t.project_id, t.from_state or "", t.to_state, t.actor_user_id) for t in transitions
    ) == [
        (PRJ_001, "", "created", None),
        (PRJ_001, "created", "pricing", None),
        (PRJ_002, "", "created", None),
    ]


def test_the_projects_of_the_witness_are_read_through_the_service(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    reader = person(witness, realm, *READING)
    answer = api.get(f"{PROJECTS}?states=created,pricing", headers=reader.headers)
    assert answer.status_code == 200
    body = answer.json()
    assert {item["project_id"]: item["client"] for item in body["items"]} == {
        str(PRJ_001): "Papeteries de la Vienne",
        str(PRJ_002): None,
    }
    assert body["meta"]["total"] == 2


def test_the_transitions_of_the_witness_project_are_read_in_their_order_at_one_instant(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The creation and the first revision of PRJ-001 share an instant: the order read through the
    # service is the cycle's, whatever the identifiers the witness gives its transitions.
    reader = person(witness, realm, *READING)
    answer = api.get(f"{PROJECTS}/{PRJ_001}/state-transitions", headers=reader.headers)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert [(item["from_state"], item["to_state"]) for item in body] == [
        (None, "created"),
        ("created", "pricing"),
    ]
    assert body[0]["occurred_at"] == body[1]["occurred_at"]


def test_a_second_loading_finds_the_projects_there_and_writes_nothing(
    witness: Database, service_database_url: str, logs: Logs
) -> None:
    settings = WitnessSettings(
        database_url=SecretStr(service_database_url), witness_path=str(WITNESS)
    )
    assert load_witness(settings) == 0
    assert any(record["event"] == "witness.already_loaded" for record in logs.records)
    with witness.transaction() as session:
        assert len(session.scalars(select(Project)).all()) == 2
        assert len(session.scalars(select(UserAccount)).all()) >= len(CONTRIBUTORS)
