# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the organisation (US-0840, WF-REF-0070, 0080), through the service.

The nodes are created, read, changed, moved and deactivated by the API, every answer checked
against the contract (``ContractClient``). The depth of a node is resolved at the reading, never
stored; the pure arrangement of the tree is tried without a database. The witness is loaded by the
command and compared with the example the contract gives (``org_nodes_with_inactive.json``).
"""

import json
import threading
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import func, insert, select
from support import WITNESS, ContractClient

from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import (
    NodeWrite,
    create_node,
    update_node,
    within_node,
)
from waterfall.core.resource_settings.interface.org_nodes import TREE_LOCK
from waterfall.core.resource_settings.org_tree import (
    Branch,
    in_tree_order,
    is_within,
    levels_of,
    with_ancestors,
)
from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole
from waterfall.platform.audit import Act
from waterfall.platform.errors import ConflictError, ServiceError, UnprocessableError
from waterfall.platform.settings import WitnessSettings
from waterfall.witness.main import load_witness

if TYPE_CHECKING:
    from support import PartSessions, ReferenceSessions

    from waterfall.platform.database import Database

NODES = "/api/v1/reference/org-nodes"
WRITE = "resource_settings.write"
DAY = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
# The same node under three names the tests give to a node that does not exist.
UNKNOWN = "0192a1b2-0000-7000-8000-0000000000ff"


@pytest.fixture
def sessions(reference_sessions: ReferenceSessions) -> PartSessions:
    """Give the three sessions of the resource settings: without, reading, and changing."""
    return reference_sessions("resource_settings")


def make(
    api: ContractClient, headers: dict[str, str], code: str, label: str, parent: str | None = None
) -> dict[str, Any]:
    """Create a node by the API and give it as the service answers."""
    sent: dict[str, object] = {"code": code, "label": label}
    if parent is not None:
        sent["parent_id"] = parent
    response = api.post(NODES, headers=headers, json=sent)
    assert response.status_code == 201, response.text
    return response.json()


def tree(api: ContractClient, headers: dict[str, str], query: str = "") -> list[dict[str, Any]]:
    """Read the tree as the service answers, with the query given."""
    response = api.get(f"{NODES}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def codes(nodes: list[dict[str, Any]]) -> list[str]:
    """Give the codes of the nodes, in the order they are read."""
    return [node["code"] for node in nodes]


def refusal(response: Any) -> tuple[int, str, list[tuple[str, str]]]:
    """Give the status, the code and the fields (pointer, code) of a refusal."""
    body = response.json()
    return (
        response.status_code,
        body["code"],
        [(each["pointer"], each["code"]) for each in body.get("fields", [])],
    )


def move(
    api: ContractClient, headers: dict[str, str], node: dict[str, Any], parent: str | None
) -> Any:
    """Move a node under a parent, or to the root, at the version read, with its code and label."""
    sent = {
        "code": node["code"],
        "label": node["label"],
        "parent_id": parent,
        "lock_version": node["lock_version"],
    }
    return api.patch(f"{NODES}/{node['org_node_id']}", headers=headers, json=sent)


def organisation(api: ContractClient, headers: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Create the organisation the tests share, by the API, and give its nodes by code.

    The technical direction holds two offices and the purchases; the electrical office holds the
    wiring workshop.
    """
    direction = make(api, headers, "DT", "Direction technique")
    root = direction["org_node_id"]
    nodes = {"DT": direction}
    nodes["BE-ELEC"] = make(api, headers, "BE-ELEC", "Bureau d'études électricité", root)
    nodes["BE-AUTO"] = make(api, headers, "BE-AUTO", "Bureau d'études automatismes", root)
    nodes["ACHATS"] = make(api, headers, "ACHATS", "Service des achats", root)
    nodes["AT-CABL"] = make(
        api, headers, "AT-CABL", "Atelier de câblage", nodes["BE-ELEC"]["org_node_id"]
    )
    return nodes


def deactivate(
    api: ContractClient, headers: dict[str, str], node: dict[str, Any], *, is_active: bool = False
) -> Any:
    """Deactivate (or reactivate) a node at the version the service reads it at."""
    version = node["lock_version"]
    sent = {"is_active": is_active, "lock_version": version}
    return api.put(f"{NODES}/{node['org_node_id']}/activation", headers=headers, json=sent)


# The arrangement of the tree, without a database.


def branch(label: str, parent: Branch | None = None) -> Branch:
    """Give a branch of a tree with a new identifier, under another or at the root."""
    return Branch(uuid4(), None if parent is None else parent.node_id, label)


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_depth_of_a_node_is_resolved_from_its_parents_one_for_a_root() -> None:
    # « Un arbre de six niveaux peut être créé. » : the depth is computed, from 1 for a root.
    chain = [branch("n1")]
    for depth in range(2, 7):
        chain.append(branch(f"n{depth}", chain[-1]))
    levels = levels_of(reversed(chain))
    assert [levels[each.node_id] for each in chain] == [1, 2, 3, 4, 5, 6]


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_siblings_come_by_label_in_the_order_of_the_code_points_each_before_its_children() -> (
    None
):
    # Capitals before lowercase, an accent after the letters: not the order of a language.
    root = branch("Racine")
    zebra, accent, lower, upper = (
        branch(label, root) for label in ("Zèbre", "Édith", "abc", "Zed")
    )
    under_zed = branch("Fils", upper)
    other_root = branch("Autre")
    ordered = in_tree_order([under_zed, lower, root, accent, upper, zebra, other_root])
    assert [each.label for each in ordered] == [
        "Autre",
        "Racine",
        "Zed",
        "Fils",
        "Zèbre",
        "abc",
        "Édith",
    ]


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_node_is_within_itself_and_its_descendants_and_nowhere_else() -> None:
    root = branch("a")
    child = branch("b", root)
    grandchild = branch("c", child)
    sibling = branch("d", root)
    parents = {each.node_id: each.parent_id for each in (root, child, grandchild, sibling)}
    assert is_within(parents, grandchild.node_id, root.node_id)
    assert is_within(parents, child.node_id, child.node_id)
    assert not is_within(parents, sibling.node_id, child.node_id)
    assert not is_within(parents, root.node_id, child.node_id)


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_ancestors_of_the_nodes_kept_are_kept_with_them() -> None:
    root = branch("a")
    child = branch("b", root)
    grandchild = branch("c", child)
    sibling = branch("d", root)
    every = [root, child, grandchild, sibling]
    assert with_ancestors(every, [grandchild.node_id]) == {
        root.node_id,
        child.node_id,
        grandchild.node_id,
    }
    assert with_ancestors(every, []) == set()


# The tree through the API.


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_tree_of_six_levels_is_created_and_read_in_depth_each_level_resolved(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « Un arbre de six niveaux peut être créé. » : level goes from 1 to 6, resolved at the
    # reading, and the tree is read whole, depth first.
    parent = None
    created: list[dict[str, Any]] = []
    for depth in range(1, 7):
        node = make(api, sessions.changing, f"N{depth}", f"Niveau {depth}", parent)
        assert node["level"] == depth
        created.append(node)
        parent = node["org_node_id"]
    nodes = tree(api, sessions.changing)
    assert [(each["code"], each["level"]) for each in nodes] == [
        (f"N{depth}", depth) for depth in range(1, 7)
    ]
    assert nodes[3]["parent_id"] == created[2]["org_node_id"]
    assert nodes[3]["parent_label"] == "Niveau 3"
    assert nodes[0]["parent_id"] is None
    assert nodes[0]["parent_label"] is None


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_level_is_never_stored() -> None:
    # The depth is resolved at the reading: the table has no column for it.
    assert "level" not in OrgNode.__table__.columns


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_children_of_a_parent_come_by_label_in_the_order_of_the_code_points(
    api: ContractClient, sessions: PartSessions
) -> None:
    # Roots and children alike, with no page and no sort: « abc » before « Zed » would be
    # a language's order; the code points put the capitals first, then the lowercase, then the
    # accents.
    root = make(api, sessions.changing, "R", "Racine")["org_node_id"]
    for code, label in (("e", "Édith"), ("a", "abc"), ("z", "Zèbre"), ("d", "Zed")):
        make(api, sessions.changing, code, label, root)
    make(api, sessions.changing, "A", "Autre racine")
    nodes = tree(api, sessions.changing)
    assert [each["label"] for each in nodes] == [
        "Autre racine",
        "Racine",
        "Zed",
        "Zèbre",
        "abc",
        "Édith",
    ]


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_code_already_borne_by_a_node_active_or_not_is_refused_naming_the_node(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « La création d'un nœud dont le code existe déjà est refusée. » : 409, on /code, among the
    # active and the deactivated nodes, naming the node that bears it.
    nodes = organisation(api, sessions.changing)
    assert deactivate(api, sessions.changing, nodes["ACHATS"]).status_code == 200
    for code, bearer in (("BE-AUTO", nodes["BE-AUTO"]), ("ACHATS", nodes["ACHATS"])):
        refused = api.post(
            NODES, headers=sessions.changing, json={"code": code, "label": "Un autre"}
        )
        assert refusal(refused) == (409, "ALREADY_EXISTS", [("/code", "ALREADY_EXISTS")])
        assert refused.json()["fields"][0]["params"] == {
            "conflicting_object_id": bearer["org_node_id"],
            "conflicting_object_label": bearer["label"],
        }
    assert len(tree(api, sessions.changing, "?include_inactive=true")) == 5


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_code_given_to_a_node_by_a_change_is_refused_when_another_bears_it(
    api: ContractClient, sessions: PartSessions
) -> None:
    nodes = organisation(api, sessions.changing)
    taken = {**nodes["ACHATS"], "code": "BE-AUTO"}
    refused = api.patch(
        f"{NODES}/{taken['org_node_id']}",
        headers=sessions.changing,
        json={
            "code": "BE-AUTO",
            "label": taken["label"],
            "parent_id": taken["parent_id"],
            "lock_version": taken["lock_version"],
        },
    )
    assert refusal(refused) == (409, "ALREADY_EXISTS", [("/code", "ALREADY_EXISTS")])
    assert (
        refused.json()["fields"][0]["params"]["conflicting_object_id"]
        == (nodes["BE-AUTO"]["org_node_id"])
    )
    # Its own code, sent again, is no collision.
    again = move(api, sessions.changing, nodes["ACHATS"], nodes["DT"]["org_node_id"])
    assert again.status_code == 200


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_node_moved_under_another_carries_its_descendants_and_their_level_follows(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « Le déplacement d'un nœud sous un autre emporte ses descendants » : the electrical office,
    # and the workshop with it, move under the purchases.
    nodes = organisation(api, sessions.changing)
    moved = move(api, sessions.changing, nodes["BE-ELEC"], nodes["ACHATS"]["org_node_id"])
    assert moved.status_code == 200, moved.text
    assert (moved.json()["level"], moved.json()["parent_label"]) == (3, "Service des achats")
    assert moved.json()["lock_version"] == nodes["BE-ELEC"]["lock_version"] + 1
    read = tree(api, sessions.changing)
    assert [(each["code"], each["level"]) for each in read] == [
        ("DT", 1),
        ("BE-AUTO", 2),
        ("ACHATS", 2),
        ("BE-ELEC", 3),
        ("AT-CABL", 4),
    ]
    # The workshop, untouched, hangs under the office all the same.
    assert read[4]["parent_id"] == nodes["BE-ELEC"]["org_node_id"]
    assert read[4]["lock_version"] == nodes["AT-CABL"]["lock_version"]


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_node_moved_to_the_root_is_a_root_and_a_parent_is_asked_of_every_change(
    api: ContractClient, sessions: PartSessions
) -> None:
    nodes = organisation(api, sessions.changing)
    at_the_root = move(api, sessions.changing, nodes["BE-ELEC"], None)
    assert at_the_root.status_code == 200
    assert (at_the_root.json()["level"], at_the_root.json()["parent_id"]) == (1, None)
    # Absent, the parent is not read as the root nor as the parent held: it is lacking.
    lacking = api.patch(
        f"{NODES}/{nodes['ACHATS']['org_node_id']}",
        headers=sessions.changing,
        json={"code": "ACHATS", "label": "Achats", "lock_version": 0},
    )
    assert refusal(lacking) == (422, "VALIDATION_FAILED", [("/parent_id", "VALUE_REQUIRED")])


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_node_moved_under_itself_or_under_a_descendant_is_refused_for_a_loop(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « un nœud ne se déplace ni sous lui-même ni sous un descendant » : 422, ORG_NODE_CYCLE.
    nodes = organisation(api, sessions.changing)
    for under in ("DT", "BE-ELEC", "AT-CABL"):
        refused = move(api, sessions.changing, nodes["DT"], nodes[under]["org_node_id"])
        assert refusal(refused) == (422, "VALIDATION_FAILED", [("/parent_id", "ORG_NODE_CYCLE")])
    own = move(api, sessions.changing, nodes["BE-ELEC"], nodes["BE-ELEC"]["org_node_id"])
    assert refusal(own) == (422, "VALIDATION_FAILED", [("/parent_id", "ORG_NODE_CYCLE")])
    assert [(each["code"], each["level"]) for each in tree(api, sessions.changing)][:2] == [
        ("DT", 1),
        ("BE-AUTO", 2),
    ]


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_node_moved_under_a_deactivated_node_is_refused_but_a_node_kept_under_one_is_changed(
    api: ContractClient, sessions: PartSessions
) -> None:
    # « Le déplacement sous un nœud désactivé est refusé. » : 422, INACTIVE_REFERENCE_OBJECT on
    # /parent_id, judged on the parent sent when it changes: a node that keeps its deactivated
    # parent is renamed.
    nodes = organisation(api, sessions.changing)
    off = deactivate(api, sessions.changing, nodes["BE-AUTO"])
    assert off.status_code == 200, off.text
    refused = move(api, sessions.changing, nodes["AT-CABL"], nodes["BE-AUTO"]["org_node_id"])
    assert refusal(refused) == (
        422,
        "VALIDATION_FAILED",
        [("/parent_id", "INACTIVE_REFERENCE_OBJECT")],
    )
    created = api.post(
        NODES,
        headers=sessions.changing,
        json={"code": "NEW", "label": "Nouveau", "parent_id": nodes["BE-AUTO"]["org_node_id"]},
    )
    assert refusal(created) == (
        422,
        "VALIDATION_FAILED",
        [("/parent_id", "INACTIVE_REFERENCE_OBJECT")],
    )
    # The deactivated office, renamed under its parent (active), then its parent changed to none.
    kept = off.json()["org_nodes"][0]
    renamed = api.patch(
        f"{NODES}/{kept['org_node_id']}",
        headers=sessions.changing,
        json={
            "code": kept["code"],
            "label": "Automatismes",
            "parent_id": kept["parent_id"],
            "lock_version": kept["lock_version"],
        },
    )
    assert renamed.status_code == 200
    assert (renamed.json()["label"], renamed.json()["is_active"]) == ("Automatismes", False)


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_deactivated_node_that_keeps_its_deactivated_parent_is_renamed(
    api: ContractClient, sessions: PartSessions
) -> None:
    nodes = organisation(api, sessions.changing)
    child = deactivate(api, sessions.changing, nodes["AT-CABL"]).json()["org_nodes"][0]
    parent = deactivate(api, sessions.changing, nodes["BE-ELEC"]).json()["org_nodes"][0]
    assert parent["is_active"] is False
    renamed = api.patch(
        f"{NODES}/{child['org_node_id']}",
        headers=sessions.changing,
        json={
            "code": child["code"],
            "label": "Atelier",
            "parent_id": child["parent_id"],
            "lock_version": child["lock_version"],
        },
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["label"] == "Atelier"


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_parent_unknown_is_refused_before_a_loop_and_a_loop_before_a_deactivated_node(
    api: ContractClient, sessions: PartSessions
) -> None:
    # One reason only, in this order: unknown, then a loop, then deactivated.
    nodes = organisation(api, sessions.changing)
    unknown = move(api, sessions.changing, nodes["BE-ELEC"], UNKNOWN)
    assert refusal(unknown) == (422, "VALIDATION_FAILED", [("/parent_id", "UNKNOWN_ORG_NODE")])
    created = api.post(
        NODES, headers=sessions.changing, json={"code": "X", "label": "X", "parent_id": UNKNOWN}
    )
    assert refusal(created) == (422, "VALIDATION_FAILED", [("/parent_id", "UNKNOWN_ORG_NODE")])
    # The workshop is deactivated, and the office, its ancestor, is moved under it: a loop first.
    workshop = deactivate(api, sessions.changing, nodes["AT-CABL"]).json()["org_nodes"][0]
    looped = move(api, sessions.changing, nodes["BE-ELEC"], workshop["org_node_id"])
    assert refusal(looped) == (422, "VALIDATION_FAILED", [("/parent_id", "ORG_NODE_CYCLE")])


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_code_or_a_label_empty_or_too_long_is_refused_on_its_field(
    api: ContractClient, sessions: PartSessions
) -> None:
    empty = api.post(NODES, headers=sessions.changing, json={"code": "", "label": " "})
    assert refusal(empty) == (
        422,
        "VALIDATION_FAILED",
        [("/code", "VALUE_REQUIRED"), ("/label", "VALIDATION_FAILED")],
    )
    long = api.post(NODES, headers=sessions.changing, json={"code": "C" * 21, "label": "L" * 201})
    assert refusal(long) == (
        422,
        "VALIDATION_FAILED",
        [("/code", "VALUE_TOO_LONG"), ("/label", "VALUE_TOO_LONG")],
    )


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_change_at_another_version_is_refused_and_an_unknown_node_is_not_found(
    api: ContractClient, sessions: PartSessions
) -> None:
    nodes = organisation(api, sessions.changing)
    stale = move(api, sessions.changing, {**nodes["ACHATS"], "lock_version": 9}, None)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", [])
    assert stale.json()["params"] == {"expected_lock_version": 0}
    absent = move(api, sessions.changing, {**nodes["ACHATS"], "org_node_id": UNKNOWN}, None)
    assert absent.status_code == 404
    assert tree(api, sessions.changing)[2]["parent_id"] == nodes["DT"]["org_node_id"]


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_search_finds_a_node_by_its_label_or_its_code_and_brings_its_ancestors(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The search holds on the label and on the code, without regard to case or accents; the nodes
    # kept come with their ancestors, which need not satisfy it.
    organisation(api, sessions.changing)
    by_label = tree(api, sessions.changing, "?search=cablage")
    assert codes(by_label) == ["DT", "BE-ELEC", "AT-CABL"]
    by_code = tree(api, sessions.changing, "?search=be-auto")
    assert codes(by_code) == ["DT", "BE-AUTO"]
    by_accent = tree(api, sessions.changing, "?search=ELECTRICITE")
    assert codes(by_accent) == ["DT", "BE-ELEC"]
    assert tree(api, sessions.changing, "?search=introuvable") == []


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_filters_of_the_columns_keep_the_nodes_and_their_ancestors(
    api: ContractClient, sessions: PartSessions
) -> None:
    organisation(api, sessions.changing)
    assert codes(tree(api, sessions.changing, "?code=be-")) == ["DT", "BE-AUTO", "BE-ELEC"]
    assert codes(tree(api, sessions.changing, "?level=1")) == ["DT"]
    assert codes(tree(api, sessions.changing, "?level=3")) == ["DT", "BE-ELEC", "AT-CABL"]
    assert codes(tree(api, sessions.changing, "?level_min=3")) == ["DT", "BE-ELEC", "AT-CABL"]
    assert codes(tree(api, sessions.changing, "?level_max=2")) == [
        "DT",
        "BE-AUTO",
        "BE-ELEC",
        "ACHATS",
    ]
    assert codes(tree(api, sessions.changing, "?level_min=2&level_max=2&search=achats")) == [
        "DT",
        "ACHATS",
    ]
    assert codes(tree(api, sessions.changing, "?level=2&level_min=3")) == []


@pytest.mark.requirement("WF-REF-0070-A")
def test_a_bound_of_the_level_malformed_or_inverted_is_refused_on_its_parameter(
    api: ContractClient, sessions: PartSessions
) -> None:
    inverted = api.get(f"{NODES}?level_min=3&level_max=2", headers=sessions.changing)
    assert refusal(inverted) == (
        422,
        "VALIDATION_FAILED",
        [("/query/level_max", "VALUE_OUT_OF_RANGE")],
    )
    assert inverted.json()["fields"][0]["params"] == {"minimum": 3}
    malformed = api.get(f"{NODES}?level_min=abc", headers=sessions.changing)
    assert refusal(malformed) == (
        422,
        "VALIDATION_FAILED",
        [("/query/level_min", "NUMBER_INVALID")],
    )


@pytest.mark.requirement("WF-REF-0150-A")
def test_the_deactivated_nodes_are_read_with_include_inactive_or_by_is_active(
    api: ContractClient, sessions: PartSessions
) -> None:
    nodes = organisation(api, sessions.changing)
    deactivate(api, sessions.changing, nodes["AT-CABL"])
    assert "AT-CABL" not in codes(tree(api, sessions.changing))
    assert "AT-CABL" in codes(tree(api, sessions.changing, "?include_inactive=true"))
    # ``is_active`` prevails: the deactivated alone, brought with their ancestors; and the active
    # alone, though the deactivated are asked for.
    assert codes(tree(api, sessions.changing, "?is_active=false")) == ["DT", "BE-ELEC", "AT-CABL"]
    assert "AT-CABL" not in codes(
        tree(api, sessions.changing, "?is_active=true&include_inactive=true")
    )


@pytest.mark.requirement("WF-REF-0150-A")
def test_the_deactivated_nodes_ask_for_the_permission_to_change_the_settings_not_to_read_them(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The decision of the author (#2084): the frozen contract holds. Reading the deactivated nodes
    # asks for ``resource_settings.write``, and reading the part is not enough.
    nodes = organisation(api, sessions.changing)
    deactivate(api, sessions.changing, nodes["AT-CABL"])
    for who in (sessions.without, sessions.reading):
        for query in ("?include_inactive=true", "?is_active=false"):
            refused = api.get(f"{NODES}{query}", headers=who)
            assert refusal(refused) == (403, "PERMISSION_MISSING", [])
            assert refused.json()["params"] == {"missing_permission": WRITE}
    assert "AT-CABL" in codes(tree(api, sessions.changing, "?include_inactive=true"))


@pytest.mark.requirement("WF-REF-0150-A")
def test_the_active_nodes_are_read_by_any_open_session_and_carry_no_command_for_it(
    api: ContractClient, sessions: PartSessions
) -> None:
    organisation(api, sessions.changing)
    for who in (sessions.without, sessions.reading):
        read = tree(api, who)
        assert len(read) == 5
        assert all(each["available_commands"] == [] for each in read)
    mine = tree(api, sessions.changing)
    assert all(
        each["available_commands"]
        == [{"command": "deactivate", "is_available": True, "missing_conditions": []}]
        for each in mine
    )
    assert api.get(NODES).status_code == 401


@pytest.mark.requirement("WF-ADM-0100-A")
def test_every_write_of_the_tree_asks_for_the_permission_to_change_the_settings(
    api: ContractClient, sessions: PartSessions
) -> None:
    nodes = organisation(api, sessions.changing)
    node = nodes["ACHATS"]
    sent = {"code": "X", "label": "X", "parent_id": None, "lock_version": 0}
    for who in (sessions.without, sessions.reading):
        responses = [
            api.post(NODES, headers=who, json={"code": "X", "label": "X"}),
            api.patch(f"{NODES}/{node['org_node_id']}", headers=who, json=sent),
            api.put(
                f"{NODES}/{node['org_node_id']}/activation",
                headers=who,
                json={"is_active": False, "lock_version": 0},
            ),
        ]
        for refused in responses:
            assert refusal(refused) == (403, "PERMISSION_MISSING", [])
            assert refused.json()["params"] == {"missing_permission": WRITE}
    assert len(tree(api, sessions.changing)) == 5


@pytest.mark.requirement("WF-REF-0080-A")
def test_the_deactivation_reaches_the_descendants_and_the_reactivation_the_node_alone(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The cascade over the roles is tried with them (``test_resource_settings_roles.py``).
    nodes = organisation(api, sessions.changing)
    off = deactivate(api, sessions.changing, nodes["BE-ELEC"])
    assert off.status_code == 200, off.text
    assert [(each["code"], each["is_active"]) for each in off.json()["org_nodes"]] == [
        ("BE-ELEC", False),
        ("AT-CABL", False),
    ]
    assert off.json()["resource_roles"] == []
    parent, workshop = off.json()["org_nodes"]
    assert parent["available_commands"] == [
        {"command": "reactivate", "is_available": True, "missing_conditions": []}
    ]
    # The workshop, deactivated with its parent, cannot come back before its parent does.
    refused = deactivate(api, sessions.changing, workshop, is_active=True)
    assert refusal(refused) == (409, "STATE_FORBIDS_OPERATION", [])
    assert refused.json()["params"] == {
        "missing_condition": "org_node_parent_active",
        "conflicting_object_id": nodes["BE-ELEC"]["org_node_id"],
    }
    listed = tree(api, sessions.changing, "?include_inactive=true")
    assert {
        each["code"]: (
            each["available_commands"][0]["command"],
            each["available_commands"][0]["missing_conditions"],
        )
        for each in listed
    } == {
        "DT": ("deactivate", []),
        "BE-AUTO": ("deactivate", []),
        "ACHATS": ("deactivate", []),
        "BE-ELEC": ("reactivate", []),
        "AT-CABL": ("reactivate", ["org_node_parent_active"]),
    }
    # The reactivation makes the node alone active: the workshop stays deactivated.
    back = deactivate(api, sessions.changing, parent, is_active=True)
    assert back.status_code == 200
    assert [(each["code"], each["is_active"]) for each in back.json()["org_nodes"]] == [
        ("BE-ELEC", True)
    ]
    assert back.json()["resource_roles"] == []
    assert "AT-CABL" not in codes(tree(api, sessions.changing))


@pytest.mark.requirement("WF-REF-0080-A")
def test_an_activation_at_another_version_or_of_an_unknown_node_is_refused_none_is_a_no_change(
    api: ContractClient, sessions: PartSessions
) -> None:
    node = organisation(api, sessions.changing)["ACHATS"]
    stale = api.put(
        f"{NODES}/{node['org_node_id']}/activation",
        headers=sessions.changing,
        json={"is_active": False, "lock_version": 4},
    )
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", [])
    absent = api.put(
        f"{NODES}/{UNKNOWN}/activation",
        headers=sessions.changing,
        json={"is_active": False, "lock_version": 0},
    )
    assert absent.status_code == 404
    unchanged = deactivate(api, sessions.changing, node, is_active=True)
    assert (unchanged.status_code, unchanged.json()) == (
        200,
        {"org_nodes": [], "resource_roles": []},
    )


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_authors_of_a_node_are_named_as_the_contract_names_them(
    api: ContractClient, sessions: PartSessions
) -> None:
    node = make(api, sessions.changing, "DT", "Direction technique")
    audit = node["audit"]
    assert audit["created_by"]["kind"] == "user"
    assert audit["updated_by"] == audit["created_by"]


# The roles a node carries, as far as the base lets this story tell: a role names its node.


def write_role(database: Database, node: UUID) -> UUID:
    """Write, around the service, a role of resources under a node, and give its identifier."""
    nature, category, calendar, role = (uuid4() for _ in range(4))
    audit = {"created_at": DAY, "updated_at": DAY}
    week = {day: Decimal(8) for day in ("monday", "tuesday", "wednesday", "thursday", "friday")}
    weekend = {"saturday": Decimal(0), "sunday": Decimal(0)}
    with database.transaction() as session:
        session.execute(
            insert(CostType).values(
                id=nature, code="MO", label="Main d'œuvre", kind="labor", is_active=True, **audit
            )
        )
        session.execute(
            insert(CostCategory).values(
                id=category,
                code="ING",
                label="Ingénierie",
                accounting_code="641",
                cost_type_id=nature,
                is_active=True,
                **audit,
            )
        )
        session.execute(
            insert(Calendar).values(
                id=calendar,
                label="Semaine",
                is_default=False,
                is_active=True,
                **week,
                **weekend,
                **audit,
            )
        )
        session.execute(
            insert(ResourceRole).values(
                id=role,
                code="MONT",
                label="Monteur",
                org_node_id=node,
                cost_category_id=category,
                calendar_id=calendar,
                monthly_hours=Decimal(140),
                headcount=Decimal(2),
                is_active=True,
                **audit,
            )
        )
    return role


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_subtree_of_the_arrival_holds_what_the_moved_node_holds_by_its_identifier(
    api: ContractClient, sessions: PartSessions, database: Database
) -> None:
    # The subtree query (``within_node``), tried on a role table written by hand: a role names its
    # node by its identifier and a move does not write it, so the arrival now holds it through
    # its descendants. This does not close « emporte … ses rôles »: asking the API for the roles
    # of a node (``listResourceRoles?org_node_id=``) is the story of the roles (US-0850), which
    # carries that assertion.
    nodes = organisation(api, sessions.changing)
    role = write_role(database, UUID(nodes["AT-CABL"]["org_node_id"]))
    arrival = UUID(nodes["BE-AUTO"]["org_node_id"])

    def held_by(node: UUID) -> list[UUID]:
        with database.transaction() as session:
            return list(
                session.scalars(
                    select(ResourceRole.id).where(within_node(node, ResourceRole.org_node_id))
                )
            )

    assert held_by(arrival) == []
    assert move(api, sessions.changing, nodes["BE-ELEC"], str(arrival)).status_code == 200
    assert held_by(arrival) == [role]
    with database.transaction() as session:
        assert session.scalars(select(ResourceRole.org_node_id)).one() == UUID(
            nodes["AT-CABL"]["org_node_id"]
        )
        assert session.scalars(select(ResourceRole.lock_version)).one() == 0


# The lock of the tree.


def hold_the_lock(database: Database) -> tuple[Any, Any]:
    """Take the lock of the tree in a transaction of its own; give the connection and the lock."""
    connection = database.engine.connect()
    transaction = connection.begin()
    connection.execute(select(func.pg_advisory_xact_lock(TREE_LOCK)))
    return connection, transaction


def run(job: Any, results: list[Any]) -> threading.Thread:
    """Start a thread that runs a job and keeps its result or the refusal it was given."""

    def work() -> None:
        try:
            results.append(job())
        except ServiceError as refused:
            results.append(refused)

    thread = threading.Thread(target=work)
    thread.start()
    return thread


@pytest.mark.requirement("WF-REF-0070-A")
def test_two_creations_of_one_code_at_once_write_one_node_and_refuse_the_other(
    database: Database,
) -> None:
    # Every write of the tree runs under its lock: while it is held, the creations wait, then one
    # is written and the other finds the code taken.
    act = Act(None, DAY)

    def create() -> str:
        with database.transaction() as session:
            return create_node(session, NodeWrite("DT", "Direction technique"), act).code

    results: list[Any] = []
    connection, transaction = hold_the_lock(database)
    threads = [run(create, results), run(create, results)]
    for thread in threads:
        thread.join(timeout=1)
    assert all(thread.is_alive() for thread in threads)
    transaction.commit()
    connection.close()
    for thread in threads:
        thread.join(timeout=10)
    refusals = [each for each in results if isinstance(each, ConflictError)]
    assert (len(results), len(refusals)) == (2, 1)
    assert "DT" in results
    assert refusals[0].fields[0].pointer == "/code"


@pytest.mark.requirement("WF-REF-0070-A")
def test_two_moves_that_would_make_a_loop_together_write_one_and_refuse_the_other(
    database: Database,
) -> None:
    # A under B and B under A, at once: each is a move allowed on the tree the other has not yet
    # written. Under the lock one runs after the other and finds the loop.
    act = Act(None, DAY)
    with database.transaction() as session:
        first = create_node(session, NodeWrite("A", "A"), act)
        second = create_node(session, NodeWrite("B", "B"), act)

    def put_under(node: Any, parent: Any) -> str:
        with database.transaction() as session:
            write = NodeWrite(node.code, node.label, parent.node_id)
            return update_node(session, node.node_id, write, node.lock_version, act).code

    results: list[Any] = []
    connection, transaction = hold_the_lock(database)
    threads = [
        run(lambda: put_under(first, second), results),
        run(lambda: put_under(second, first), results),
    ]
    for thread in threads:
        thread.join(timeout=1)
    assert all(thread.is_alive() for thread in threads)
    transaction.commit()
    connection.close()
    for thread in threads:
        thread.join(timeout=10)
    refusals = [each for each in results if isinstance(each, UnprocessableError)]
    assert (len(results), len(refusals)) == (2, 1)
    assert refusals[0].fields[0].code == "ORG_NODE_CYCLE"


# The witness.


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.usefixtures("witness")
def test_the_witness_loads_the_nodes_of_the_example_then_deactivates_those_it_says_deactivated(
    api: ContractClient, sessions: PartSessions
) -> None:
    # The list the service reads is the example the contract gives, to the audit columns and the
    # counter of writes near: the calculated becomes the expected.
    expected = json.loads((WITNESS / "org_nodes_with_inactive.json").read_text("utf-8"))["value"]
    read = tree(api, sessions.changing, "?include_inactive=true")

    def shape(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in node.items() if key not in {"audit", "lock_version"}}
            for node in nodes
        ]

    assert shape(read) == shape(expected)
    assert [each["code"] for each in tree(api, sessions.changing)] == [
        "DT",
        "BE-ELEC",
        "AT-CABL",
        "ACHATS",
    ]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loaded_twice_writes_its_nodes_once(
    service_database_url: str, witness: Database
) -> None:
    settings = WitnessSettings(
        database_url=SecretStr(service_database_url), witness_path=str(WITNESS)
    )
    assert load_witness(settings) == 0
    with witness.transaction() as session:
        assert session.scalar(select(func.count()).select_from(OrgNode)) == 6
