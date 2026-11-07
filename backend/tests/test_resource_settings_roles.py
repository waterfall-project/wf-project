# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources (US-0850, WF-REF-0080, 0090, 0100), through the service.

The service is loaded with the witness by its command; the roles are created, read, changed,
deactivated and reactivated by the API, every answer checked against the contract
(``ContractClient``), and the refusals compared with the examples the contract gives. The cascade
of a node over its descendants and its roles is tried here, with the roles; two writes that cross
are tried in ``test_resource_settings_role_locks.py``.
"""

import json
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from support import WITNESS, ContractClient

from waterfall.api.resource_role_admission import category_admission
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
    set_cost_category_activation,
)
from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.resource_settings.interface import (
    active_role_exists,
    category_has_roles,
    read_node,
    role_calendars,
    roles_of_categories,
    set_activation,
)
from waterfall.core.resource_settings.interface import resource_roles as roles_module
from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.settings import WitnessSettings
from waterfall.witness.main import load_witness

if TYPE_CHECKING:
    from support import PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

ROLES = "/api/v1/reference/resource-roles"
NODES = "/api/v1/reference/org-nodes"
CATEGORIES = "/api/v1/reference/cost-categories"
WRITE = "resource_settings.write"
UNKNOWN = "0192a1b2-0000-7000-8000-0000000000ff"


def witness_id(suffix: str) -> str:
    """Give an identifier of the witness by its last digits."""
    return f"01926f3a-7c00-7000-8000-{suffix:0>12}"


# The objects of the witness the tests name.
DT, BE_ELEC, AT_CABL, BE_AUTO = (witness_id(each) for each in ("470", "471", "472", "474"))
INGENIERIE, MISE_EN_SERVICE, SOUS_TRAITANCE = (witness_id(each) for each in ("402", "405", "401"))
MO_003, MO_004 = witness_id("400000000"), witness_id("400000001")
STANDARD, FOUR_DAYS, THIRTY_NINE = (witness_id(each) for each in ("481", "482", "483"))
AUTOM, ING_ELEC, TECH_MES, PROG_AUTO = (witness_id(each) for each in ("453", "451", "452", "455"))


@pytest.fixture
def sessions(witness: Database, reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the resource settings on a service loaded with the witness."""
    del witness
    return reference_sessions("resource_settings")


def example(name: str) -> Any:
    """Read the value of an example of the contract."""
    return json.loads((WITNESS / f"{name}.json").read_text("utf-8"))["value"]


def shape(roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give roles without what a loading writes anew: the columns of audit and the counter."""
    return [
        {key: value for key, value in role.items() if key not in {"audit", "lock_version"}}
        for role in roles
    ]


def listed(api: ContractClient, headers: dict[str, str], query: str = "") -> dict[str, Any]:
    """Read the roles as the service answers, with the query given."""
    response = api.get(f"{ROLES}?{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def codes(api: ContractClient, headers: dict[str, str], query: str = "") -> list[str]:
    """Give the codes of the roles read, in their order."""
    return [role["code"] for role in listed(api, headers, query)["items"]]


def role(api: ContractClient, headers: dict[str, str], code: str) -> dict[str, Any]:
    """Read one role, active or not, by its code."""
    found = listed(api, headers, f"include_inactive=true&code={code}")["items"]
    return next(each for each in found if each["code"] == code)


def new_role(**changes: object) -> dict[str, object]:
    """Give the body of a role under the electrical office, on the standard week, with changes."""
    return {
        "code": "DESS-ELEC",
        "label": "Dessinateur électricien",
        "org_node_id": BE_ELEC,
        "cost_category_id": INGENIERIE,
        "calendar_id": STANDARD,
        "capacity": {"monthly_hours": "520.00", "headcount": "3"},
        **changes,
    }


def change_of(read: dict[str, Any], **changes: object) -> dict[str, object]:
    """Give the body that changes a role as it was read, with changes."""
    return {
        "code": read["code"],
        "label": read["label"],
        "cost_category_id": read["cost_category_id"],
        "calendar_id": read["calendar_id"],
        "capacity": read["capacity"],
        "lock_version": read["lock_version"],
        **changes,
    }


def refusal(response: Any) -> tuple[int, str, list[tuple[str, str]]]:
    """Give the status, the code and the fields (pointer, code) of a refusal."""
    body = response.json()
    fields = [(each["pointer"], each["code"]) for each in body.get("fields", [])]
    return response.status_code, body["code"], fields


def without_correlation(response: Any) -> dict[str, Any]:
    """Give a refusal without its identifier of correlation, which no example can tell."""
    return {key: value for key, value in response.json().items() if key != "correlation_id"}


def activation(
    api: ContractClient, headers: dict[str, str], read: dict[str, Any], *, is_active: bool
) -> Any:
    """Deactivate or reactivate a role at the version read."""
    sent = {"is_active": is_active, "lock_version": read["lock_version"]}
    return api.put(f"{ROLES}/{read['resource_role_id']}/activation", headers=headers, json=sent)


def nodes_by_code(api: ContractClient, headers: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Read every node of the tree, deactivated ones too, by its code."""
    tree = api.get(f"{NODES}?include_inactive=true", headers=headers).json()
    return {each["code"]: each for each in tree}


def node_activation(
    api: ContractClient, headers: dict[str, str], node_id: str, *, is_active: bool
) -> Any:
    """Deactivate or reactivate a node at the version the tree gives."""
    tree = api.get(f"{NODES}?include_inactive=true", headers=headers).json()
    version = next(each["lock_version"] for each in tree if each["org_node_id"] == node_id)
    sent = {"is_active": is_active, "lock_version": version}
    return api.put(f"{NODES}/{node_id}/activation", headers=headers, json=sent)


# The witness and the lists.


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_roles_are_listed_as_the_example_the_faux_back_serves(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The roles are loaded, then those the witness says deactivated deactivated: the calculated
    # becomes the expected, to the audit columns and the counter of writes near.
    read = listed(api, sessions.changing, "include_inactive=true")
    expected = example("resource_roles")
    assert shape(read["items"]) == shape(expected["items"])
    assert read["meta"] == expected["meta"]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loaded_twice_writes_its_roles_once(
    service_database_url: str, witness: Database
) -> None:
    settings = WitnessSettings(
        database_url=SecretStr(service_database_url), witness_path=str(WITNESS)
    )
    assert load_witness(settings) == 0
    with witness.transaction() as session:
        assert session.scalar(select(func.count()).select_from(ResourceRole)) == 5
        # The deactivated calendar of a role, which the calendars of the witness do not give, is
        # there, deactivated; the node a role was created under stays deactivated.
        assert session.get_one(Calendar, UUID(THIRTY_NINE)).is_active is False
        assert session.get_one(OrgNode, UUID(BE_AUTO)).is_active is False


@pytest.mark.requirement("WF-REF-0150-A")
def test_the_active_roles_are_read_by_any_open_session_without_commands(
    api: ContractClient, sessions: PartSessions
) -> None:
    # WF-DEV-0020: whoever reads a project chooses the role of a line of a quote.
    expected = example("resource_roles_reader")
    for headers in (sessions.without, sessions.reading):
        read = listed(api, headers)
        assert shape(read["items"]) == shape(expected["items"])
        assert read["meta"] == expected["meta"]
    assert api.get(ROLES).status_code == 401


@pytest.mark.requirement("WF-REF-0150-A")
@pytest.mark.parametrize("query", ["include_inactive=true", "is_active=false"])
def test_the_deactivated_roles_ask_for_the_permission_to_change_the_resource_settings(
    api: ContractClient, sessions: PartSessions, query: str
) -> None:
    # The decision of the author (#2084): reading the part is not enough.
    for headers in (sessions.without, sessions.reading):
        refused = api.get(f"{ROLES}?{query}", headers=headers)
        assert refusal(refused) == (403, "PERMISSION_MISSING", [])
        assert refused.json()["params"] == {"missing_permission": WRITE}
    assert codes(api, sessions.changing, "is_active=false") == ["AUTOM", "PROG-AUTO"]


@pytest.mark.requirement("WF-ADM-0100-A")
def test_every_write_of_a_role_asks_for_the_permission_to_change_the_resource_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    read = role(api, sessions.changing, "TECH-MES")
    for headers in (sessions.without, sessions.reading):
        for refused in (
            api.post(ROLES, headers=headers, json=new_role()),
            api.patch(f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read)),
            activation(api, headers, read, is_active=False),
        ):
            assert refusal(refused) == (403, "PERMISSION_MISSING", [])
    assert role(api, sessions.changing, "TECH-MES") == read


@pytest.mark.requirement("WF-REF-0090-A")
def test_the_roles_are_searched_filtered_bounded_sorted_and_counted_by_the_server(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    every = "include_inactive=true"
    assert codes(api, headers, "search=électricien") == ["ING-ELEC"]
    assert codes(api, headers, "search=mont-cab") == ["MONT-CAB"]
    assert codes(api, headers, f"{every}&code=AUTO") == ["AUTOM", "PROG-AUTO"]
    # A node keeps its own roles and those of its descendants (WF-REF-0070).
    assert codes(api, headers, f"{every}&org_node_id={BE_ELEC}") == [
        "AUTOM",
        "ING-ELEC",
        "MONT-CAB",
        "TECH-MES",
    ]
    assert codes(api, headers, f"org_node_id={AT_CABL}") == ["MONT-CAB"]
    assert codes(api, headers, f"cost_category_id={MISE_EN_SERVICE}") == ["TECH-MES"]
    assert codes(api, headers, f"{every}&calendar_id={THIRTY_NINE}") == ["AUTOM"]
    assert codes(api, headers, f"{every}&headcount_min=2&headcount_max=3") == ["AUTOM", "PROG-AUTO"]
    bounded = listed(api, headers, f"{every}&monthly_hours_min=485324.00")
    assert shape(bounded["items"]) == shape(example("resource_roles_bounded")["items"])
    assert bounded["meta"] == example("resource_roles_bounded")["meta"]
    page = listed(api, headers, f"{every}&limit=2&offset=1")
    assert ([each["code"] for each in page["items"]], page["meta"]["total"]) == (
        ["ING-ELEC", "MONT-CAB"],
        5,
    )


@pytest.mark.requirement("WF-REF-0090-A")
@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        ("code", ["AUTOM", "ING-ELEC", "MONT-CAB", "PROG-AUTO", "TECH-MES"]),
        ("label&sort_order=desc", ["TECH-MES", "PROG-AUTO", "MONT-CAB", "ING-ELEC", "AUTOM"]),
        # By the labels of the nodes, equals by the label of the role.
        ("org_node", ["MONT-CAB", "PROG-AUTO", "AUTOM", "ING-ELEC", "TECH-MES"]),
        (
            "cost_category&sort_order=desc",
            ["TECH-MES", "AUTOM", "ING-ELEC", "MONT-CAB", "PROG-AUTO"],
        ),
        ("calendar", ["MONT-CAB", "AUTOM", "ING-ELEC", "PROG-AUTO", "TECH-MES"]),
        ("monthly_hours", ["AUTOM", "PROG-AUTO", "MONT-CAB", "TECH-MES", "ING-ELEC"]),
        ("headcount&sort_order=desc", ["ING-ELEC", "TECH-MES", "MONT-CAB", "PROG-AUTO", "AUTOM"]),
        ("is_active", ["ING-ELEC", "MONT-CAB", "TECH-MES", "AUTOM", "PROG-AUTO"]),
    ],
)
def test_the_roles_are_sorted_by_each_column_equals_by_label(
    api: ContractClient, sessions: PartSessions, sort: str, expected: list[str]
) -> None:
    assert codes(api, sessions.changing, f"include_inactive=true&sort_by={sort}") == expected


@pytest.mark.requirement("WF-REF-0090-A")
def test_a_bound_of_the_capacity_malformed_or_inverted_is_refused_on_its_parameter(
    api: ContractClient, sessions: PartSessions
) -> None:
    inverted = api.get(
        f"{ROLES}?monthly_hours_min=1000&monthly_hours_max=500", headers=sessions.changing
    )
    assert without_correlation(inverted) == without_correlation_of("resource_roles_bounds_inverted")
    malformed = api.get(f"{ROLES}?headcount_min=two&headcount_max=1e3", headers=sessions.changing)
    assert refusal(malformed) == (
        422,
        "VALIDATION_FAILED",
        [("/query/headcount_min", "NUMBER_INVALID"), ("/query/headcount_max", "NUMBER_INVALID")],
    )


def without_correlation_of(name: str) -> dict[str, Any]:
    """Give the refusal of an example without its identifier of correlation."""
    return {key: value for key, value in example(name).items() if key != "correlation_id"}


# The creation (WF-REF-0090, WF-REF-0100).


@pytest.mark.requirement("WF-REF-0090-A")
@pytest.mark.requirement("WF-REF-0100-A")
def test_a_role_is_created_with_its_three_attachments_and_its_single_capacity(
    api: ContractClient, sessions: PartSessions
) -> None:
    created = api.post(ROLES, headers=sessions.changing, json=new_role())
    assert created.status_code == 201, created.text
    # The example, but for the identifier the service gives and what the creation writes anew.
    (read,) = shape([created.json()])
    (expected,) = shape([example("resource_role_created")])
    assert {**read, "resource_role_id": None} == {**expected, "resource_role_id": None}
    # One capacity, without a date of validity.
    assert set(created.json()["capacity"]) == {"monthly_hours", "headcount"}
    assert created.json()["lock_version"] == 1
    assert created.json()["audit"]["created_by"]["kind"] == "user"
    assert "DESS-ELEC" in codes(api, sessions.without)


@pytest.mark.requirement("WF-REF-0090-A")
def test_a_role_lacking_an_attachment_absent_or_null_is_refused_at_each_one(
    api: ContractClient, sessions: PartSessions
) -> None:
    sent = new_role(cost_category_id=None, calendar_id=None)
    del sent["org_node_id"]
    refused = api.post(ROLES, headers=sessions.changing, json=sent)
    assert refusal(refused) == (
        422,
        "VALIDATION_FAILED",
        [
            ("/org_node_id", "VALUE_REQUIRED"),
            ("/cost_category_id", "VALUE_REQUIRED"),
            ("/calendar_id", "VALUE_REQUIRED"),
        ],
    )


@pytest.mark.requirement("WF-REF-0090-A")
def test_an_attachment_unknown_out_of_labour_or_deactivated_is_refused_one_reason_a_field(
    api: ContractClient, sessions: PartSessions, database: Database
) -> None:
    headers = sessions.changing
    attachments = new_role(
        org_node_id=UNKNOWN, cost_category_id=SOUS_TRAITANCE, calendar_id=THIRTY_NINE
    )
    refused = api.post(ROLES, headers=headers, json=attachments)
    assert without_correlation(refused) == without_correlation_of(
        "resource_role_attachments_refused"
    )
    unknown = api.post(ROLES, headers=headers, json=new_role(calendar_id=UNKNOWN))
    assert without_correlation(unknown) == without_correlation_of("resource_role_calendar_unknown")
    under_closed = api.post(ROLES, headers=headers, json=new_role(org_node_id=BE_AUTO))
    assert without_correlation(under_closed) == without_correlation_of(
        "resource_role_creation_refused"
    )
    nowhere = api.post(ROLES, headers=headers, json=new_role(cost_category_id=UNKNOWN))
    assert refusal(nowhere)[2] == [("/cost_category_id", "UNKNOWN_COST_CATEGORY")]
    # A category deactivated is refused as such; deactivated and out of labour, as out of labour.
    act = Act(None, utc_now())
    with database.transaction() as session:
        for category in (MO_003, SOUS_TRAITANCE):
            version = session.get_one(CostCategory, UUID(category)).lock_version
            set_cost_category_activation(
                session, UUID(category), is_active=False, lock_version=version, act=act
            )
    closed = api.post(ROLES, headers=headers, json=new_role(cost_category_id=MO_003))
    assert refusal(closed)[2] == [("/cost_category_id", "INACTIVE_REFERENCE_OBJECT")]
    both = api.post(ROLES, headers=headers, json=new_role(cost_category_id=SOUS_TRAITANCE))
    assert refusal(both)[2] == [("/cost_category_id", "LABOUR_CATEGORY_REQUIRED")]
    assert "DESS-ELEC" not in codes(api, headers, "include_inactive=true")


@pytest.mark.requirement("WF-REF-0100-A")
def test_a_negative_capacity_is_refused_at_its_value_and_a_zero_one_is_accepted(
    api: ContractClient, sessions: PartSessions
) -> None:
    negative = {"monthly_hours": "-0.01", "headcount": "-1"}
    refused = api.post(ROLES, headers=sessions.changing, json=new_role(capacity=negative))
    assert refusal(refused) == (
        422,
        "VALIDATION_FAILED",
        [
            ("/capacity/monthly_hours", "VALUE_OUT_OF_RANGE"),
            ("/capacity/headcount", "VALUE_OUT_OF_RANGE"),
        ],
    )
    assert [each["params"] for each in refused.json()["fields"]] == [{"minimum": "0"}] * 2
    zero = {"monthly_hours": "0", "headcount": "0"}
    created = api.post(ROLES, headers=sessions.changing, json=new_role(capacity=zero))
    assert created.status_code == 201
    assert created.json()["capacity"] == zero


@pytest.mark.requirement("WF-REF-0090-A")
def test_a_code_borne_by_another_role_active_or_not_is_refused_naming_it(
    api: ContractClient, sessions: PartSessions
) -> None:
    # AUTOM is borne by the automation engineer, deactivated: the list without them hides him.
    headers = sessions.changing
    taken = api.post(ROLES, headers=headers, json=new_role(code="AUTOM"))
    expected = without_correlation_of("resource_role_code_taken")
    assert without_correlation(taken) == expected
    read = role(api, headers, "TECH-MES")
    changed = api.patch(f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read, code="AUTOM"))
    assert without_correlation(changed) == expected
    # Its own code is not taken from itself.
    kept = api.patch(f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read))
    assert kept.status_code == 200


# The change (WF-REF-0090).


@pytest.mark.requirement("WF-REF-0090-A")
def test_the_node_of_a_role_is_never_changed_and_its_category_is_towards_one_of_labour(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    read = role(api, headers, "TECH-MES")
    moved = api.patch(
        f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read, org_node_id=AT_CABL)
    )
    assert refusal(moved) == (422, "VALIDATION_FAILED", [("/org_node_id", "FIELD_READ_ONLY")])
    # Optional, the node is never null: sent so, it is a value refused, not a node lacking; the
    # calendar sent null is lacking, as at the creation.
    nulled = api.patch(
        f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read, org_node_id=None)
    )
    assert refusal(nulled) == (422, "VALIDATION_FAILED", [("/org_node_id", "VALIDATION_FAILED")])
    lacking = api.patch(
        f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read, calendar_id=None)
    )
    assert refusal(lacking) == (422, "VALIDATION_FAILED", [("/calendar_id", "VALUE_REQUIRED")])
    out_of_labour = api.patch(
        f"{ROLES}/{TECH_MES}",
        headers=headers,
        json=change_of(read, cost_category_id=SOUS_TRAITANCE),
    )
    assert refusal(out_of_labour)[2] == [("/cost_category_id", "LABOUR_CATEGORY_REQUIRED")]
    # Sent unchanged, the node changes nothing; the category moves to an active one of labour.
    renamed = api.patch(
        f"{ROLES}/{TECH_MES}",
        headers=headers,
        json=change_of(read, org_node_id=BE_ELEC, cost_category_id=MO_003, label="Essais"),
    )
    assert renamed.status_code == 200, renamed.text
    assert (renamed.json()["label"], renamed.json()["cost_category_id"]) == ("Essais", MO_003)
    assert renamed.json()["lock_version"] == read["lock_version"] + 1
    assert role(api, headers, "TECH-MES")["org_node_id"] == BE_ELEC


@pytest.mark.requirement("WF-REF-0090-A")
@pytest.mark.requirement("WF-REF-0100-A")
def test_a_change_towards_a_deactivated_calendar_is_refused_but_a_role_keeps_its_own(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    read = role(api, headers, "TECH-MES")
    capacity = {"monthly_hours": read["capacity"]["monthly_hours"], "headcount": "-1"}
    refused = api.patch(
        f"{ROLES}/{TECH_MES}",
        headers=headers,
        json=change_of(read, calendar_id=THIRTY_NINE, capacity=capacity),
    )
    assert without_correlation(refused) == without_correlation_of("resource_role_update_refused")
    # The automation engineer keeps the week of thirty-nine hours, deactivated since: he changes.
    automation = role(api, headers, "AUTOM")
    kept = api.patch(
        f"{ROLES}/{AUTOM}", headers=headers, json=change_of(automation, label="Automaticien senior")
    )
    assert kept.status_code == 200, kept.text
    assert kept.json()["calendar_id"] == THIRTY_NINE


@pytest.mark.requirement("WF-REF-0090-A")
def test_a_change_at_another_version_or_of_an_unknown_role_is_refused(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    read = role(api, headers, "TECH-MES")
    stale = api.patch(f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read, lock_version=7))
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", [])
    assert stale.json()["params"] == {"expected_lock_version": read["lock_version"]}
    absent = api.patch(f"{ROLES}/{UNKNOWN}", headers=headers, json=change_of(read))
    assert absent.status_code == 404


@pytest.mark.requirement("WF-REF-0090-A")
def test_a_calendar_that_would_leave_a_task_without_an_hour_is_refused_as_epic_06_will_say(
    api: ContractClient, sessions: PartSessions, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No task exists before EP-06, which answers the question; the refusal is ready for it.
    def refusing(*_: object) -> bool:
        return False

    monkeypatch.setattr(roles_module, "role_calendar_change_is_admissible", refusing)
    headers = sessions.changing
    read = role(api, headers, "TECH-MES")
    refused = api.patch(
        f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read, calendar_id=FOUR_DAYS)
    )
    assert refusal(refused) == (422, "TASK_WITHOUT_WORKING_HOURS", [])
    # A change that keeps the calendar does not ask.
    assert (
        api.patch(f"{ROLES}/{TECH_MES}", headers=headers, json=change_of(read)).status_code == 200
    )


# What a role binds in the cost settings (WF-REF-0030, WF-REF-0040).


def category_commands(api: ContractClient, headers: dict[str, str], code: str) -> list[str]:
    """Give what the change of nature of a category lacks, as its list says it."""
    read = api.get(f"{CATEGORIES}?search={code}", headers=headers).json()["items"]
    found = next(each for each in read if each["code"] == code)
    return found["available_commands"][1]["missing_conditions"]


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_role_created_or_moved_binds_its_category_and_its_nature_to_labour(
    api: ContractClient,
    sessions: PartSessions,
    reference_sessions: ReferenceSessions,
    database: Database,
) -> None:
    costs = reference_sessions("cost_settings").changing
    headers = sessions.changing
    assert "cost_category_without_role" not in category_commands(api, costs, "MO-003")
    body = new_role(cost_category_id=MO_003)
    created = api.post(ROLES, headers=headers, json=body).json()
    assert "cost_category_without_role" in category_commands(api, costs, "MO-003")
    moved = api.patch(
        f"{ROLES}/{created['resource_role_id']}",
        headers=headers,
        json=change_of(created, cost_category_id=MO_004),
    )
    assert moved.status_code == 200
    assert "cost_category_without_role" not in category_commands(api, costs, "MO-003")
    assert "cost_category_without_role" in category_commands(api, costs, "MO-004")
    # A nature of labour of its own, bound by the role of its single category.
    act = Act(None, utc_now())
    with database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft("MO2", "Intérim", "labor"), act)
        draft = CostCategoryDraft("INT-1", "Intérim", "642", nature.cost_type_id)
        category = create_cost_category(session, draft, act)
    sent = new_role(code="INT", cost_category_id=str(category.cost_category_id))
    assert api.post(ROLES, headers=headers, json=sent).status_code == 201
    natures = api.get("/api/v1/reference/cost-types", headers=costs).json()["items"]
    own = next(each for each in natures if each["code"] == "MO2")
    assert own["available_commands"][1] == {
        "command": "change_kind",
        "is_available": False,
        "missing_conditions": ["cost_type_without_role"],
    }


@pytest.mark.requirement("WF-REF-0040-A")
def test_the_questions_the_other_modules_ask_of_the_roles(witness: Database) -> None:
    with witness.transaction() as session:
        categories = {UUID(INGENIERIE), UUID(SOUS_TRAITANCE), UUID(MISE_EN_SERVICE)}
        assert category_has_roles(session, categories) == {UUID(INGENIERIE), UUID(MISE_EN_SERVICE)}
        assert category_has_roles(session, []) == frozenset()
        named = roles_of_categories(session, [UUID(INGENIERIE)])
        assert [each.code for each in named] == ["AUTOM", "ING-ELEC", "MONT-CAB", "PROG-AUTO"]
        assert roles_of_categories(session, []) == []
        assert role_calendars(session, [UUID(AUTOM), UUID(TECH_MES), UUID(UNKNOWN)]) == {
            UUID(AUTOM): UUID(THIRTY_NINE),
            UUID(TECH_MES): UUID(STANDARD),
        }
        assert role_calendars(session, []) == {}
        assert active_role_exists(session) is True
        admitted = category_admission(session, UUID(SOUS_TRAITANCE))
        assert admitted is not None
        assert (admitted.is_labour, admitted.is_active) == (False, True)
        assert category_admission(session, UUID(UNKNOWN)) is None
        set_activation(
            session,
            UUID(DT),
            is_active=False,
            lock_version=read_node(session, UUID(DT), may_change=False).lock_version,
            act=Act(None, utc_now()),
        )
        assert active_role_exists(session) is False


# The activation and the cascade (WF-REF-0080).


@pytest.mark.requirement("WF-REF-0080-A")
def test_the_deactivation_of_a_node_of_two_levels_of_descendants_deactivates_them_and_their_roles(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    before = {each["code"]: each for each in listed(api, headers, "include_inactive=true")["items"]}
    nodes_before = nodes_by_code(api, headers)
    off = node_activation(api, headers, DT, is_active=False)
    assert off.status_code == 200, off.text
    answer = off.json()
    # The direction, its offices and the workshop under one of them, two levels; the office of
    # automation was deactivated already, with its cell.
    assert [each["code"] for each in answer["org_nodes"]] == ["DT", "BE-ELEC", "AT-CABL", "ACHATS"]
    assert not any(each["is_active"] for each in answer["org_nodes"])
    assert [each["code"] for each in answer["resource_roles"]] == [
        "ING-ELEC",
        "MONT-CAB",
        "TECH-MES",
    ]
    author = api.get("/api/v1/me", headers=headers).json()["user_id"]
    # Each node written, its descendants as itself, at a version further, by the author.
    for each in answer["org_nodes"]:
        assert each["lock_version"] == nodes_before[each["code"]]["lock_version"] + 1
        assert each["audit"]["updated_by"]["user_id"] == author
    nodes_after = nodes_by_code(api, headers)
    assert set(nodes_after) == set(nodes_before)
    written = {each["code"] for each in answer["org_nodes"]}
    assert set(nodes_after) - written == {"BE-AUTO", "CEL-ROBOT"}
    for code, node in nodes_after.items():
        if code in written:
            assert node["lock_version"] == nodes_before[code]["lock_version"] + 1
            assert node["audit"]["updated_by"]["user_id"] == author
        else:
            # Deactivated already, the office of automation and its cell are not written again.
            assert (node["lock_version"], node["audit"]) == (
                nodes_before[code]["lock_version"],
                nodes_before[code]["audit"],
            )
    for each in answer["resource_roles"]:
        assert each["is_active"] is False
        assert each["lock_version"] == before[each["code"]]["lock_version"] + 1
        assert each["audit"]["updated_by"]["user_id"] == author
        assert each["available_commands"] == [
            {
                "command": "reactivate",
                "is_available": False,
                "missing_conditions": ["org_node_active"],
            }
        ]
    # The lists read again show them; the roles deactivated before are not written again.
    assert codes(api, headers) == []
    after = {each["code"]: each for each in listed(api, headers, "include_inactive=true")["items"]}
    assert after["AUTOM"]["lock_version"] == before["AUTOM"]["lock_version"]
    assert api.get(NODES, headers=headers).json() == []


@pytest.mark.requirement("WF-REF-0080-A")
def test_a_role_is_not_reactivated_under_a_deactivated_node_and_a_reactivation_is_of_one_object(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    programmer = role(api, headers, "PROG-AUTO")
    assert programmer["available_commands"] == [
        {"command": "reactivate", "is_available": False, "missing_conditions": ["org_node_active"]}
    ]
    refused = activation(api, headers, programmer, is_active=True)
    assert without_correlation(refused) == without_correlation_of(
        "resource_role_reactivation_refused"
    )
    # Its calendar deactivated, the automation engineer is reactivated: his node is active.
    automation = activation(api, headers, role(api, headers, "AUTOM"), is_active=True)
    assert shape([automation.json()]) == shape([example("resource_role_reactivated")])
    # A node reactivated makes itself active alone; its roles are reactivated one by one.
    assert node_activation(api, headers, BE_ELEC, is_active=False).status_code == 200
    back = node_activation(api, headers, BE_ELEC, is_active=True).json()
    assert ([each["code"] for each in back["org_nodes"]], back["resource_roles"]) == (
        ["BE-ELEC"],
        [],
    )
    assert codes(api, headers, f"org_node_id={BE_ELEC}") == []
    reactivated = activation(api, headers, role(api, headers, "TECH-MES"), is_active=True)
    assert reactivated.status_code == 200
    assert codes(api, headers, f"org_node_id={BE_ELEC}") == ["TECH-MES"]


@pytest.mark.requirement("WF-REF-0080-A")
def test_an_activation_stale_unknown_or_without_change_writes_nothing(
    api: ContractClient, sessions: PartSessions
) -> None:
    headers = sessions.changing
    read = role(api, headers, "ING-ELEC")
    stale = activation(api, headers, {**read, "lock_version": 9}, is_active=False)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", [])
    absent = activation(api, headers, {**read, "resource_role_id": UNKNOWN}, is_active=False)
    assert absent.status_code == 404
    unchanged = activation(api, headers, read, is_active=True)
    assert unchanged.status_code == 200
    assert unchanged.json()["lock_version"] == read["lock_version"]
    off = activation(api, headers, read, is_active=False)
    assert (off.json()["is_active"], off.json()["lock_version"]) == (
        False,
        read["lock_version"] + 1,
    )


# A node moved carries its roles (WF-REF-0070).


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_node_moved_brings_its_roles_and_those_of_its_descendants_under_its_arrival(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The electrical office, with its workshop, moves under the purchases: a role names its node by
    # its identifier, which the move does not write, so the arrival now holds them.
    headers = sessions.changing
    nodes = nodes_by_code(api, headers)
    arrival = nodes["ACHATS"]["org_node_id"]
    everything = "include_inactive=true&sort_by=code"
    carried = listed(api, headers, f"{everything}&org_node_id={BE_ELEC}")["items"]
    assert {each["org_node_id"] for each in carried} == {BE_ELEC, AT_CABL}
    already = listed(api, headers, f"{everything}&org_node_id={arrival}")["items"]
    office = nodes["BE-ELEC"]
    sent = {
        "code": office["code"],
        "label": office["label"],
        "parent_id": arrival,
        "lock_version": office["lock_version"],
    }
    moved = api.patch(f"{NODES}/{BE_ELEC}", headers=headers, json=sent)
    assert moved.status_code == 200, moved.text
    held = listed(api, headers, f"{everything}&org_node_id={arrival}")["items"]
    expected = sorted([*already, *carried], key=lambda each: each["code"])
    assert [(each["code"], each["org_node_id"], each["lock_version"]) for each in held] == [
        (each["code"], each["org_node_id"], each["lock_version"]) for each in expected
    ]
