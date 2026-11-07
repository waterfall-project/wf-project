# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the projects of the witness (US-0990; WF-QUA-0040), loaded at its instants and read.

``load-witness`` writes, after the reference, the local accounts of the contributors of the
witness, PRJ-002 and PRJ-001 with their client, the contributors, the subprojects, the work
breakdown, then the events of the chronology (``project_state_transitions.json``) each at its
instant: the offer 100 opened (Created to Pricing) and marked, the 101 opened, the designation of
100 tried and refused for the lack of tasks, the code entered, the 101 marked, the 102 opened.

What the service reads of the loaded witness is compared with the examples of the contract, but for
what the slice does not reach, listed here (``UNREACHED``): each entry names the EPIC that lifts it.
"""

import json
import shutil
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from installed_reference import install
from projects_support import PROJECTS, READING, person
from pydantic import SecretStr
from sqlalchemy import func, select, text
from support import WITNESS, captured_logs
from test_witness import load, wipe

from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.projects.tables import (
    Contributor,
    Project,
    ProjectStateTransition,
    Subproject,
    WorkPackage,
)
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import WitnessSettings
from waterfall.witness import projects, revisions
from waterfall.witness.description import Witness
from waterfall.witness.main import load_witness
from waterfall.witness.timeline import Chronology

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient, Logs

    from waterfall.platform.database import Database

PRJ_001 = UUID("01926f3a-7c00-7000-8000-000000000001")
PRJ_002 = UUID("01926f3a-7c00-7000-8000-000000000002")
REVISION_100 = UUID("01926f3a-7c00-7000-8000-000000000100")
REVISION_101 = UUID("01926f3a-7c00-7000-8000-000000000101")
REVISION_102 = UUID("01926f3a-7c00-7000-8000-000000000102")
# The contributors of the witness: Camille Martin, Alix Moreau (deactivated), Lucas Petit, Inès
# Roux.
CONTRIBUTORS = {
    UUID("01926f3a-7c00-7000-8000-000000000301"): True,
    UUID("01926f3a-7c00-7000-8000-000000000303"): False,
    UUID("01926f3a-7c00-7000-8000-000000000305"): True,
    UUID("01926f3a-7c00-7000-8000-000000000306"): True,
}
# What the slice does not reach, by object: the fields of an example the loaded witness differs
# from, each with the EPIC that lifts it. The author is the platform, never the account the example
# names; the counter of writes and the commands follow the writes and the state of the object.
UNREACHED = {
    "project": {
        "state": "PRJ-001 stays in Pricing until the order received (EP-07), PRJ-002 has none",
        "order_received_on": "the order received (EP-07)",
        "reference_revision_id": "the designation succeeds with tasks and lines (EP-06, EP-07)",
        "win_probability": "the order received sets it to 1 (EP-07); no slice loads the others",
        "inflation_rate": "the rate of the project is not written by the slice",
        "lock_version": "the counter follows the writes of the slice",
        "audit": "the platform is the author; updated_at follows the writes",
        "available_commands": "the commands follow the state of the project",
    },
    "revision": {
        "is_reference": "the designation succeeds with tasks and lines (EP-06, EP-07)",
        "inflation_rate": "copied from the project, which the slice does not set",
        "win_probability": "copied from the project, which the slice does not set",
        "lock_version": "the counter follows the writes of the slice",
        "audit": "the platform is the author; updated_at follows the writes",
        "available_commands": "the commands follow the state of the revision",
    },
    "subproject": {
        "has_actual_costs": "the actual costs are imported (EP-09)",
        "lock_version": "the counter follows the writes of the slice",
        "audit": "the platform is the author; the instant is the creation of the project",
        "available_commands": "the commands follow the state of the subproject",
    },
    "work_breakdown": {"attached_task": "the tasks attached to a package (EP-06)"},
}


def example(name: str) -> Any:
    """Read the value of an example of the contract."""
    return json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))["value"]


def chronology() -> Chronology:
    """Read the chronology the witness is loaded with."""
    return Chronology.model_validate(example("project_state_transitions"))


def instant(sequence: int) -> datetime:
    """Give the instant of an event of the chronology."""
    return chronology().events[sequence - 1].occurred_at


def keyed(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    """Give the items of a reading by their identifier."""
    return {item[key]: item for item in items}


def without(value: Any, names: set[str]) -> Any:
    """Give a value without the keys ``names``, at any depth."""
    if isinstance(value, list):
        return [without(each, names) for each in cast("list[object]", value)]
    if isinstance(value, dict):
        mapped = cast("dict[str, object]", value)
        return {key: without(each, names) for key, each in mapped.items() if key not in names}
    return value


def read(api: ContractClient, witness: Database, realm: TestRealm, url: str) -> Any:
    """Read a route of the service as a reader of all the projects; refuse anything but 200."""
    answer = api.get(url, headers=person(witness, realm, *READING).headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def counts(database: Database) -> dict[str, int]:
    """Count the rows of the tables the slice writes, the journal included."""
    with database.transaction() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
            for model in (
                UserAccount,
                Project,
                Revision,
                Contributor,
                Subproject,
                WorkPackage,
                ProjectStateTransition,
                AuditEntry,
            )
        }


def identifying(database: Database) -> dict[str, list[tuple[object, ...]]]:
    """Give the identifiers, codes, labels and dates of the projects of the witness.

    What the platform engenders — the identifiers of the transitions and of the default lines, the
    counters — is left out: it differs from a loading to the other.
    """
    with database.transaction() as session:
        return {
            "account": sorted(
                (a.id, a.email, a.first_name, a.last_name, a.state, a.created_at)
                for a in session.scalars(
                    select(UserAccount).where(UserAccount.id.in_(CONTRIBUTORS))
                )
            ),
            "project": sorted(
                (p.id, p.code, p.label, p.client, p.state, p.created_at, p.updated_at)
                for p in session.scalars(select(Project))
            ),
            "revision": sorted(
                (r.id, r.project_id, r.version_name, r.status, r.marked_at, r.created_at)
                for r in session.scalars(select(Revision))
            ),
            "transition": sorted(
                (t.project_id, t.from_state or "", t.to_state, t.occurred_at)
                for t in session.scalars(select(ProjectStateTransition))
            ),
            "contributor": sorted(
                (c.project_id, c.user_account_id, c.kind)
                for c in session.scalars(select(Contributor))
            ),
            "subproject": sorted(
                (s.id, s.code, s.label, s.created_at) for s in session.scalars(select(Subproject))
            ),
        }


@pytest.mark.requirement("WF-QUA-0040-A")
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
        assert (account.first_name, account.last_name) == (
            expected["first_name"],
            expected["last_name"],
        )
        # Local to Waterfall: no identity provider ever knows them, and they never sign in.
        assert account.origin == "local"
        assert account.idp_subject == f"witness-{account.id}"


@pytest.mark.requirement("WF-QUA-0040-A")
def test_no_account_of_the_witness_bears_an_address_outside_waterfall_test(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        addresses = list(session.scalars(select(UserAccount.email)))
    assert len(addresses) == len(CONTRIBUTORS)
    assert all(address and address.endswith("@waterfall.test") for address in addresses)
    assert len(set(addresses)) == len(addresses)


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_projects_read_are_the_examples_but_for_what_the_slice_does_not_reach(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    unreached = set(UNREACHED["project"])
    body = read(api, witness, realm, f"{PROJECTS}?states=created,pricing")
    read_projects = keyed(body["items"], "project_id")
    expected = keyed(example("projects")["items"], "project_id")
    assert read_projects.keys() == expected.keys() == {str(PRJ_001), str(PRJ_002)}
    for identifier, item in read_projects.items():
        assert without(item, unreached) == without(expected[identifier], unreached)
    # Where the slice stops: PRJ-001 in Pricing with its code and its current revision, PRJ-002
    # created with its own.
    assert read_projects[str(PRJ_001)]["state"] == "pricing"
    assert read_projects[str(PRJ_002)]["state"] == "created"
    assert read_projects[str(PRJ_001)]["current_revision_id"] == str(REVISION_102)
    assert body["meta"]["total"] == 2


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_revisions_read_are_the_examples_but_for_what_the_slice_does_not_reach(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    unreached = set(UNREACHED["revision"])
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/revisions")
    read_revisions = keyed(body["items"], "revision_id")
    expected = keyed(example("revisions")["items"], "revision_id")
    assert read_revisions.keys() == expected.keys()
    for identifier, item in read_revisions.items():
        assert without(item, unreached) == without(expected[identifier], unreached)
    assert [
        (identifier[-3:], item["status"], item["version_name"])
        for identifier, item in sorted(read_revisions.items())
    ] == [("100", "marked", "Offre v1.0"), ("101", "marked", "Référence"), ("102", "draft", None)]
    # The designation of 100 was refused, and no other tried: no reference (EP-06, EP-07).
    assert not any(item["is_reference"] for item in read_revisions.values())


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_contributors_read_are_the_example(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/contributors")
    assert body == example("contributors")


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_subprojects_read_are_the_examples_but_for_what_the_slice_does_not_reach(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    unreached = set(UNREACHED["subproject"])
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/subprojects")
    expected = example("subprojects")
    assert without(body, unreached) == without(expected, unreached)
    assert len(body) == len(expected) > 0


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_work_breakdown_read_is_the_example_but_for_what_the_slice_does_not_reach(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    unreached = set(UNREACHED["work_breakdown"])
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/work-breakdown")
    assert without(body, unreached) == without(example("work_breakdown"), unreached)


@pytest.mark.requirement("WF-CYC-0130-A")
def test_the_transitions_read_are_the_examples_up_to_the_pricing_the_slice_stops_at(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The third transition of the example, Pricing to In progress at the order received, is the
    # designation that tasks and lines allow (EP-07); the author is the platform.
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/state-transitions")
    expected = example("state_transitions")
    assert [(each["from_state"], each["to_state"], each["occurred_at"]) for each in body] == [
        (each["from_state"], each["to_state"], each["occurred_at"]) for each in expected[:2]
    ]
    assert all(each["actor"]["kind"] == "platform" for each in body)


@pytest.mark.requirement("WF-CYC-0130-A")
def test_the_dates_of_the_projects_revisions_and_transitions_are_those_of_the_chronology(
    witness: Database,
) -> None:
    created, opened_offer, marked_offer, opened_reference = (instant(n) for n in (2, 3, 4, 5))
    marked_reference, opened_current = (instant(n) for n in (8, 9))
    with witness.transaction() as session:
        projects_ = {p.id: p for p in session.scalars(select(Project))}
        revisions_ = {r.id: r for r in session.scalars(select(Revision))}
        transitions = [
            (t.project_id, t.from_state, t.to_state, t.occurred_at)
            for t in session.scalars(select(ProjectStateTransition))
        ]
    # PRJ-002, which the chronology does not date, is created with PRJ-001.
    assert {p.created_at for p in projects_.values()} == {created}
    # The last write into PRJ-001 is the opening of the 102, as in the example; its code is entered.
    assert projects_[PRJ_001].updated_at == opened_current
    assert (projects_[PRJ_001].code, projects_[PRJ_002].code) == ("PRJ-001", "PRJ-002")
    assert {r: (revisions_[r].created_at, revisions_[r].marked_at) for r in revisions_} == {
        REVISION_100: (opened_offer, marked_offer),
        REVISION_101: (opened_reference, marked_reference),
        REVISION_102: (opened_current, None),
    }
    assert sorted(transitions, key=lambda each: (each[3], str(each[0]))) == [
        (PRJ_001, None, "created", created),
        (PRJ_002, None, "created", created),
        (PRJ_001, "created", "pricing", opened_offer),
    ]


@pytest.mark.requirement("WF-CYC-0130-A")
def test_the_dates_of_the_reference_are_those_of_the_loading(witness: Database) -> None:
    with witness.transaction() as session:
        dates = set(session.scalars(select(CostCategory.created_at)))
    assert dates
    assert all(utc_now() - each < timedelta(hours=1) for each in dates)


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_revisions_100_101_and_102_each_hold_their_main_cost_structure(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        main = [
            session.scalar(
                select(func.count())
                .select_from(CostStructure)
                .where(CostStructure.revision_id == each, CostStructure.kind == "main")
            )
            for each in (REVISION_100, REVISION_101, REVISION_102)
        ]
    assert main == [1, 1, 1]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_designation_of_the_offer_is_tried_refused_and_noted_in_the_output(
    logs: Logs, witness: Database
) -> None:
    noted = logs.named("witness.designation_refused")
    assert [(each["project"], each["revision"], each["missing_condition"]) for each in noted] == [
        ("PRJ-001", 100, "revision_has_tasks_and_lines")
    ]
    assert len(logs.named("witness.loaded")) == 1
    with witness.transaction() as session:
        assert session.scalar(select(func.count()).where(Revision.is_reference)) == 0


@pytest.mark.requirement("WF-QUA-0040-A")
def test_two_new_platforms_loaded_with_the_witness_hold_the_same_identifying_data(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    first = identifying(witness)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert identifying(witness) == first
    assert len(first["revision"]) == 3
    assert len(first["project"]) == 2


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_second_loading_finds_the_projects_there_and_writes_nothing(
    witness: Database, service_database_url: str, logs: Logs
) -> None:
    before = counts(witness)
    settings = WitnessSettings(
        database_url=SecretStr(service_database_url), witness_path=str(WITNESS)
    )
    logs.clear()
    assert load_witness(settings) == 0
    assert [record["event"] for record in logs.records if "witness." in record["event"]] == [
        "witness.already_loaded"
    ]
    assert counts(witness) == before
    assert before["project"] == 2


@pytest.mark.requirement("WF-QUA-0040-A")
def test_an_identifier_held_by_half_the_platform_stops_the_command_and_writes_nothing(
    witness: Database, owner: Engine, service_database_url: str, logs: Logs
) -> None:
    # The platform holds the revisions 100 and 101 but not the 102: the witness is half there, a
    # collision, and nothing is written (the other slices find their objects and write nothing).
    with owner.begin() as connection:
        connection.exec_driver_sql("SET LOCAL session_replication_role = replica")
        connection.execute(text("DELETE FROM revision WHERE id = :id"), {"id": REVISION_102})
    before = counts(witness)
    logs.clear()
    assert load(service_database_url) == 1
    refused = logs.named("witness.refused")
    assert [(each["code"]) for each in refused] == ["ALREADY_EXISTS"]
    assert counts(witness) == before


def copied(tmp_path: Path, mutate: Any) -> Path:
    """Copy the description of the witness, its chronology changed by ``mutate``."""
    directory = tmp_path / "witness"
    shutil.copytree(WITNESS, directory)
    path = directory / "project_state_transitions.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document["value"]["events"])
    path.write_text(json.dumps(document), encoding="utf-8")
    return directory


def stray_field(events: list[dict[str, Any]]) -> None:
    """Add a field beyond the model to the first write."""
    events[1]["writes"][0]["beyond"] = True


def unknown_kind(events: list[dict[str, Any]]) -> None:
    """Give the first write a kind the model does not know."""
    events[1]["writes"][0]["kind"] = "project_deleted"


def out_of_order(events: list[dict[str, Any]]) -> None:
    """Give the third event the instant of the second."""
    events[2]["occurred_at"] = events[1]["occurred_at"]


def unknown_revision(events: list[dict[str, Any]]) -> None:
    """Open a revision that revisions.json does not describe."""
    events[2]["writes"][0]["revision"] = 999


def misnamed_version(events: list[dict[str, Any]]) -> None:
    """Mark the offer under a name revisions.json does not give it."""
    events[3]["writes"][0]["version_name"] = "Offre v9"


def transition_not_made(events: list[dict[str, Any]]) -> None:
    """Say the opening of the offer moves the project to In progress."""
    events[2]["writes"][1]["to"] = "in_progress"


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize(
    "case",
    [
        (stray_field, "Extra inputs are not permitted"),
        (unknown_kind, "project_deleted"),
        (out_of_order, "does not come after event"),
        (unknown_revision, "revision 999 that revisions.json does not"),
        (misnamed_version, "revision 100 is marked Offre v9, not Offre v1.0"),
        (transition_not_made, "the project did not move created to in_progress"),
    ],
)
def test_a_chronology_that_strays_from_its_model_or_the_description_stops_the_command(
    case: tuple[Any, str],
    tmp_path: Path,
    witness: Database,
    owner: Engine,
    service_database_url: str,
) -> None:
    mutate, cause = case
    wipe(owner)
    install(owner)
    before = counts(witness)
    directory = copied(tmp_path, mutate)
    with captured_logs() as logs:
        assert load(service_database_url, directory) == 1
    (failed,) = logs.named("witness.failed")
    assert cause in failed["exception"]
    assert counts(witness) == before


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_designation_that_is_not_refused_stops_the_command(
    monkeypatch: pytest.MonkeyPatch,
    witness: Database,
    owner: Engine,
    service_database_url: str,
) -> None:
    def accepted(*_: object) -> None:
        return None

    monkeypatch.setattr(revisions, "designate_reference", accepted)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 1
    assert counts(witness)["project"] == 0


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_refusal_elsewhere_than_at_the_designation_stops_the_command(
    monkeypatch: pytest.MonkeyPatch,
    witness: Database,
    owner: Engine,
    service_database_url: str,
    logs: Logs,
) -> None:
    def refused(*_: object) -> None:
        message = "STATE_FORBIDS_OPERATION"
        raise ConflictError(message, {"missing_condition": "revision_marked"})

    monkeypatch.setattr(revisions, "designate_reference", refused)
    wipe(owner)
    install(owner)
    logs.clear()
    assert load(service_database_url) == 1
    assert [each["params"] for each in logs.named("witness.refused")] == [
        {"missing_condition": "revision_marked"}
    ]
    assert counts(witness)["project"] == 0


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_projects_are_created_by_the_rules_of_the_creation_the_minimal_reference_included(
    witness: Database, owner: Engine
) -> None:
    # A platform whose reference lacks a prerequisite refuses the witness (#2155): the projects
    # slice, run on the bootstrap alone, names what is missing and writes nothing.
    wipe(owner)
    install(owner)
    current = Witness(WITNESS, Act(None, utc_now()))
    with (
        logging_context(correlation_id="witness-refused"),
        pytest.raises(ConflictError) as refused,
        witness.transaction() as session,
    ):
        projects.load(session, current)
    assert refused.value.code == "REFERENCE_INCOMPLETE"
    assert counts(witness)["project"] == 0
