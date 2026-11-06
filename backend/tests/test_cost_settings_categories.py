# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The categories of cost (US-0820, WF-REF-0040), through the service.

The service is loaded with the witness by its command, and read by three sessions of the cost
settings (``reference_sessions``): one holding nothing of them, one that reads them, one that
changes them. Every answer is checked against the contract (``ContractClient``); the lists are the
examples the faux back serves.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from cost_settings_examples import (
    CATEGORIES,
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
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from support import WAITING

from waterfall.core.cost_settings.records import NATURES_LOCK
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import RoleOfCategory

if TYPE_CHECKING:
    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

CHANGE = "cost_settings.write"
UNKNOWN = "7d1e5b0a-3c94-4f2e-9a68-5b20c4e1f9d3"
REACTIVATION_LACKS = ("reactivate", False, ["cost_type_active"])


@pytest.fixture
def sessions(witness: Database, reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the cost settings on a service loaded with the witness."""
    del witness
    return reference_sessions("cost_settings")


def listed(api: ContractClient, headers: dict[str, str], query: str = "") -> dict[str, Any]:
    """Read the categories by a session, the query given, and expect them."""
    response = api.get(f"{CATEGORIES}?{query}", headers=headers)
    assert response.status_code == 200
    return response.json()


def codes(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the codes of the categories a query keeps, in their order."""
    return [item["code"] for item in listed(api, headers, query)["items"]]


def sent(code: str, cost_type_id: object, **more: object) -> dict[str, object]:
    """Give the body of a category, its accounting code derived from its code."""
    return {
        "code": code,
        "label": f"Libellé {code}",
        "accounting_code": f"7{code}",
        "cost_type_id": str(cost_type_id),
        **more,
    }


def activation(
    api: ContractClient, headers: dict[str, str], item: dict[str, Any], *, on: bool
) -> Any:
    """Deactivate or reactivate a category at the version it was read at."""
    body = {"is_active": on, "lock_version": item["lock_version"]}
    return api.put(
        f"{CATEGORIES}/{item['cost_category_id']}/activation", headers=headers, json=body
    )


def category(api: ContractClient, headers: dict[str, str], code: str) -> dict[str, Any]:
    """Read a category by its code, deactivated ones included."""
    (found,) = listed(api, headers, f"include_inactive=true&search={code}&limit=500")["items"]
    return found


@pytest.mark.requirement("WF-REF-0040-A")
def test_the_witness_categories_are_listed_as_the_example_the_faux_back_serves(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The 200 categories of the volume, by a session that holds nothing of the cost settings: the
    # active categories are the vocabulary of the lines of a quote (WF-DEV-0020).
    expected = [shown(item) for item in example("volume/cost_categories")["items"]]
    for headers in (sessions.without, sessions.reading):
        read = listed(api, headers, "limit=500")
        # The category of provision the bootstrap wrote (#2143) is read beside the witness's.
        kept = [item for item in read["items"] if item["code"] != "PROV-001"]
        assert [shown(item) for item in kept] == expected
        assert all(item["available_commands"] == [] for item in read["items"])
        assert read["meta"] == {"limit": 500, "offset": 0, "total": 201}
    # A page of fifty, the second, as the example of the page.
    page = example("volume/cost_categories_page")
    second = listed(api, sessions.without, "limit=50&offset=50")
    assert [shown(item) for item in second["items"]] == [shown(item) for item in page["items"]]
    assert second["meta"] == {**page["meta"], "total": 201}


@pytest.mark.requirement("WF-REF-0040-A")
def test_the_commands_of_a_category_are_those_of_a_caller_who_changes_the_cost_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    managed = listed(api, sessions.changing, "limit=500")["items"]
    available: list[tuple[str, bool, list[str]]] = [
        ("deactivate", True, []),
        ("change_cost_type", True, []),
    ]
    # The witness rates every category of labour and attaches roles to two of them (US-0850): the
    # labour categories keep their kind for their rates, MO-001 and MO-002 for their roles too, the
    # others can leave it.
    rated = [available[0], ("change_cost_type", False, ["cost_category_unrated"])]
    bound = [
        available[0],
        ("change_cost_type", False, ["cost_category_unrated", "cost_category_without_role"]),
    ]
    assert len(managed) == 201
    for item in managed:
        if item["code"] in {"MO-001", "MO-002"}:
            assert commands(item) == bound
        else:
            assert commands(item) == (rated if item["cost_type_kind"] == "labor" else available)
    assert sum(item["cost_type_kind"] == "labor" for item in managed) == 150


@pytest.mark.requirement("WF-REF-0040-A")
def test_the_categories_are_filtered_searched_sorted_and_paged_by_the_server(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.without
    in_provision = listed(api, headers, f"cost_type_id={PROVISION}")
    assert [item["code"] for item in in_provision["items"]] == ["PRV-001"]
    assert in_provision["meta"]["total"] == 1
    # The search covers the code, the label and the accounting code.
    assert codes(api, headers, "search=prv-001") == ["PRV-001"]
    accounting = category(api, sessions.changing, "ACH-001")["accounting_code"]
    assert codes(api, headers, f"search={accounting}") == ["ACH-001"]
    assert codes(api, headers, "search=sous-traitance&limit=500")[0] == "ACH-001"
    # Sorted by the label of the nature, then the code; descending, the last nature first.
    by_type = listed(api, headers, "sort_by=cost_type&sort_order=desc&limit=3")
    assert [item["cost_type_label"] for item in by_type["items"]] == [
        "Provision pour risques",
        "Provision",
        "Main-d'œuvre",
    ]
    # The provision of the bootstrap bears the lowest accounting code (#2143).
    assert codes(api, headers, "sort_by=accounting_code&limit=2") == ["PROV-001", "ACH-001"]
    assert codes(api, headers, "sort_by=code&sort_order=desc&limit=2") == ["PRV-001", "PROV-001"]
    page = listed(api, headers, "limit=10&offset=195&search=-")
    assert (len(page["items"]), page["meta"]["total"]) == (6, 201)


@pytest.mark.requirement("WF-REF-0040-A")
@pytest.mark.requirement("WF-REF-0150-A")
def test_the_deactivated_categories_are_read_by_the_permission_to_change_and_come_after_the_active(
    api: ContractClient, sessions: PartSessions
) -> None:
    changing = sessions.changing
    first = category(api, changing, "ACH-001")
    assert activation(api, changing, first, on=False).status_code == 200
    assert "ACH-001" not in codes(api, sessions.without, "limit=500")
    assert codes(api, changing, "is_active=false") == ["ACH-001"]
    ordered = codes(api, changing, "include_inactive=true&sort_by=is_active&limit=500")
    assert (ordered[0], ordered[-1], len(ordered)) == ("ACH-002", "ACH-001", 201)
    for headers in (sessions.without, sessions.reading):
        for query in ("include_inactive=true", "is_active=false"):
            response = api.get(f"{CATEGORIES}?{query}", headers=headers)
            assert refusal(response) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_is_created_under_a_nature_with_its_commands_its_nature_and_its_author(
    api: ContractClient, sessions: PartSessions
) -> None:
    author = caller_id(api, sessions.changing)
    response = api.post(CATEGORIES, headers=sessions.changing, json=sent("NEW", LABOUR))
    assert response.status_code == 201
    created = response.json()
    assert (created["cost_type_label"], created["cost_type_kind"], created["is_active"]) == (
        "Main-d'œuvre",
        "labor",
        True,
    )
    assert created["audit"]["created_by"]["user_id"] == author
    assert commands(created) == [("deactivate", True, []), ("change_cost_type", True, [])]
    for headers in (sessions.without, sessions.reading):
        refused = api.post(CATEGORIES, headers=headers, json=sent("X", LABOUR))
        assert refusal(refused) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})


@pytest.mark.requirement("WF-REF-0040-A")
@pytest.mark.parametrize("lacking", ["absent", "null"])
def test_a_category_without_a_nature_is_refused_as_lacking_it(
    api: ContractClient, sessions: PartSessions, lacking: str
) -> None:
    body = sent("NOT", LABOUR)
    if lacking == "absent":
        del body["cost_type_id"]
    else:
        body["cost_type_id"] = None
    response = api.post(CATEGORIES, headers=sessions.changing, json=body)
    assert response.status_code == 422
    assert pointers(response) == [("/cost_type_id", "VALUE_REQUIRED", {})]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_under_an_unknown_or_a_deactivated_nature_is_refused_at_its_nature(
    api: ContractClient, sessions: PartSessions
) -> None:
    unknown = api.post(CATEGORIES, headers=sessions.changing, json=sent("UNK", UNKNOWN))
    assert unknown.status_code == 422
    assert pointers(unknown) == [("/cost_type_id", "UNKNOWN_COST_TYPE", {})]
    deb = next(item for item in listed_types(api, sessions.changing) if item["code"] == "DEB")
    assert deactivate(api, sessions.changing, deb).status_code == 200
    inactive = api.post(CATEGORIES, headers=sessions.changing, json=sent("OFF", NON_LABOUR))
    assert inactive.status_code == 422
    assert pointers(inactive) == [("/cost_type_id", "INACTIVE_REFERENCE_OBJECT", {})]
    assert codes(api, sessions.without, "search=OFF") == []


def listed_types(api: ContractClient, headers: dict[str, str]) -> list[dict[str, Any]]:
    """Read the natures a session sees."""
    return api.get(TYPES, headers=headers).json()["items"]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_whose_code_or_accounting_code_exists_is_refused_naming_each_holder(
    api: ContractClient, sessions: PartSessions
) -> None:
    first = category(api, sessions.changing, "ACH-001")
    second = category(api, sessions.changing, "ACH-002")
    both = sent("ACH-001", LABOUR, accounting_code=second["accounting_code"])
    response = api.post(CATEGORIES, headers=sessions.changing, json=both)
    assert response.status_code == 409
    assert pointers(response) == [
        ("/code", "ALREADY_EXISTS", {"conflicting_object_id": first["cost_category_id"]}),
        (
            "/accounting_code",
            "ALREADY_EXISTS",
            {"conflicting_object_id": second["cost_category_id"]},
        ),
    ]
    # Deactivated, a category holds its codes all the same.
    assert activation(api, sessions.changing, first, on=False).status_code == 200
    only = sent("OTHER", LABOUR, accounting_code=first["accounting_code"])
    again = api.post(CATEGORIES, headers=sessions.changing, json=only)
    assert pointers(again) == [
        ("/accounting_code", "ALREADY_EXISTS", {"conflicting_object_id": first["cost_category_id"]})
    ]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_without_label_or_beyond_the_bounds_of_its_texts_is_refused_field_by_field(
    api: ContractClient, sessions: PartSessions
) -> None:
    body = sent("BAD", LABOUR, label="", accounting_code="9" * 21)
    response = api.post(CATEGORIES, headers=sessions.changing, json=body)
    assert response.status_code == 422
    assert pointers(response) == [
        ("/label", "VALUE_REQUIRED", {}),
        ("/accounting_code", "VALUE_TOO_LONG", {"max_length": 20}),
    ]
    blank = api.post(CATEGORIES, headers=sessions.changing, json=sent("BAD", LABOUR, label="  "))
    assert pointers(blank) == [("/label", "VALIDATION_FAILED", {})]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_unbound_changes_nature_whatever_the_kind_and_keeps_its_codes(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    created = new_category(api, headers, "MOV", LABOUR)
    url = f"{CATEGORIES}/{created['cost_category_id']}"
    body = sent("MOV", PROVISION, label="Déplacée", accounting_code=created["accounting_code"])
    moved = api.patch(url, headers=headers, json={**body, "lock_version": 0})
    assert moved.status_code == 200
    assert (
        moved.json()["cost_type_kind"],
        moved.json()["label"],
        moved.json()["lock_version"],
    ) == (
        "provision",
        "Déplacée",
        1,
    )
    stale = api.patch(url, headers=headers, json={**body, "lock_version": 0})
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    gone = api.patch(f"{CATEGORIES}/{UNKNOWN}", headers=headers, json={**body, "lock_version": 0})
    assert gone.status_code == 404


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_bound_is_refused_a_nature_of_another_kind_for_the_first_condition_it_lacks(
    api: ContractClient, sessions: PartSessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = sessions.changing
    created = new_category(api, headers, "BND", LABOUR)
    identifier = UUID(created["cost_category_id"])
    url = f"{CATEGORIES}/{identifier}"
    body = {
        **sent("BND", NON_LABOUR, accounting_code=created["accounting_code"]),
        "lock_version": 0,
    }
    role = RoleOfCategory(UUID(UNKNOWN), "AUTOM", "Automaticien")
    bind(monkeypatch, employed={identifier}, rated={identifier}, roles={identifier: role})
    employed = api.patch(url, headers=headers, json=body)
    assert refusal(employed) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "cost_category_unused"},
    )
    assert commands(category(api, headers, "BND"))[1] == (
        "change_cost_type",
        False,
        ["cost_category_unused", "cost_category_unrated", "cost_category_without_role"],
    )
    bind(monkeypatch, rated={identifier}, roles={identifier: role})
    rated = api.patch(url, headers=headers, json=body)
    assert refusal(rated) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "cost_category_unrated"},
    )
    bind(monkeypatch, roles={identifier: role})
    held = api.patch(url, headers=headers, json=body)
    assert refusal(held) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {
            "missing_condition": "cost_category_without_role",
            "resource_roles": [
                {"resource_role_id": UNKNOWN, "code": "AUTOM", "label": "Automaticien"}
            ],
        },
    )
    # To a nature of the same kind the move is always accepted, however bound the category is.
    same = api.patch(
        url, headers=headers, json={**body, "cost_type_id": str(LABOUR), "label": "Même"}
    )
    assert (same.status_code, same.json()["label"]) == (200, "Même")
    other = new_type(api, headers, "LAB2", "labor")
    again = api.patch(
        url,
        headers=headers,
        json={**body, "cost_type_id": other["cost_type_id"], "lock_version": 1},
    )
    assert (again.status_code, again.json()["cost_type_id"]) == (200, other["cost_type_id"])
    assert category(api, headers, "BND")["cost_type_id"] == other["cost_type_id"]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_is_not_moved_under_a_nature_unknown_or_deactivated_but_keeps_its_own(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    created = new_category(api, headers, "KEP", NON_LABOUR)
    url = f"{CATEGORIES}/{created['cost_category_id']}"
    body = {**sent("KEP", UNKNOWN, accounting_code=created["accounting_code"]), "lock_version": 0}
    unknown = api.patch(url, headers=headers, json=body)
    assert pointers(unknown) == [("/cost_type_id", "UNKNOWN_COST_TYPE", {})]
    off = new_type(api, headers, "OFF2", "non_labor")
    assert deactivate(api, headers, off).status_code == 200
    inactive = api.patch(url, headers=headers, json={**body, "cost_type_id": off["cost_type_id"]})
    assert pointers(inactive) == [("/cost_type_id", "INACTIVE_REFERENCE_OBJECT", {})]
    # Its own nature, deactivated since, is kept: the category changes its label under it.
    deb = next(item for item in listed_types(api, headers) if item["code"] == "DEB")
    assert deactivate(api, headers, deb).status_code == 200
    # The cascade of its nature advanced its counter.
    kept = api.patch(
        url,
        headers=headers,
        json={**body, "cost_type_id": str(NON_LABOUR), "lock_version": 1},
    )
    assert kept.status_code == 200
    assert (kept.json()["cost_type_is_active"], kept.json()["is_active"]) == (False, False)
    lacking = {name: value for name, value in body.items() if name != "cost_type_id"}
    missing = api.patch(url, headers=headers, json={**lacking, "lock_version": 2})
    assert pointers(missing) == [("/cost_type_id", "VALUE_REQUIRED", {})]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_code_another_category_holds_is_refused_on_a_change_but_not_its_own(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    first = category(api, headers, "ACH-001")
    second = category(api, headers, "ACH-002")
    body = sent("ACH-001", first["cost_type_id"], accounting_code=first["accounting_code"])
    same = api.patch(
        f"{CATEGORIES}/{first['cost_category_id']}",
        headers=headers,
        json={**body, "label": "Renommée", "lock_version": first["lock_version"]},
    )
    assert same.status_code == 200
    taken = api.patch(
        f"{CATEGORIES}/{second['cost_category_id']}",
        headers=headers,
        json={**body, "lock_version": second["lock_version"]},
    )
    assert taken.status_code == 409
    assert [each[0] for each in pointers(taken)] == ["/code", "/accounting_code"]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_under_a_nature_deactivated_is_not_reactivated_and_its_command_says_so(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    nature = new_type(api, headers, "CLS")
    created = new_category(api, headers, "CLC", nature["cost_type_id"])
    off = deactivate(api, headers, nature).json()
    closed = category(api, headers, "CLC")
    # The cascade deactivated it with its nature; its reactivation lacks the nature active.
    assert (closed["is_active"], closed["cost_type_is_active"]) == (False, False)
    assert commands(closed)[0] == REACTIVATION_LACKS
    refused = activation(api, headers, closed, on=True)
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "cost_type_active", "conflicting_object_id": nature["cost_type_id"]},
    )
    on = api.put(
        f"{TYPES}/{nature['cost_type_id']}/activation",
        headers=headers,
        json={"is_active": True, "lock_version": off["lock_version"]},
    )
    assert on.status_code == 200
    # The nature alone is active again: the category is reactivated one by one.
    still = category(api, headers, "CLC")
    assert (still["is_active"], still["cost_type_is_active"]) == (False, True)
    assert commands(still)[0] == ("reactivate", True, [])
    back = activation(api, headers, still, on=True)
    assert (back.status_code, back.json()["is_active"]) == (200, True)
    assert created["cost_category_id"] == back.json()["cost_category_id"]


@pytest.mark.requirement("WF-REF-0040-A")
def test_the_activation_of_a_category_is_refused_stale_unknown_or_without_the_permission(
    api: ContractClient, sessions: PartSessions
) -> None:
    first = category(api, sessions.changing, "ACH-001")
    url = f"{CATEGORIES}/{first['cost_category_id']}/activation"
    stale = api.put(url, headers=sessions.changing, json={"is_active": False, "lock_version": 9})
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 0})
    gone = api.put(
        f"{CATEGORIES}/{UNKNOWN}/activation",
        headers=sessions.changing,
        json={"is_active": False, "lock_version": 0},
    )
    assert gone.status_code == 404
    for headers in (sessions.without, sessions.reading):
        denied = api.put(url, headers=headers, json={"is_active": False, "lock_version": 0})
        assert refusal(denied) == (403, "PERMISSION_MISSING", {"missing_permission": CHANGE})
    assert category(api, sessions.changing, "ACH-001")["is_active"] is True


def wait_for_locks(database: Database, waiting: int) -> None:
    """Wait until ``waiting`` transactions at least wait for a lock, in 10 seconds at most."""
    deadline = time.monotonic() + 10
    with database.engine.connect() as watching:
        while time.monotonic() < deadline:
            if (watching.scalar(WAITING) or 0) >= waiting:
                return
            watching.rollback()
            time.sleep(0.05)
    pytest.fail(f"fewer than {waiting} transactions wait for a lock")


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_created_while_its_nature_is_being_deactivated_is_refused_not_left_active(
    api: ContractClient, database: Database, sessions: PartSessions
) -> None:
    # The real deactivation of the nature and a creation under it both ask for the lock of the
    # natures, which another transaction holds: both wait, then one takes it. Created first, the
    # category is deactivated by the cascade; after, it is refused. Read before the lock, the
    # nature would be active, and a category be written active under a nature deactivated.
    nature = new_type(api, sessions.changing, "RACE")
    off = {"is_active": False, "lock_version": nature["lock_version"]}
    url = f"{TYPES}/{nature['cost_type_id']}/activation"
    with ThreadPoolExecutor(2) as other, Session(database.engine) as holding:
        holding.execute(select(func.pg_advisory_xact_lock(NATURES_LOCK)))
        creating = other.submit(
            api.post,
            CATEGORIES,
            headers=sessions.changing,
            json=sent("LATE", nature["cost_type_id"]),
        )
        deactivating = other.submit(api.put, url, headers=sessions.changing, json=off)
        # Both wait for the lock: without it, the deactivation would end at once and the
        # interleaving (nature read active, nature deactivated, category written active) be missed.
        wait_for_locks(database, 2)
        assert not deactivating.done()
        assert not creating.done()
        holding.commit()
        answer = creating.result(timeout=10)
        assert deactivating.result(timeout=10).status_code == 200
    assert answer.status_code in {201, 422}
    if answer.status_code == 422:
        assert pointers(answer) == [("/cost_type_id", "INACTIVE_REFERENCE_OBJECT", {})]
    with database.transaction() as session:
        active = session.scalars(
            select(CostCategory.code).where(
                CostCategory.cost_type_id == UUID(nature["cost_type_id"]), CostCategory.is_active
            )
        ).all()
        shut = session.scalars(
            select(CostType.is_active).where(CostType.id == UUID(nature["cost_type_id"]))
        ).one()
    assert (shut, active) == (False, [])


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_created_after_the_deactivation_of_its_nature_is_refused_at_its_nature(
    api: ContractClient, sessions: PartSessions
) -> None:
    nature = new_type(api, sessions.changing, "AFTER")
    off = {"is_active": False, "lock_version": nature["lock_version"]}
    shut = api.put(
        f"{TYPES}/{nature['cost_type_id']}/activation", headers=sessions.changing, json=off
    )
    assert shut.status_code == 200
    late = api.post(
        CATEGORIES, headers=sessions.changing, json=sent("LATE", nature["cost_type_id"])
    )
    assert late.status_code == 422
    assert pointers(late) == [("/cost_type_id", "INACTIVE_REFERENCE_OBJECT", {})]


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_last_category_of_provision_is_deactivated_alone_without_refusal(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « La désactivation de la dernière catégorie active de type provision pour risques est
    # acceptée » : the category alone, its nature staying active.
    before = category(api, sessions.changing, "PRV-001")
    assert before["is_active"] is True
    done = activation(api, sessions.changing, before, on=False)
    assert done.status_code == 200
    assert (done.json()["is_active"], done.json()["lock_version"]) == (
        False,
        before["lock_version"] + 1,
    )
    after = category(api, sessions.changing, "PRV-001")
    assert (after["is_active"], after["cost_type_is_active"]) == (False, True)
    assert codes(api, sessions.without, "search=PRV-001") == []


@pytest.mark.requirement("WF-REF-0030-A")
def test_the_deactivation_of_the_nature_of_provision_deactivates_its_last_category_without_refusal(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The same acceptance by the nature: its category follows, the version one further.
    before = category(api, sessions.changing, "PRV-001")
    prv = next(item for item in listed_types(api, sessions.changing) if item["code"] == "PRV")
    assert deactivate(api, sessions.changing, prv).status_code == 200
    after = category(api, sessions.changing, "PRV-001")
    assert (after["is_active"], after["lock_version"]) == (False, before["lock_version"] + 1)
    assert codes(api, sessions.without, "search=PRV-001") == []


@pytest.mark.requirement("WF-REF-0040-A")
def test_two_simultaneous_creations_of_one_code_leave_one_category_and_one_refusal(
    api: ContractClient, sessions: PartSessions
) -> None:
    body = sent("TWIN", LABOUR)

    def create(_: int) -> Any:
        return api.post(CATEGORIES, headers=sessions.changing, json=body)

    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(create, range(2)))
    created = [answer for answer in answers if answer.status_code == 201]
    refused = [answer for answer in answers if answer.status_code == 409]
    assert (len(created), len(refused)) == (1, 1)
    holder = created[0].json()["cost_category_id"]
    assert pointers(refused[0]) == [
        ("/code", "ALREADY_EXISTS", {"conflicting_object_id": holder}),
        ("/accounting_code", "ALREADY_EXISTS", {"conflicting_object_id": holder}),
    ]
    assert codes(api, sessions.without, "search=TWIN") == ["TWIN"]
