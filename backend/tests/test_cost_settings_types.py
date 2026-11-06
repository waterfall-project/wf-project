# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The natures of cost (US-0820, WF-REF-0030), through the service.

The service is loaded with the witness by its command, as an installation of the examples, and
read by three sessions of the cost settings: one holding nothing of them, one that reads them, one
that changes them (``reference_sessions``). Every answer is checked against the contract
(``ContractClient``); the lists are the examples the faux back serves.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import pytest
from cost_settings_examples import (
    LABOUR,
    NON_LABOUR,
    TYPES,
    caller_id,
    commands,
    deactivate,
    example,
    new_type,
    pointers,
    refusal,
    shown,
)
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.cost_settings.tables import CostType
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.identifiers import new_id
from waterfall.witness.cost_types import load as load_types
from waterfall.witness.description import Witness

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

CHANGE = "cost_settings.write"
UNKNOWN = "7d1e5b0a-3c94-4f2e-9a68-5b20c4e1f9d3"
AVAILABLE: list[tuple[str, bool, list[str]]] = [("deactivate", True, []), ("change_kind", True, [])]


@pytest.fixture
def sessions(witness: Database, reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the cost settings on a service loaded with the witness."""
    del witness
    return reference_sessions("cost_settings")


def listed(api: ContractClient, headers: dict[str, str], query: str = "") -> dict[str, Any]:
    """Read the natures by a session, the query given, and expect them."""
    response = api.get(f"{TYPES}?{query}", headers=headers)
    assert response.status_code == 200
    return response.json()


def codes(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the codes of the natures a query keeps, in their order."""
    return [item["code"] for item in listed(api, headers, query)["items"]]


@pytest.mark.requirement("WF-REF-0030-A")
def test_every_session_reads_the_active_natures_as_the_example_the_faux_back_serves(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The active natures are the vocabulary of the projects: read without any permission of the
    # cost settings (decision of the author, 2026-11-01). The service answers the example, to the
    # dates and the authors of the loading, the counters and the commands.
    expected = [shown(item) for item in example("cost_types")["items"]]
    for headers in (sessions.without, sessions.reading, sessions.changing):
        read = listed(api, headers)
        assert [shown(item) for item in read["items"]] == expected
        assert read["meta"] == {"limit": 50, "offset": 0, "total": 3}
    reader = example("cost_types_reader")["items"]
    assert [shown(item) for item in listed(api, sessions.reading)["items"]] == [
        shown(item) for item in reader
    ]


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_commands_of_a_nature_are_those_of_a_caller_who_changes_the_cost_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    # No category exists yet to bind the kind (US-0820b): the change of kind is available, and
    # the deactivation always is.
    for headers in (sessions.without, sessions.reading):
        assert all(item["available_commands"] == [] for item in listed(api, headers)["items"])
    managed = listed(api, sessions.changing)["items"]
    assert [commands(item) for item in managed] == [AVAILABLE] * 3


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_natures_are_filtered_searched_sorted_and_paged_by_the_server(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.without
    assert codes(api, headers, "kinds=labor,provision") == ["MO", "PRV"]
    assert codes(api, headers, "kinds=non_labor") == ["DEB"]
    # The search covers the code and the label, whatever the case and the accents.
    assert codes(api, headers, "search=prv") == ["PRV"]
    assert codes(api, headers, "search=DEBOURS") == ["DEB"]
    assert codes(api, headers, "search=main-d") == ["MO"]
    assert codes(api, headers, "sort_by=kind&sort_order=desc") == ["PRV", "DEB", "MO"]
    assert codes(api, headers, "sort_by=label") == ["DEB", "MO", "PRV"]
    # ``meta.total`` counts what is kept, not the page.
    page = listed(api, headers, "kinds=labor,non_labor&limit=1&offset=1")
    assert [item["code"] for item in page["items"]] == ["MO"]
    assert page["meta"] == {"limit": 1, "offset": 1, "total": 2}
    beyond = listed(api, headers, "limit=5&offset=10")
    assert (beyond["items"], beyond["meta"]["total"]) == ([], 3)


@pytest.mark.requirement("WF-REF-0030-A")
@pytest.mark.requirement("WF-REF-0150-A")
def test_the_deactivated_natures_are_read_by_the_permission_to_change_and_come_after_the_active(
    api: ContractClient, sessions: PartSessions
) -> None:
    changing = sessions.changing
    deb = next(item for item in listed(api, changing)["items"] if item["code"] == "DEB")
    assert deactivate(api, changing, deb).status_code == 200
    assert codes(api, sessions.without) == ["MO", "PRV"]
    assert codes(api, changing, "include_inactive=true") == ["DEB", "MO", "PRV"]
    assert codes(api, changing, "is_active=false") == ["DEB"]
    assert codes(api, changing, "is_active=true&include_inactive=true") == ["MO", "PRV"]
    assert codes(api, changing, "include_inactive=true&sort_by=is_active") == ["MO", "PRV", "DEB"]
    # Equals keep the order of the code, whatever the direction.
    assert codes(api, changing, "include_inactive=true&sort_by=is_active&sort_order=desc") == [
        "DEB",
        "MO",
        "PRV",
    ]
    page = listed(api, changing, "include_inactive=true&limit=2")
    assert page["meta"]["total"] == 3


@pytest.mark.requirement("WF-REF-0150-A")
@pytest.mark.parametrize(
    "query", ["include_inactive=true", "is_active=false", "is_active=true&include_inactive=true"]
)
def test_the_deactivated_natures_are_refused_without_the_permission_to_change_the_settings(
    api: ContractClient, sessions: PartSessions, query: str
) -> None:
    # The permission to read the cost settings does not open them (decision of the author of
    # 2026-11-06, #2084): the contract refuses it who only reads, naming the permission to change.
    for headers in (sessions.without, sessions.reading):
        response = api.get(f"{TYPES}?{query}", headers=headers)
        assert refusal(response) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})
    assert api.get(f"{TYPES}?{query}", headers=sessions.changing).status_code == 200


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_of_each_of_the_three_kinds_is_created_with_its_commands_and_its_author(
    api: ContractClient, sessions: PartSessions
) -> None:
    author = caller_id(api, sessions.changing)
    for kind in ("labor", "non_labor", "provision"):
        created = new_type(api, sessions.changing, f"NK-{kind}", kind)
        assert (created["code"], created["kind"], created["is_active"]) == (
            f"NK-{kind}",
            kind,
            True,
        )
        assert (created["lock_version"], commands(created)) == (0, AVAILABLE)
        assert created["audit"]["created_by"]["user_id"] == author
        assert created["audit"]["updated_by"]["user_id"] == author
    assert codes(api, sessions.without, "search=NK-") == [
        "NK-labor",
        "NK-non_labor",
        "NK-provision",
    ]


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_whose_code_exists_is_refused_naming_the_nature_that_holds_it(
    api: ContractClient, sessions: PartSessions
) -> None:
    sent = {"code": "DEB", "label": "Autre", "kind": "non_labor"}
    response = api.post(TYPES, headers=sessions.changing, json=sent)
    assert response.status_code == 409
    assert pointers(response) == [
        ("/code", "ALREADY_EXISTS", {"conflicting_object_id": str(NON_LABOUR)})
    ]
    # A code a deactivated nature holds is held all the same.
    deb = next(item for item in listed(api, sessions.changing)["items"] if item["code"] == "DEB")
    assert deactivate(api, sessions.changing, deb).status_code == 200
    again = api.post(TYPES, headers=sessions.changing, json=sent)
    assert pointers(again) == pointers(response)
    assert codes(api, sessions.changing, "include_inactive=true") == ["DEB", "MO", "PRV"]


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_without_code_or_label_or_beyond_their_bounds_is_refused_field_by_field(
    api: ContractClient, sessions: PartSessions
) -> None:
    sent = {"code": "C" * 21, "label": "", "kind": "labor"}
    response = api.post(TYPES, headers=sessions.changing, json=sent)
    assert response.status_code == 422
    assert pointers(response) == [
        ("/code", "VALUE_TOO_LONG", {"max_length": 20}),
        ("/label", "VALUE_REQUIRED", {}),
    ]
    blank = api.post(TYPES, headers=sessions.changing, json={**sent, "code": "  ", "label": "x"})
    assert pointers(blank) == [("/code", "VALIDATION_FAILED", {})]
    assert codes(api, sessions.without) == ["DEB", "MO", "PRV"]


@pytest.mark.requirement("WF-REF-0030-A")
def test_every_write_of_a_nature_asks_for_the_permission_to_change_the_cost_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    sent = {"code": "X", "label": "X", "kind": "labor"}
    activation = {"is_active": False, "lock_version": 1}
    for headers in (sessions.without, sessions.reading):
        for response in (
            api.post(TYPES, headers=headers, json=sent),
            api.patch(f"{TYPES}/{LABOUR}", headers=headers, json={**sent, "lock_version": 1}),
            api.put(f"{TYPES}/{LABOUR}/activation", headers=headers, json=activation),
        ):
            assert refusal(response) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})
    assert codes(api, sessions.without) == ["DEB", "MO", "PRV"]


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_changes_its_code_its_label_and_its_kind_while_no_category_binds_it(
    api: ContractClient, sessions: PartSessions
) -> None:
    created = new_type(api, sessions.changing, "TMP")
    sent = {"code": "TMP2", "label": "Autre libellé", "kind": "provision", "lock_version": 0}
    response = api.patch(f"{TYPES}/{created['cost_type_id']}", headers=sessions.changing, json=sent)
    assert response.status_code == 200
    changed = response.json()
    assert (changed["code"], changed["label"], changed["kind"], changed["lock_version"]) == (
        "TMP2",
        "Autre libellé",
        "provision",
        1,
    )
    # The version read is stale once written (412), and an unknown nature is not found (404).
    stale = api.patch(f"{TYPES}/{created['cost_type_id']}", headers=sessions.changing, json=sent)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    missing = api.patch(f"{TYPES}/{UNKNOWN}", headers=sessions.changing, json=sent)
    assert missing.status_code == 404
    # Its own code is not taken, another's is.
    own = api.patch(
        f"{TYPES}/{created['cost_type_id']}",
        headers=sessions.changing,
        json={**sent, "lock_version": 1},
    )
    assert own.status_code == 200
    taken = api.patch(
        f"{TYPES}/{created['cost_type_id']}",
        headers=sessions.changing,
        json={**sent, "code": "MO", "lock_version": 2},
    )
    assert taken.status_code == 409
    assert pointers(taken) == [("/code", "ALREADY_EXISTS", {"conflicting_object_id": str(LABOUR)})]


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_reactivated_is_active_again_and_asking_for_its_state_writes_nothing(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    nature = new_type(api, headers, "REA")
    off = deactivate(api, headers, nature).json()
    on = api.put(
        f"{TYPES}/{nature['cost_type_id']}/activation",
        headers=headers,
        json={"is_active": True, "lock_version": off["lock_version"]},
    )
    assert (on.status_code, on.json()["is_active"], on.json()["lock_version"]) == (200, True, 2)
    # Asking for the state it is in writes nothing, whatever the version... read.
    again = api.put(
        f"{TYPES}/{nature['cost_type_id']}/activation",
        headers=headers,
        json={"is_active": True, "lock_version": 2},
    )
    assert (again.status_code, again.json()["lock_version"]) == (200, 2)


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_activation_of_a_nature_is_refused_stale_or_unknown(
    api: ContractClient, sessions: PartSessions
) -> None:
    stale = api.put(
        f"{TYPES}/{LABOUR}/activation",
        headers=sessions.changing,
        json={"is_active": False, "lock_version": 7},
    )
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 0})
    unknown = api.put(
        f"{TYPES}/{UNKNOWN}/activation",
        headers=sessions.changing,
        json={"is_active": False, "lock_version": 0},
    )
    assert unknown.status_code == 404
    assert codes(api, sessions.without) == ["DEB", "MO", "PRV"]


def insert_type(code: str, type_id: UUID) -> Any:
    """Write a nature as another transaction does, to be committed or not by the test."""
    now = utc_now()
    return insert(CostType).values(
        id=type_id,
        code=code,
        label=code,
        kind="labor",
        is_active=True,
        created_at=now,
        created_by=None,
        updated_at=now,
        updated_by=None,
    )


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_creation_that_meets_a_code_being_written_waits_for_it_and_is_refused_naming_it(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # The unique index decides when two creations meet: the second waits for the first to commit,
    # then is refused by the nature the first wrote, which it could not read before.
    holder = new_id()
    sent = {"code": "RACE", "label": "RACE", "kind": "labor"}
    with ThreadPoolExecutor(1) as other, Session(database.engine) as writing:
        writing.execute(insert_type("RACE", holder))
        creating = other.submit(api.post, TYPES, headers=sessions.changing, json=sent)
        wait_for_a_lock(database)
        writing.commit()
        answer = creating.result(timeout=10)
    assert answer.status_code == 409
    assert pointers(answer) == [("/code", "ALREADY_EXISTS", {"conflicting_object_id": str(holder)})]
    assert codes(api, sessions.without, "search=RACE") == ["RACE"]


@pytest.mark.requirement("WF-REF-0030-A")
def test_two_simultaneous_creations_of_one_code_leave_one_nature_and_one_refusal(
    api: ContractClient, sessions: PartSessions
) -> None:
    sent = {"code": "TWIN", "label": "TWIN", "kind": "labor"}

    def create(_: int) -> Any:
        return api.post(TYPES, headers=sessions.changing, json=sent)

    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(create, range(2)))
    created = [answer for answer in answers if answer.status_code == 201]
    refused = [answer for answer in answers if answer.status_code == 409]
    assert (len(created), len(refused)) == (1, 1)
    assert pointers(refused[0]) == [
        (
            "/code",
            "ALREADY_EXISTS",
            {"conflicting_object_id": created[0].json()["cost_type_id"]},
        )
    ]
    assert codes(api, sessions.without, "search=TWIN") == ["TWIN"]


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_witness_deactivates_the_objects_it_says_deactivated_and_is_loaded_once(
    database: Database, tmp_path: Path
) -> None:
    # The slice of the natures, on a description of its own: a nature the witness says deactivated
    # is written, then deactivated; run again, it finds its objects there and writes nothing.
    open_type, shut_type = new_id(), new_id()
    nature = example("cost_types")["items"][0]
    types = [
        {**nature, "cost_type_id": str(open_type), "code": "OPEN"},
        {**nature, "cost_type_id": str(shut_type), "code": "SHUT", "is_active": False},
    ]
    (tmp_path / "cost_types.json").write_text(json.dumps({"value": {"items": types}}))
    witness = Witness(tmp_path, Act(None, utc_now()))
    with database.transaction() as session:
        assert load_types(session, witness) is True
    with database.transaction() as session:
        assert load_types(session, witness) is False
        natures = {
            row.code: (row.is_active, row.lock_version) for row in session.scalars(select(CostType))
        }
    assert natures == {"OPEN": (True, 0), "SHUT": (False, 1)}
