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
from uuid import UUID

import pytest
from cost_settings_examples import (
    LABOUR,
    NON_LABOUR,
    PROVISION,
    TYPES,
    bind,
    caller_id,
    commands,
    deactivate,
    example,
    new_category,
    new_type,
    pointers,
    refusal,
    shown,
)
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.cost_settings.interface.cost_types import CostTypeDraft, create_cost_type
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import RoleOfCategory
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.identifiers import new_id
from waterfall.witness.cost_categories import load as load_categories
from waterfall.witness.cost_types import load as load_types
from waterfall.witness.description import Witness

if TYPE_CHECKING:
    from pathlib import Path

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
    # Nothing binds a category before the lines and the roles exist, but the rates: the witness
    # rates every category of labour, so the nature of labour cannot change kind, the others can.
    # The deactivation always is available.
    for headers in (sessions.without, sessions.reading):
        assert all(item["available_commands"] == [] for item in listed(api, headers)["items"])
    managed = {item["code"]: commands(item) for item in listed(api, sessions.changing)["items"]}
    assert managed == {
        "MO": [AVAILABLE[0], ("change_kind", False, ["cost_type_unrated"])],
        "DEB": AVAILABLE,
        "PRV": AVAILABLE,
    }


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
def test_the_deactivated_natures_are_read_by_the_permission_to_change_and_come_last_by_state(
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
@pytest.mark.parametrize(
    ("query", "pointer"),
    [
        ("limit=0", "/query/limit"),
        ("limit=501", "/query/limit"),
        ("sort_by=state", "/query/sort_by"),
        ("kinds=labor,other", "/query/kinds"),
    ],
)
def test_a_parameter_of_the_list_outside_the_contract_is_a_value_refused(
    api: ContractClient, sessions: PartSessions, query: str, pointer: str
) -> None:
    # Read through the contract, which declares that 422 (#799): code, status and pointer.
    response = api.get(f"{TYPES}?{query}", headers=sessions.changing)
    body = response.json()
    assert (response.status_code, body["code"], [each["pointer"] for each in body["fields"]]) == (
        422,
        "VALIDATION_FAILED",
        [pointer],
    )


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_created_with_an_identifier_already_borne_is_refused_naming_it(
    database: Database, witness: Database
) -> None:
    # The identifier the loader of the witness imposes: a nature already bears it (409).
    del witness
    draft = CostTypeDraft(code="NEW", label="Nouvelle", kind="labor")
    with database.transaction() as session, pytest.raises(ConflictError) as refused:
        create_cost_type(session, draft, Act(None, utc_now()), identifier=LABOUR)
    assert refused.value.code == "ALREADY_EXISTS"
    assert refused.value.params == {"conflicting_object_id": str(LABOUR)}


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
def test_a_nature_changes_its_code_its_label_and_its_kind_while_nothing_binds_a_category(
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
def test_the_kind_of_a_nature_is_refused_while_a_category_of_it_is_rated_and_the_command_says_so(
    api: ContractClient, sessions: PartSessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = sessions.changing
    nature = new_type(api, headers, "BND")
    new_category(api, headers, "A", nature["cost_type_id"])
    second = new_category(api, headers, "B", nature["cost_type_id"])
    bind(monkeypatch, rated={UUID(second["cost_category_id"])})
    sent = {"code": "BND", "label": "BND", "kind": "non_labor", "lock_version": 0}
    response = api.patch(f"{TYPES}/{nature['cost_type_id']}", headers=headers, json=sent)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {
            "missing_condition": "cost_type_unrated",
            "cost_categories": [
                {"cost_category_id": second["cost_category_id"], "code": "B", "label": "B"}
            ],
        },
    )
    listed_nature = next(item for item in listed(api, headers)["items"] if item["code"] == "BND")
    assert commands(listed_nature) == [
        ("deactivate", True, []),
        ("change_kind", False, ["cost_type_unrated"]),
    ]
    # The code and the label change all the same, and nothing was written by the refusal.
    renamed = api.patch(
        f"{TYPES}/{nature['cost_type_id']}", headers=headers, json={**sent, "kind": "labor"}
    )
    assert (renamed.status_code, renamed.json()["kind"]) == (200, "labor")


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_kind_of_a_nature_is_refused_for_the_first_condition_its_command_lacks(
    api: ContractClient, sessions: PartSessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    # In the order the contract refuses by: employed, then rated, then held by a role.
    headers = sessions.changing
    nature = new_type(api, headers, "ORD")
    first = UUID(new_category(api, headers, "A", nature["cost_type_id"])["cost_category_id"])
    second = UUID(new_category(api, headers, "B", nature["cost_type_id"])["cost_category_id"])
    role = RoleOfCategory(UUID(UNKNOWN), "AUTOM", "Automaticien")
    bind(monkeypatch, employed={second}, rated={first}, roles={first: role})
    sent = {"code": "ORD", "label": "ORD", "kind": "provision", "lock_version": 0}
    url = f"{TYPES}/{nature['cost_type_id']}"
    employed = api.patch(url, headers=headers, json=sent)
    status, code, params = refusal(employed)
    assert (status, code, params["missing_condition"]) == (
        409,
        "STATE_FORBIDS_OPERATION",
        "cost_type_unused",
    )
    assert [each["code"] for each in params["cost_categories"]] == ["B"]
    read = next(item for item in listed(api, headers)["items"] if item["code"] == "ORD")
    assert commands(read)[1] == (
        "change_kind",
        False,
        ["cost_type_unused", "cost_type_unrated", "cost_type_without_role"],
    )
    bind(monkeypatch, roles={first: role})
    held = api.patch(url, headers=headers, json=sent)
    assert refusal(held) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {
            "missing_condition": "cost_type_without_role",
            "resource_roles": [
                {"resource_role_id": UNKNOWN, "code": "AUTOM", "label": "Automaticien"}
            ],
        },
    )
    bind(monkeypatch)
    assert api.patch(url, headers=headers, json=sent).status_code == 200


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_deactivated_deactivates_its_active_categories_with_their_counter_and_author(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    headers = sessions.changing
    author = UUID(caller_id(api, headers))
    nature = new_type(api, headers, "CAS")
    kept = new_category(api, headers, "K", nature["cost_type_id"])
    closed = new_category(api, headers, "L", nature["cost_type_id"])
    other = new_category(api, headers, "M", str(PROVISION))
    deactivation = {"is_active": False, "lock_version": closed["lock_version"]}
    assert (
        api.put(
            f"/api/v1/reference/cost-categories/{closed['cost_category_id']}/activation",
            headers=headers,
            json=deactivation,
        ).status_code
        == 200
    )
    response = deactivate(api, headers, nature)
    assert response.status_code == 200
    assert (response.json()["is_active"], response.json()["lock_version"]) == (False, 1)
    with database.transaction() as session:
        rows = {
            row.code: (row.is_active, row.lock_version, row.updated_by)
            for row in session.scalars(select(CostCategory))
            if row.code in {"K", "L", "M"}
        }
    # Each active category follows its nature, its counter advances and its author is the caller's;
    # the one deactivated already is not written again, nor that of another nature.
    assert rows == {
        "K": (False, kept["lock_version"] + 1, author),
        "L": (False, closed["lock_version"] + 1, author),
        "M": (True, other["lock_version"], author),
    }


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_reactivated_makes_active_the_nature_alone(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    headers = sessions.changing
    nature = new_type(api, headers, "REA")
    new_category(api, headers, "R1", nature["cost_type_id"])
    off = deactivate(api, headers, nature).json()
    on = api.put(
        f"{TYPES}/{nature['cost_type_id']}/activation",
        headers=headers,
        json={"is_active": True, "lock_version": off["lock_version"]},
    )
    assert (on.status_code, on.json()["is_active"], on.json()["lock_version"]) == (200, True, 2)
    with database.transaction() as session:
        category = session.scalars(select(CostCategory).where(CostCategory.code == "R1")).one()
        assert category.is_active is False
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
    # The slices of the natures and of the categories, on a description of their own: a nature and
    # a category the witness says deactivated are written, then deactivated; run again, they find
    # their objects there and write nothing.
    (tmp_path / "volume").mkdir()
    open_type, shut_type = new_id(), new_id()
    nature = example("cost_types")["items"][0]
    types = [
        {**nature, "cost_type_id": str(open_type), "code": "OPEN"},
        {**nature, "cost_type_id": str(shut_type), "code": "SHUT", "is_active": False},
    ]
    category = example("volume/cost_categories")["items"][0]
    categories = [
        {
            **category,
            "cost_category_id": str(new_id()),
            "code": "OFF",
            "accounting_code": "OFF",
            "cost_type_id": str(open_type),
            "is_active": False,
        }
    ]
    (tmp_path / "cost_types.json").write_text(json.dumps({"value": {"items": types}}))
    (tmp_path / "volume" / "cost_categories.json").write_text(
        json.dumps({"value": {"items": categories}})
    )
    witness = Witness(tmp_path, Act(None, utc_now()))
    with database.transaction() as session:
        assert (load_types(session, witness), load_categories(session, witness)) == (True, True)
    with database.transaction() as session:
        assert (load_types(session, witness), load_categories(session, witness)) == (False, False)
        natures = {
            row.code: (row.is_active, row.lock_version) for row in session.scalars(select(CostType))
        }
        shut = {
            row.code: (row.is_active, row.lock_version)
            for row in session.scalars(select(CostCategory))
        }
    assert natures == {"OPEN": (True, 0), "SHUT": (False, 1)}
    assert shut == {"OFF": (False, 1)}
