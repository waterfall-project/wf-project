# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Nothing of the reference is deleted, a deactivated object stays named (US-0880, WF-REF-0010).

The five lists the reference offers — the nodes, the roles, the calendars, the natures and the
categories of cost — and the grid of the rates are read by three sessions of their part, as the
story says: one holding nothing of the reference, one that reads it, one that changes it
(``reference_sessions``). The service is loaded with the witness; an object is created, deactivated
and reactivated by the API, every answer checked against the contract (``ContractClient``). The
story adds no operation: it observes what the stories of the objects built.

``include_inactive`` and ``is_active`` false are read under the permission to change the part, as
the frozen contract says (decision of the author of 2026-11-06, #2084, option A), not under the
permission to read it.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from access_rows import account, role
from cost_settings_examples import CATEGORIES, LABOUR, TYPES, caller_id, example, new_category
from cost_settings_examples import new_type as create_type
from cost_settings_examples import refusal as refused
from realm import KEY
from sqlalchemy import func, select
from support import bearer, operations

from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from collections.abc import Callable

    from openapi_core import OpenAPI
    from realm import TestRealm
    from support import ContractClient, PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

NODES = "/api/v1/reference/org-nodes"
ROLES = "/api/v1/reference/resource-roles"
CALENDARS = "/api/v1/reference/calendars"
GRID = "/api/v1/reference/hourly-rates"
USERS = "/api/v1/users"
INACTIVE = ["include_inactive=true", "is_active=false", "is_active=true&include_inactive=true"]
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

type World = dict[str, PartSessions]


@dataclass(frozen=True, slots=True)
class Kind:
    """A list of the reference: where it is, how it names its objects, how one is created."""

    name: str
    url: str
    key: str
    part: str
    make: Callable[[ContractClient, World, str], dict[str, Any]]
    tree: bool = False


def make_node(api: ContractClient, world: World, tag: str) -> dict[str, Any]:
    """Create a node of the organisation, with no descendant and no role."""
    sent = {"code": f"N-{tag}", "label": f"Nœud {tag}"}
    response = api.post(NODES, headers=world["resource_settings"].changing, json=sent)
    assert response.status_code == 201, response.text
    return response.json()


def make_calendar(api: ContractClient, world: World, tag: str) -> dict[str, Any]:
    """Create a calendar that is not the default."""
    hours = {day: "0" if day in DAYS[5:] else "8" for day in DAYS}
    sent = {"label": f"Calendrier {tag}", "weekly_hours": hours}
    response = api.post(CALENDARS, headers=world["resource_settings"].changing, json=sent)
    assert response.status_code == 201, response.text
    return response.json()


def make_type(api: ContractClient, world: World, tag: str) -> dict[str, Any]:
    """Create a nature of labour, with no category."""
    return create_type(api, world["cost_settings"].changing, f"T-{tag}")


def make_category(api: ContractClient, world: World, tag: str) -> dict[str, Any]:
    """Create a category of labour under the nature of labour of the witness."""
    return new_category(api, world["cost_settings"].changing, f"C-{tag}", LABOUR)


def make_role(api: ContractClient, world: World, tag: str) -> dict[str, Any]:
    """Create a role under a node, a category and a calendar of its own."""
    sent = {
        "code": f"R-{tag}",
        "label": f"Rôle {tag}",
        "org_node_id": make_node(api, world, tag)["org_node_id"],
        "cost_category_id": make_category(api, world, tag)["cost_category_id"],
        "calendar_id": make_calendar(api, world, tag)["calendar_id"],
        "capacity": {"monthly_hours": "520.00", "headcount": "3"},
    }
    response = api.post(ROLES, headers=world["resource_settings"].changing, json=sent)
    assert response.status_code == 201, response.text
    return response.json()


KINDS = [
    Kind("org_node", NODES, "org_node_id", "resource_settings", make_node, tree=True),
    Kind("resource_role", ROLES, "resource_role_id", "resource_settings", make_role),
    Kind("calendar", CALENDARS, "calendar_id", "resource_settings", make_calendar),
    Kind("cost_type", TYPES, "cost_type_id", "cost_settings", make_type),
    Kind("cost_category", CATEGORIES, "cost_category_id", "cost_settings", make_category),
]
BY_NAME = {kind.name: kind for kind in KINDS}
EACH_LIST = pytest.mark.parametrize("kind", KINDS, ids=[kind.name for kind in KINDS])


@pytest.fixture
def world(witness: Database, reference_sessions: ReferenceSessions) -> World:
    """Give, on a service loaded with the witness, the three sessions of each part."""
    del witness
    return {part: reference_sessions(part) for part in ("cost_settings", "resource_settings")}


def read(
    api: ContractClient, headers: dict[str, str], kind: Kind, query: str = ""
) -> list[dict[str, Any]]:
    """Read a list by a session, the query given, whole; expect it and give its objects."""
    asked = [query] if query else []
    response = api.get(
        f"{kind.url}?{'&'.join([*asked, *([] if kind.tree else ['limit=500'])])}", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json() if kind.tree else response.json()["items"]


def identifiers(
    api: ContractClient, headers: dict[str, str], kind: Kind, query: str = ""
) -> list[str]:
    """Give the identifiers of the objects a list keeps."""
    return [each[kind.key] for each in read(api, headers, kind, query)]


def find(api: ContractClient, world: World, kind: Kind, identifier: str) -> dict[str, Any]:
    """Read one object, active or not, as the session that changes its part sees it."""
    listed = read(api, world[kind.part].changing, kind, "include_inactive=true")
    return next(each for each in listed if each[kind.key] == identifier)


def switch(
    api: ContractClient, world: World, kind: Kind, identifier: str, *, active: bool
) -> dict[str, Any]:
    """Deactivate or reactivate an object by its command, at the version read; give it written."""
    version = find(api, world, kind, identifier)["lock_version"]
    sent = {"is_active": active, "lock_version": version}
    response = api.put(
        f"{kind.url}/{identifier}/activation", headers=world[kind.part].changing, json=sent
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # The answer of a node names the nodes written, and the roles, by the cascade.
    return (
        next(each for each in body["org_nodes"] if each[kind.key] == identifier)
        if kind.tree
        else body
    )


def sessions_of(world: World, kind: Kind) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Give the headers of the sessions of the part of a list: without, reading, changing."""
    held = world[kind.part]
    return held.without, held.reading, held.changing


def moment(text: str) -> datetime:
    """Read a moment of an audit column."""
    return datetime.fromisoformat(text)


# The lists.


@pytest.mark.requirement("WF-REF-0150-A")
@EACH_LIST
def test_every_open_session_reads_the_active_objects_of_a_list_and_no_other(
    api: ContractClient, world: World, kind: Kind
) -> None:
    # Constat #1746: the active objects are the vocabulary of the forms, read by any session that
    # is open, whatever it holds of the reference; the anonymous caller is not open (401).
    created = kind.make(api, world, "ACT")[kind.key]
    off = kind.make(api, world, "OFF")[kind.key]
    switch(api, world, kind, off, active=False)
    seen = [read(api, headers, kind) for headers in sessions_of(world, kind)]
    for items in seen:
        assert created in [each[kind.key] for each in items]
        assert off not in [each[kind.key] for each in items]
        assert all(each["is_active"] for each in items)
    assert len({tuple(each[kind.key] for each in items) for items in seen}) == 1
    for items in seen[:2]:
        assert all(each["available_commands"] == [] for each in items)
    assert api.get(kind.url).status_code == 401


@pytest.mark.requirement("WF-REF-0150-A")
def test_the_grid_of_the_rates_is_unknown_without_the_permission_to_read_the_cost_settings(
    api: ContractClient, world: World
) -> None:
    # Constat #1746, WF-ADM-0110: the grid is not a vocabulary; whoever may not read the cost
    # settings is told it does not exist (404), the example the contract gives.
    code = example("hourly_rate_grid_not_readable")["code"]
    cost = world["cost_settings"]
    absent = api.get(f"{GRID}?limit=500", headers=cost.without)
    assert (absent.status_code, absent.json()["code"]) == (404, code)
    for headers in (cost.reading, cost.changing):
        rows = api.get(f"{GRID}?limit=500", headers=headers).json()["rows"]
        assert rows
        assert all(each["is_active"] for each in rows)


@pytest.mark.requirement("WF-REF-0150-A")
@EACH_LIST
def test_a_deactivated_object_leaves_the_default_list_and_is_listed_to_who_may_change_the_part(
    api: ContractClient, world: World, kind: Kind
) -> None:
    identifier = kind.make(api, world, "OFF")[kind.key]
    switch(api, world, kind, identifier, active=False)
    without, reading, changing = sessions_of(world, kind)
    for headers in (without, reading, changing):
        assert identifier not in identifiers(api, headers, kind)
    # The permission to read the part does not open the deactivated objects (#2084): the
    # `*_inactive_forbidden` examples of the contract name the permission to change.
    for query in INACTIVE:
        for headers in (without, reading):
            response = api.get(f"{kind.url}?{query}", headers=headers)
            assert refused(response) == (
                403,
                "PERMISSION_MISSING",
                {"missing_permission": f"{kind.part}.write"},
            )
    assert identifier in identifiers(api, changing, kind, "include_inactive=true")
    assert identifier in identifiers(api, changing, kind, "is_active=false")
    assert identifier not in identifiers(
        api, changing, kind, "is_active=true&include_inactive=true"
    )
    if not kind.tree:
        # The tree brings the ancestors of what it keeps; a list keeps only the deactivated.
        assert not any(each["is_active"] for each in read(api, changing, kind, "is_active=false"))


@pytest.mark.requirement("WF-REF-0150-A")
def test_a_deactivated_category_leaves_the_grid_and_is_read_by_who_may_change_the_cost_settings(
    api: ContractClient, world: World
) -> None:
    kind = BY_NAME["cost_category"]
    created = kind.make(api, world, "GRID")
    code = created["code"]
    cost = world["cost_settings"]
    switch(api, world, kind, created[kind.key], active=False)

    def rows(headers: dict[str, str], query: str = "") -> dict[str, dict[str, Any]]:
        response = api.get(f"{GRID}?limit=500&{query}", headers=headers)
        assert response.status_code == 200, response.text
        return {each["code"]: each for each in response.json()["rows"]}

    assert code not in rows(cost.reading)
    assert code not in rows(cost.changing)
    for query in INACTIVE:
        # Unknown before it is forbidden: who cannot read the grid is told 404, not 403.
        assert api.get(f"{GRID}?{query}", headers=cost.without).status_code == 404
        denied = api.get(f"{GRID}?{query}", headers=cost.reading)
        assert refused(denied) == (
            403,
            "PERMISSION_MISSING",
            {"missing_permission": "cost_settings.write"},
        )
    assert rows(cost.changing, "include_inactive=true")[code]["is_active"] is False
    # ``>=`` on purpose: the witness holds other deactivated categories, this one among them.
    assert set(rows(cost.changing, "is_active=false")) >= {code}
    assert code not in rows(cost.changing, "is_active=true&include_inactive=true")
    switch(api, world, kind, created[kind.key], active=True)
    assert rows(cost.reading)[code]["is_active"] is True


# The reactivation.


@pytest.mark.requirement("WF-REF-0010-A")
@pytest.mark.requirement("WF-REF-0150-A")
@EACH_LIST
def test_an_object_is_reactivated_by_its_command_under_the_permission_to_change_and_proposed_again(
    api: ContractClient, world: World, kind: Kind
) -> None:
    identifier = kind.make(api, world, "BACK")[kind.key]
    switch(api, world, kind, identifier, active=False)
    version = find(api, world, kind, identifier)["lock_version"]
    without, reading, changing = sessions_of(world, kind)
    for headers in (without, reading):
        response = api.put(
            f"{kind.url}/{identifier}/activation",
            headers=headers,
            json={"is_active": True, "lock_version": version},
        )
        assert refused(response) == (
            403,
            "PERMISSION_MISSING",
            {"missing_permission": f"{kind.part}.write"},
        )
    # Nothing was written, and the object is still not proposed.
    still = find(api, world, kind, identifier)
    assert (still["is_active"], still["lock_version"]) == (False, version)
    assert identifier not in identifiers(api, without, kind)
    back = switch(api, world, kind, identifier, active=True)
    assert back["is_active"] is True
    for headers in (without, reading, changing):
        assert identifier in identifiers(api, headers, kind)


# The audit columns, and the journal.


@pytest.mark.requirement("WF-DAT-0070-A")
@pytest.mark.requirement("WF-SEC-0030-A")
@EACH_LIST
def test_the_audit_columns_of_a_deactivated_then_reactivated_object_name_the_author_and_the_moment(
    api: ContractClient,
    database: Database,
    reference_sessions: ReferenceSessions,
    world: World,
    kind: Kind,
) -> None:
    # WF-DAT-0070: who touched a row last, and when. Two accounts that change the part: the one
    # who creates and reactivates, the one who deactivates. And no inscription in the journal of
    # audit: WF-SEC-0030 lists none for the reference.
    first = world[kind.part].changing
    second = reference_sessions(kind.part).changing
    author, other = caller_id(api, first), caller_id(api, second)
    assert author != other
    created = kind.make(api, world, "AUD")
    identifier = created[kind.key]
    assert created["audit"]["created_by"]["user_id"] == author

    def entries() -> int:
        with database.transaction() as session:
            return session.scalar(select(func.count()).select_from(AuditEntry)) or 0

    before = entries()
    version = find(api, world, kind, identifier)["lock_version"]
    sent = {"is_active": False, "lock_version": version}
    response = api.put(f"{kind.url}/{identifier}/activation", headers=second, json=sent)
    assert response.status_code == 200, response.text
    off = find(api, world, kind, identifier)
    assert off["is_active"] is False
    assert off["audit"]["created_by"] == created["audit"]["created_by"]
    assert off["audit"]["created_at"] == created["audit"]["created_at"]
    assert off["audit"]["updated_by"]["user_id"] == other
    assert moment(off["audit"]["updated_at"]) > moment(created["audit"]["updated_at"])
    assert off["lock_version"] == version + 1
    sent = {"is_active": True, "lock_version": off["lock_version"]}
    assert (
        api.put(f"{kind.url}/{identifier}/activation", headers=first, json=sent).status_code == 200
    )
    on = find(api, world, kind, identifier)
    assert on["is_active"] is True
    assert on["audit"]["created_by"]["user_id"] == author
    assert on["audit"]["updated_by"]["user_id"] == author
    assert moment(on["audit"]["updated_at"]) > moment(off["audit"]["updated_at"])
    assert on["lock_version"] == version + 2
    assert entries() == before


# What a deactivated object still names.


@pytest.mark.requirement("WF-REF-0010-A")
def test_a_deactivated_object_stays_named_where_it_is_employed_and_is_not_proposed(
    api: ContractClient, database: Database, realm: TestRealm, world: World
) -> None:
    node, category, calendar = BY_NAME["org_node"], BY_NAME["cost_category"], BY_NAME["calendar"]
    created = make_role(api, world, "USE")
    role_id = created["resource_role_id"]
    switch(api, world, calendar, created["calendar_id"], active=False)
    switch(api, world, category, created["cost_category_id"], active=False)
    resource = world["resource_settings"]
    for headers in (resource.without, resource.reading, resource.changing):
        # The role is active, and names its category and its calendar deactivated; the lists of
        # choice of its form propose neither.
        (employing,) = [
            each
            for each in read(api, headers, BY_NAME["resource_role"])
            if each["resource_role_id"] == role_id
        ]
        assert employing["cost_category_label"] == created["cost_category_label"]
        assert employing["calendar_label"] == created["calendar_label"]
        assert created["calendar_id"] not in identifiers(api, headers, calendar)
    assert created["cost_category_id"] not in identifiers(
        api, world["cost_settings"].without, category
    )
    # A node deactivated takes its roles with it; it is named by the role, and by the account
    # attached to it, which a reader of the accounts sees with the node's label.
    held = role(database, "Lecture des comptes", permissions=("users.read",))
    subject = uuid4().hex
    account(database, "Lectrice", "Alix", roles=(held,), idp_subject=subject)
    attached = account(database, "Attachee", "Camille", org_node_id=created["org_node_id"])
    switch(api, world, node, created["org_node_id"], active=False)
    assert created["org_node_id"] not in identifiers(api, resource.without, node)
    off = find(api, world, BY_NAME["resource_role"], role_id)
    assert off["is_active"] is False
    assert off["org_node_label"] == created["org_node_label"]
    reader = bearer(realm.token(subject, KEY))
    shown = api.get(f"{USERS}/{attached}", headers=reader).json()
    assert (shown["org_node_id"], shown["org_node_label"]) == (
        created["org_node_id"],
        created["org_node_label"],
    )


@pytest.mark.requirement("WF-REF-0010-A")
def test_a_deactivated_nature_stays_named_by_its_categories_which_are_deactivated_with_it(
    api: ContractClient, world: World
) -> None:
    nature, category = BY_NAME["cost_type"], BY_NAME["cost_category"]
    created = make_type(api, world, "NAT")
    sent = {
        "code": "C-NAT",
        "label": "Catégorie NAT",
        "accounting_code": "6NAT",
        "cost_type_id": created["cost_type_id"],
    }
    cost = world["cost_settings"]
    posted = api.post(CATEGORIES, headers=cost.changing, json=sent)
    assert posted.status_code == 201
    switch(api, world, nature, created["cost_type_id"], active=False)
    assert created["cost_type_id"] not in identifiers(api, cost.without, nature)
    assert posted.json()["cost_category_id"] not in identifiers(api, cost.without, category)
    held = find(api, world, category, posted.json()["cost_category_id"])
    assert held["is_active"] is False
    assert held["cost_type_label"] == created["label"]


# What a deactivation or a modification writes.


def snapshot(api: ContractClient, world: World) -> dict[tuple[str, str], Any]:
    """Give what every object of the reference bears of its writes: its counter, its audit."""
    found: dict[tuple[str, str], Any] = {}
    for kind in KINDS:
        for each in read(api, world[kind.part].changing, kind, "include_inactive=true"):
            found[kind.name, each[kind.key]] = (each["lock_version"], each["audit"])
    cost = world["cost_settings"].changing
    grid = api.get(f"{GRID}?include_inactive=true&limit=500", headers=cost).json()
    for row in grid["rows"]:
        found["grid", row["code"]] = [cell and cell["audit"] for cell in row["cells"]]
    return found


def written(
    before: dict[tuple[str, str], Any], after: dict[tuple[str, str], Any], *, grid: bool = True
) -> set[tuple[str, str]]:
    """Name the objects whose counter or audit columns are not what they were."""
    return {
        key
        for key in before.keys() | after.keys()
        if before.get(key) != after.get(key) and (grid or key[0] != "grid")
    }


@pytest.mark.requirement("WF-REF-0020-A")
@EACH_LIST
def test_a_deactivation_and_a_reactivation_write_the_object_and_nothing_else(
    api: ContractClient, world: World, kind: Kind
) -> None:
    # The object has no descendant, no category and no role: what the cascade names is it alone.
    # Every other object of the reference, those that employ it among them, keeps its audit.
    identifier = kind.make(api, world, "ONE")[kind.key]
    start = snapshot(api, world)
    switch(api, world, kind, identifier, active=False)
    stopped = snapshot(api, world)
    # The grid shows a category of labour too: the same object, read another way.
    assert written(start, stopped, grid=False) == {(kind.name, identifier)}
    switch(api, world, kind, identifier, active=True)
    assert written(stopped, snapshot(api, world), grid=False) == {(kind.name, identifier)}


@pytest.mark.requirement("WF-REF-0130-A")
def test_a_modification_writes_the_object_and_nothing_that_employs_it(
    api: ContractClient, world: World
) -> None:
    # A rate corrected, the category of a role changed, a node, a calendar and a category renamed:
    # the roles that employ them are not written, and no table of a revision is the story's.
    created = make_role(api, world, "MOD")
    other = make_category(api, world, "OTH")
    cost, resource = world["cost_settings"].changing, world["resource_settings"].changing
    before = snapshot(api, world)
    rate = f"{CATEGORIES}/{created['cost_category_id']}/hourly-rates/2026"
    entered = api.put(rate, headers=cost, json={"amount": "100"})
    assert entered.status_code == 200, entered.text
    corrected = api.put(
        rate, headers=cost, json={"amount": "110", "lock_version": entered.json()["lock_version"]}
    )
    assert corrected.status_code == 200, corrected.text
    after = snapshot(api, world)
    assert written(before, after) == {("grid", "C-MOD")}
    before = after
    changed = {
        "code": created["code"],
        "label": created["label"],
        "cost_category_id": other["cost_category_id"],
        "calendar_id": created["calendar_id"],
        "capacity": created["capacity"],
        "lock_version": created["lock_version"],
    }
    moved = api.patch(f"{ROLES}/{created['resource_role_id']}", headers=resource, json=changed)
    assert moved.status_code == 200, moved.text
    after = snapshot(api, world)
    assert written(before, after) == {("resource_role", created["resource_role_id"])}
    weekly = find(api, world, BY_NAME["calendar"], created["calendar_id"])["weekly_hours"]
    renamings = (
        (BY_NAME["org_node"], {"code": "N-MOD", "label": "Renommé", "parent_id": None}),
        (BY_NAME["calendar"], {"label": "Renommé", "weekly_hours": weekly}),
        (
            BY_NAME["cost_category"],
            {
                "code": "C-MOD",
                "label": "Renommée",
                "accounting_code": "6C-MOD",
                "cost_type_id": str(LABOUR),
            },
        ),
    )
    for kind, patch in renamings:
        identifier = created[kind.key]
        before = snapshot(api, world)
        version = find(api, world, kind, identifier)["lock_version"]
        response = api.patch(
            f"{kind.url}/{identifier}",
            headers=world[kind.part].changing,
            json={**patch, "lock_version": version},
        )
        assert response.status_code == 200, response.text
        assert written(before, snapshot(api, world)) == {(kind.name, identifier)}


# Nothing is deleted.


@pytest.mark.requirement("WF-REF-0010-A")
def test_no_operation_of_the_contract_deletes_an_object_of_the_reference(
    api: ContractClient, contract: OpenAPI, world: World
) -> None:
    declared = [
        (method, path) for method, path in operations(contract).values() if "/reference/" in path
    ]
    assert ("PUT", f"{NODES}/{{org_node_id}}/activation") in declared
    assert [each for each in declared if each[0] == "DELETE"] == []
    # And the service serves none: a deletion of an object, or of a rate, is an unknown address.
    made = {kind.name: kind.make(api, world, f"D{n}")[kind.key] for n, kind in enumerate(KINDS)}
    for kind in KINDS:
        response = api.client.delete(
            f"{kind.url}/{made[kind.name]}", headers=world[kind.part].changing
        )
        assert (response.status_code, response.json()["code"]) == (404, "NOT_FOUND")
        assert find(api, world, kind, made[kind.name])["is_active"] is True
    rate = f"{CATEGORIES}/{made['cost_category']}/hourly-rates/2026"
    assert api.client.delete(rate, headers=world["cost_settings"].changing).status_code == 404
