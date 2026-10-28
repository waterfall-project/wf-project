# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the readings of the lists of the projects, of a project and of the administration.

The list of the projects, the subprojects and the contributors (#536), the accounts, the access
roles and the work breakdown (#560). They try the rules of sort, search and filter the fake back
applies on rows made for them,
and the examples against the lists written by hand and the contract they illustrate — not the
Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from dataclasses import replace
from datetime import UTC, date, datetime, time
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest

from wftools import REPOSITORY, mockdata, mocklists, mocktext, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Row = dict[str, Any]


@pytest.fixture(scope="module")
def lists() -> dict[str, Any]:
    """Read the examples of the lists back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mocklists.examples().items()
    }


def _enumeration(schema: str, name: str) -> list[str]:
    """Return the values of an enumeration of the contract, in its order."""
    text = (REPOSITORY / "docs/api/components/schemas" / schema).read_text(encoding="utf-8")
    found = re.search(rf"^{name}:\n(?:[ \t].*\n)*?\s+enum: \[([^\]]*)\]", text, re.MULTILINE)
    assert found is not None
    return [value.strip() for value in found.group(1).split(",")]


def _project(identifier: str, label: str, code: str | None, state: str, updated: str) -> Row:
    return {
        "project_id": identifier,
        "label": label,
        "code": code,
        "state": state,
        "audit": {"updated_at": updated},
    }


PROJECTS: list[Row] = [
    _project("p1", "Ligne de presse", "PRJ-010", "in_progress", "2026-03-31T21:59:59Z"),
    _project("p2", "Banc d'essai", None, "pricing", "2026-02-28T23:00:00Z"),
    _project("p3", "Atelier", "LIGNE-7", "completed", "2026-02-28T12:00:00Z"),
    _project("p4", "Convoyeur", "PRJ-011", "in_progress", "2026-03-31T22:00:00Z"),
    _project("p5", "Pont roulant", "PRJ-012", "in_progress", "2026-02-28T23:30:00Z"),
]
"""Projects modified around March in Paris: from 2026-02-28T23:00Z to 2026-03-31T22:00Z."""

MARCH_IN_PARIS = (datetime(2026, 2, 28, 23, tzinfo=UTC), datetime(2026, 3, 31, 22, tzinfo=UTC))


def _ids(rows: list[Row], key: str = "project_id") -> list[str]:
    return [row[key] for row in rows]


def test_the_orders_follow_the_enumerations_of_the_contract() -> None:
    assert list(mocklists.PROJECT_STATES) == _enumeration("projects.yaml", "ProjectState")
    assert list(mocklists.CONTRIBUTOR_KINDS) == _enumeration("projects.yaml", "ContributorKind")
    assert list(mocklists.BREAKDOWN_KINDS) == _enumeration("projects.yaml", "WorkBreakdownKind")


def test_without_states_the_projects_in_progress_alone_and_the_answer_names_them() -> None:
    page: dict[str, Any] = mocklists.project_page(PROJECTS)
    # The last modified first, whatever the order they are given in.
    assert _ids(page["items"]) == ["p4", "p1", "p5"]
    assert page["meta"] == {"limit": 50, "offset": 0, "total": 3, "states": ["in_progress"]}


def test_a_page_counts_every_project_retained_not_those_it_shows() -> None:
    page: dict[str, Any] = mocklists.project_page(PROJECTS, limit=1)
    assert _ids(page["items"]) == ["p4"]
    assert page["meta"] == {"limit": 1, "offset": 0, "total": 3, "states": ["in_progress"]}


def test_the_states_retained_are_named_once_in_the_order_of_the_life_cycle() -> None:
    page: dict[str, Any] = mocklists.project_page(PROJECTS, ["completed", "pricing", "completed"])
    assert page["meta"]["states"] == ["pricing", "completed"]
    assert _ids(page["items"]) == ["p2", "p3"]


def test_a_state_the_life_cycle_has_not_is_refused() -> None:
    with pytest.raises(ValueError, match="no state of a project"):
        mocklists.retained_states(["archived"])


def test_the_projects_without_sort_come_the_last_modified_first_then_by_identifier() -> None:
    tied = [
        _project("p9", "Neuf", None, "pricing", "2026-02-28T23:00:00Z"),
        *PROJECTS,
        _project("p0", "Zéro", None, "pricing", "2026-03-01T00:00:00+01:00"),
    ]
    # p0, p2 and p9 were modified at one instant, p0 written in another offset: their
    # identifiers decide.
    assert _ids(mocklists.by_default(tied)) == ["p4", "p1", "p5", "p0", "p2", "p9", "p3"]


def test_every_example_of_the_list_of_the_projects_comes_in_the_order_without_sort() -> None:
    # Every answer of listProjects, written by hand or generated, read without sort_by
    # (`sort_by` absent: the last modified first, then the identifier).
    text = (REPOSITORY / "docs/api/paths/projects.yaml").read_text(encoding="utf-8")
    block = text.split("operationId: listProjects", 1)[1].split("'401'", 1)[0]
    names = re.findall(r"fixtures/api/(\w+)\.json", block)
    assert {"projects", "projects_empty", "projects_period"} <= set(names)
    for name in names:
        items = fixture(name)["items"]
        assert items == mocklists.by_default(items), name


def test_the_search_of_the_projects_reads_the_label_and_the_code() -> None:
    # « ligne » is in the label of p1 and the code of p3, whatever the case; p2 has no code.
    assert _ids(mocklists.searched_projects(PROJECTS, "ligne")) == ["p1", "p3"]
    assert _ids(mocklists.searched_projects(PROJECTS, "PRJ-011")) == ["p4"]
    assert mocklists.searched_projects(PROJECTS, "absent") == []


def test_the_period_retains_the_instants_of_last_modification_from_included_to_excluded() -> None:
    start, end = MARCH_IN_PARIS
    march = mocklists.modified_within(PROJECTS, start, end)
    # p2 at the very start is in, and p5 at 23:30Z on 28 February — 1 March in Paris —, which a
    # day in universal time would leave out; p4 at the very end is out, p1 a second before in.
    assert _ids(march) == ["p1", "p2", "p5"]
    assert _ids(mocklists.modified_within(PROJECTS, end, None)) == ["p4"]
    assert _ids(mocklists.modified_within(PROJECTS, None, start)) == ["p3"]
    assert mocklists.modified_within(PROJECTS, start, start) == []
    with pytest.raises(ValueError, match="before it starts"):
        mocklists.modified_within(PROJECTS, end, start)


ROWS: list[Row] = [
    {"id": "a", "label": "beta", "flag": False, "rank": 1},
    {"id": "b", "label": None, "flag": True, "rank": 0},
    {"id": "c", "label": "Alpha", "flag": True, "rank": 1},
    {"id": "d", "label": "beta", "flag": False, "rank": 0},
]


def test_a_text_sorts_by_code_point_ties_keep_their_order_and_none_comes_last() -> None:
    def label(row: Row) -> str | None:
        return row["label"]

    # « A » precedes « b » by code point; a and d, of one label, keep their order both ways.
    assert _ids(mocklists.ordered(ROWS, label), "id") == ["c", "a", "d", "b"]
    assert _ids(mocklists.ordered(ROWS, label, descending=True), "id") == ["b", "a", "d", "c"]


def test_the_subprojects_sort_by_their_code_and_their_actual_costs_both_ways() -> None:
    rows: list[Row] = [
        {"subproject_id": "s1", "code": "SP-B", "has_actual_costs": False},
        {"subproject_id": "s2", "code": "SP-C", "has_actual_costs": True},
        {"subproject_id": "s3", "code": "SP-A", "has_actual_costs": False},
        {"subproject_id": "s4", "code": "SP-D", "has_actual_costs": True},
    ]
    code, costs = mocklists.SUBPROJECT_KEYS["code"], mocklists.SUBPROJECT_KEYS["has_actual_costs"]
    assert _ids(mocklists.ordered(rows, code), "subproject_id") == ["s3", "s1", "s2", "s4"]
    assert _ids(mocklists.ordered(rows, code, descending=True), "subproject_id") == [
        "s4",
        "s2",
        "s1",
        "s3",
    ]
    # Those that bear actual costs first ascending; ties keep the order given, both ways.
    assert _ids(mocklists.ordered(rows, costs), "subproject_id") == ["s2", "s4", "s1", "s3"]
    assert _ids(mocklists.ordered(rows, costs, descending=True), "subproject_id") == [
        "s1",
        "s3",
        "s2",
        "s4",
    ]


def test_a_column_of_truth_values_ranges_the_true_rows_first_in_the_ascending_order() -> None:
    flag = mocklists.first_true("flag")
    assert _ids(mocklists.ordered(ROWS, flag), "id") == ["b", "c", "a", "d"]
    assert _ids(mocklists.ordered(ROWS, flag, descending=True), "id") == ["a", "d", "b", "c"]


def test_the_contributors_sort_by_kind_project_managers_first() -> None:
    people: list[Row] = [
        {"user_id": "u1", "display_name": "Zoé", "kind": "contributor", "is_active": True},
        {"user_id": "u2", "display_name": "Yann", "kind": "project_manager", "is_active": False},
        {"user_id": "u3", "display_name": "Xavier", "kind": "contributor", "is_active": False},
    ]
    kind, active = mocklists.CONTRIBUTOR_KEYS["kind"], mocklists.CONTRIBUTOR_KEYS["is_active"]
    assert _ids(mocklists.ordered(people, kind), "user_id") == ["u2", "u1", "u3"]
    assert _ids(mocklists.ordered(people, kind, descending=True), "user_id") == ["u1", "u3", "u2"]
    assert _ids(mocklists.ordered(people, active), "user_id") == ["u1", "u2", "u3"]


def test_the_projects_read_by_the_home_name_the_six_states() -> None:
    for name in ("projects", "projects_empty"):
        assert fixture(name)["meta"]["states"] == list(mocklists.PROJECT_STATES)


def test_the_readings_of_the_projects_follow_their_parameters(lists: dict[str, Any]) -> None:
    labels = {row["code"]: row["label"] for row in fixture("projects")["items"]}
    default = lists["projects_default_states"]
    assert [row["code"] for row in default["items"]] == ["PRJ-001"]
    assert default["meta"]["states"] == ["in_progress"]
    found = lists["projects_search_code"]["items"]
    # Found by its code, which its label does not hold.
    assert [row["code"] for row in found] == [mocklists.SEARCHED_CODE]
    assert mocklists.SEARCHED_CODE not in labels[mocklists.SEARCHED_CODE]
    period = lists["projects_period"]
    assert [row["code"] for row in period["items"]] == ["PRJ-002"]
    start, end = mocklists.PERIOD
    assert start <= mocklists.modified_at(period["items"][0]) < end
    assert period["meta"]["total"] == 1


def test_the_readings_of_the_subprojects_follow_their_parameters(lists: dict[str, Any]) -> None:
    written = fixture("subprojects")
    assert [row["code"] for row in written] == sorted(row["code"] for row in written)
    by_label = [row["label"] for row in lists["subprojects_by_label"]]
    assert by_label == ["Essais et mise en service", "Poste de commande"]
    assert [row["code"] for row in written] == ["SP-CMD", "SP-ESS"]
    # Both subprojects bear actual costs: the invoice of the screens, and those of the drawn tasks
    # of the lots « Ligne d'essais » completed (EP-14/L45a).
    charged = lists["subprojects_with_actual_costs"]
    assert [row["code"] for row in charged] == ["SP-CMD", "SP-ESS"]
    assert all(row["has_actual_costs"] is True for row in charged)


def test_the_readings_of_the_contributors_follow_their_parameters(lists: dict[str, Any]) -> None:
    written = fixture("contributors")
    by_name = lists["contributors_by_name"]
    assert [row["display_name"] for row in by_name["items"]] == [
        "Alix Moreau",
        "Camille Martin",
        "Inès Roux",
        "Lucas Petit",
    ]
    # The list without sort: the project manager first, then by family name.
    assert [row["display_name"] for row in written["items"]] == [
        "Camille Martin",
        "Alix Moreau",
        "Lucas Petit",
        "Inès Roux",
    ]
    assert [row["display_name"] for row in lists["contributors_search"]["items"]] == ["Lucas Petit"]
    assert [row["display_name"] for row in lists["contributors_inactive"]["items"]] == [
        "Alix Moreau"
    ]
    # Sorted, the reading is the whole list, with its counter; filtered, it has none (#560).
    assert lists["contributors_by_name"]["lock_version"] == written["lock_version"]
    for name in ("contributors_search", "contributors_inactive"):
        assert lists[name]["lock_version"] is None


_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
"""An instant as a summary writes it, as the contract carries it."""

PARIS = ZoneInfo("Europe/Paris")


def _local_midnight(day: date) -> datetime:
    """Return the instant the screen asks for the start of a day of its reader in Paris."""
    return datetime.combine(day, time(), PARIS).astimezone(UTC)


def test_the_instants_of_the_periods_are_those_the_screen_asks_for_its_days() -> None:
    # The screen asks a period of days by the start of its first day and the start of the day
    # after its last (`from` included, `to` excluded): the summaries say these instants.
    period: dict[str, Any] = mocklists.examples()["projects_period.json"]
    start, end = (datetime.fromisoformat(each) for each in _INSTANT.findall(period["summary"]))
    assert (start, end) == mocklists.PERIOD
    assert (start, end) == (_local_midnight(date(2026, 3, 1)), _local_midnight(date(2026, 4, 1)))
    path = REPOSITORY / "fixtures/api/projects_period_inverted.json"
    inverted = json.loads(path.read_text(encoding="utf-8"))
    begun, ended = (datetime.fromisoformat(each) for each in _INSTANT.findall(inverted["summary"]))
    # Asked from 1 April to 1 March: the end is the start of 2 March, before the start.
    assert begun == _local_midnight(date(2026, 4, 1))
    assert ended == _local_midnight(date(2026, 3, 2))
    assert ended < begun
    [field] = inverted["value"]["fields"]
    assert datetime.fromisoformat(field["params"]["minimum"]) == begun


# --- The accounts and the access roles (#560) ---------------------------------------------------


def _user(identifier: str, last: str, first: str, email: str, roles: list[str]) -> Row:
    return {
        "user_id": identifier,
        "last_name": last,
        "first_name": first,
        "email": email,
        "access_role_ids": roles,
    }


USERS: list[Row] = [
    _user("u1", "Durand", "Élise", "e.durand@example.com", ["r1"]),
    _user("u2", "Masson", "Léa", "lmasson@example.com", ["r2", "r3"]),
    _user("u3", "Noël", "Paul", "pn@example.com", []),
    _user("u4", "Paul", "Anne", "contact.ap@example.com", ["r3"]),
]
"""Accounts whose addresses hold neither their name nor their first name."""


def test_the_search_of_the_accounts_reads_the_name_the_first_name_the_address_and_the_display() -> (
    None
):
    # « paul » is the first name of u3 and the name of u4, whatever the case.
    assert _ids(mocklists.searched_users(USERS, "PAUL"), "user_id") == ["u3", "u4"]
    # The address: « lmasson » is in that of u2 alone.
    assert _ids(mocklists.searched_users(USERS, "lmasson"), "user_id") == ["u2"]
    # Compared by code point: « Élise » and « Noël » keep their accents.
    assert _ids(mocklists.searched_users(USERS, "élise"), "user_id") == ["u1"]
    assert _ids(mocklists.searched_users(USERS, "elise"), "user_id") == ["u1"]
    assert _ids(mocklists.searched_users(USERS, "NOEL"), "user_id") == ["u3"]
    # The displayed name, the first name then the name, which no column holds whole.
    assert _ids(mocklists.searched_users(USERS, "Léa Masson"), "user_id") == ["u2"]
    assert mocklists.searched_users(USERS, "Masson Léa") == []


def test_the_accounts_are_filtered_by_one_at_least_of_the_roles_named() -> None:
    assert _ids(mocklists.holding(USERS, ["r3"]), "user_id") == ["u2", "u4"]
    # Either role retains: u1 by r1, u2 by r2 — once, though it holds r3 too.
    assert _ids(mocklists.holding(USERS, ["r2", "r1"]), "user_id") == ["u1", "u2"]
    # An account without a role is retained by no value; a role nobody holds retains nobody.
    assert mocklists.holding(USERS, ["r9"]) == []


def test_a_page_of_the_accounts_counts_every_account_retained() -> None:
    page: dict[str, Any] = mocklists.user_page(USERS, limit=2)
    assert _ids(page["items"], "user_id") == ["u1", "u2"]
    assert page["meta"] == {"limit": 2, "offset": 0, "total": 4}


ROLES: list[Row] = [
    {"access_role_id": "a", "is_predefined": True, "holder_count": 0},
    {"access_role_id": "b", "is_predefined": False, "holder_count": 2},
    {"access_role_id": "c", "is_predefined": True, "holder_count": 1},
    {"access_role_id": "d", "is_predefined": False, "holder_count": 3},
]


def test_the_roles_are_filtered_by_their_nature() -> None:
    assert _ids(mocklists.of_nature(ROLES, predefined=True), "access_role_id") == ["a", "c"]
    assert _ids(mocklists.of_nature(ROLES, predefined=False), "access_role_id") == ["b", "d"]


def test_the_bounds_of_the_holders_are_both_included() -> None:
    def held(minimum: int | None, maximum: int | None) -> list[str]:
        return _ids(mocklists.held_within(ROLES, minimum, maximum), "access_role_id")

    assert held(1, 2) == ["b", "c"]
    assert held(None, 0) == ["a"]
    assert held(3, None) == ["d"]
    assert held(2, 2) == ["b"]
    assert held(None, None) == ["a", "b", "c", "d"]
    with pytest.raises(ValueError, match="below the lower bound"):
        mocklists.held_within(ROLES, 2, 1)


def test_the_readings_of_the_accounts_follow_their_parameters(lists: dict[str, Any]) -> None:
    written = fixture("users")["items"]
    # The accounts written by hand come in the order without sort: by name, then first name.
    assert written == sorted(written, key=lambda row: (row["last_name"], row["first_name"]))
    held = lists["users_by_access_role"]
    assert [mocklists.display_name(row) for row in held["items"]] == [
        "Dominique Bernard",
        "Alix Moreau",
    ]
    assert held["meta"]["total"] == 2
    asked = set(mocklists.HELD_ROLES)
    assert all(asked & set(row["access_role_ids"]) for row in held["items"])
    others = [row for row in written if row not in held["items"]]
    assert not any(asked & set(row["access_role_ids"]) for row in others)
    # Held by an account deactivated: the reading counts it, as the role counts its holders.
    assert [row["is_active"] for row in held["items"]] == [True, False]
    [found] = lists["users_search"]["items"]
    assert mocklists.display_name(found) == "Inès Roux"
    # Found by the address alone: neither the name nor the first name holds the text.
    # Found by its displayed name alone, without its accent nor its case: no column, nor the
    # address, holds the text, and the displayed name holds it only so compared.
    for column in ("last_name", "first_name", "email"):
        assert mocklists.SEARCHED_ACCOUNT not in found[column].lower()
    assert mocklists.SEARCHED_ACCOUNT not in mocklists.display_name(found).lower()
    assert mocktext.holds(mocklists.display_name(found), mocklists.SEARCHED_ACCOUNT)


def test_the_readings_of_the_roles_follow_their_parameters(lists: dict[str, Any]) -> None:
    written = fixture("access_roles")
    composed = lists["access_roles_composed"]
    assert [row["label"] for row in composed] == [
        "Auditeur",
        "Chiffreur",
        "Direction de projet",
        "Pilotage de projet",
    ]
    assert [row for row in written if row["is_predefined"] is False] == composed
    unheld = lists["access_roles_unheld"]
    assert [(row["label"], row["holder_count"]) for row in unheld] == [("Administrateur", 0)]
    assert all(row["holder_count"] >= 1 for row in written if row not in unheld)


def test_the_bounds_of_the_holders_inverted_are_refused_by_the_rule_of_the_bounds() -> None:
    refused = fixture("access_roles_bounds_inverted")
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    [field] = refused["fields"]
    # An integer, in the type of the column, as `holder_count` is.
    assert field == {
        "pointer": "/query/holder_count_max",
        "code": "VALUE_OUT_OF_RANGE",
        "params": {"minimum": 2},
    }


# --- The work breakdown (#560) ------------------------------------------------------------------


def _element(kind: str, identifier: str, label: str, below: list[Row] | None = None) -> Row:
    held = {"work_package": "order_items", "order_item": "deliverables"}
    row: Row = {f"{kind}_id": identifier, "label": label}
    if kind in held:
        row[held[kind]] = below or []
    return row


BREAKDOWN: Row = {
    "work_packages": [
        _element(
            "work_package",
            "w1",
            "Études",
            [
                _element("order_item", "o1", "Plans", [_element("deliverable", "d1", "Plan A")]),
                _element("order_item", "o2", "Notes", [_element("deliverable", "d2", "Note")]),
            ],
        ),
        _element(
            "work_package",
            "w2",
            "Montage des plans",
            [_element("order_item", "o3", "Câblage", [_element("deliverable", "d3", "Essai")])],
        ),
    ],
    "lock_version": 7,
}
"""A work breakdown of two lots, the first of two posts, each post of one deliverable (C-350)."""


def _tree(breakdown: dict[str, Any]) -> list[tuple[str, list[tuple[str, list[str]]]]]:
    """Say a work breakdown by its identifiers: lots, their posts, their deliverables."""
    return [
        (
            lot["work_package_id"],
            [
                (item["order_item_id"], [each["deliverable_id"] for each in item["deliverables"]])
                for item in lot["order_items"]
            ],
        )
        for lot in breakdown["work_packages"]
    ]


def test_the_search_of_the_breakdown_retains_its_matches_under_their_parents_alone() -> None:
    found: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, "PLAN")
    # « plan » is in w2 alone — its post o3 is not —, in o1 and in d1, under w1, whose post o2
    # holds nothing that matches.
    assert _tree(found) == [("w1", [("o1", ["d1"])]), ("w2", [])]
    assert _tree(mocklists.filtered_breakdown(BREAKDOWN, "absent")) == []


def test_a_filtered_reading_of_the_breakdown_has_no_counter_the_whole_one_has_its_own() -> None:
    # Sent back to setWorkBreakdown, a filtered reading would remove what it leaves out: its
    # counter is none, which the write refuses (#560) — even when the filter retains everything.
    assert mocklists.filtered_breakdown(BREAKDOWN)["lock_version"] == 7
    assert mocklists.filtered_breakdown(BREAKDOWN, "PLAN")["lock_version"] is None
    every = mocklists.filtered_breakdown(BREAKDOWN, kinds=mocklists.BREAKDOWN_KINDS)
    assert _tree(every) == _tree(BREAKDOWN)
    assert every["lock_version"] is None


def test_a_reading_of_the_contributors_has_a_counter_unless_it_is_filtered() -> None:
    contributors: Row = {"items": [], "lock_version": 4}
    rows: list[Row] = [{"user_id": "u1"}]
    assert mocklists.contributor_list(contributors, rows, filtered=False)["lock_version"] == 4
    assert mocklists.contributor_list(contributors, rows, filtered=True)["lock_version"] is None


def test_the_kinds_of_the_breakdown_retain_their_elements_under_their_parents() -> None:
    def kept(*kinds: str) -> list[tuple[str, list[tuple[str, list[str]]]]]:
        return _tree(mocklists.filtered_breakdown(BREAKDOWN, kinds=kinds))

    # The kinds in the order of the levels: lots, posts, deliverables (C-350).
    assert mocklists.BREAKDOWN_KINDS == ("work_package", "order_item", "deliverable")
    assert kept("work_package") == [("w1", []), ("w2", [])]
    assert kept("order_item") == [("w1", [("o1", []), ("o2", [])]), ("w2", [("o3", [])])]
    assert kept("deliverable") == _tree(BREAKDOWN)
    assert kept() == _tree(BREAKDOWN)
    with pytest.raises(ValueError, match="no kind of an element"):
        mocklists.filtered_breakdown(BREAKDOWN, kinds=("lot",))


def test_the_filters_of_the_breakdown_combine() -> None:
    # The posts whose label holds « n »: o1 « Plans » and o2 « Notes », under w1, given as their
    # parent; not o3 « Câblage ». w2 « Montage des plans » holds it, but is no post, and holds
    # none retained: it is left out.
    combined: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, "n", ("order_item",))
    assert _tree(combined) == [("w1", [("o1", []), ("o2", [])])]


def _marks(breakdown: dict[str, Any]) -> dict[str, bool]:
    """Say whether each element a reading gives is retained, by its identifier (#574)."""
    marks: dict[str, bool] = {}
    for lot in breakdown["work_packages"]:
        marks[lot["work_package_id"]] = lot["is_match"]
        for item in lot["order_items"]:
            marks[item["order_item_id"]] = item["is_match"]
            for each in item["deliverables"]:
                marks[each["deliverable_id"]] = each["is_match"]
    return marks


def test_each_element_given_says_whether_the_filters_retain_it_or_give_it_for_its_context() -> None:
    # « plan »: w1 is given for o1, which holds it, as d1 does; w2 holds it itself.
    searched: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, "PLAN")
    assert _marks(searched) == {"w1": False, "o1": True, "d1": True, "w2": True}
    # The posts: their lots are their context alone, never counted (#574).
    items: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, kinds=("order_item",))
    assert _marks(items) == {"w1": False, "o1": True, "o2": True, "w2": False, "o3": True}
    # « essai » is in d3 alone: w2 and o3 are its context, and w2 does not hold the text.
    tried: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, "Essai")
    assert _marks(tried) == {"w2": False, "o3": False, "d3": True}
    # The deliverables: every lot and every post is their context alone.
    deliverables: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, kinds=("deliverable",))
    assert _marks(deliverables) == {
        "w1": False,
        "o1": False,
        "d1": True,
        "o2": False,
        "d2": True,
        "w2": False,
        "o3": False,
        "d3": True,
    }
    # Without a filter, or every kind named, every element is retained.
    for every in ((), mocklists.BREAKDOWN_KINDS):
        found: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, kinds=every)
        whole: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN)
        assert set(_marks(found).values()) == {True}
        assert len(_marks(found)) == len(_marks(whole))
    # The mark comes after the label and before what the element holds, as the contract has it.
    [first, _] = searched["work_packages"]
    assert list(first) == ["work_package_id", "label", "is_match", "order_items"]
    held = ["order_item_id", "label", "is_match", "deliverables"]
    assert list(first["order_items"][0]) == held


def test_each_lot_and_post_read_says_the_task_that_bears_it() -> None:
    # #802: the reading says whether a task of the current revision bears a lot or a post, and
    # which, by its node and label (`attached_task`): « un lot ou un poste n'y est porté que par
    # une tâche à la fois » (WF-PLA-0170). The witness: the summary « Poste de commande » bears its
    # lot, no task its post; the mark, then the task, then what the element holds.
    read = fixture("work_breakdown")
    [lot] = read["work_packages"]
    [item] = lot["order_items"]
    station = universe(mockwitness.N.CONTROL_STATION)
    [core] = [node for node in fixture("nodes_core")["items"] if node["node_id"] == station]
    assert lot["attached_task"] == {"node_id": station, "label": core["task"]["label"]}
    assert core["task"]["work_package_id"] == lot["work_package_id"]
    assert item["attached_task"] is None
    keys = ["work_package_id", "label", "is_match", "attached_task", "order_items"]
    assert list(lot) == keys
    assert list(item) == ["order_item_id", "label", "is_match", "attached_task", "deliverables"]
    assert "attached_task" not in item["deliverables"][0]
    # Once the factory acceptance bears the post (task_attached), the post says it.
    acceptance = mockwitness.N.FACTORY_ACCEPTANCE
    attached = mockwitness.rewritten(
        mockwitness.CORE,
        lambda task: (
            replace(task, bears=mockwitness.FIRST_ITEM) if task.number == acceptance else task
        ),
    )
    after: dict[str, Any] = mocklists.breakdown_reading(mockwitness.WORK_BREAKDOWN, 1, attached)
    [node] = fixture("task_attached")["nodes"]
    borne = after["work_packages"][0]["order_items"][0]["attached_task"]
    assert borne == {"node_id": node["node_id"], "label": node["task"]["label"]}
    # The project created today has no task: its default work breakdown, no bearer.
    [default] = fixture("work_breakdown_default")["work_packages"]
    assert default["attached_task"] is None
    assert default["order_items"][0]["attached_task"] is None


def test_the_readings_of_the_breakdown_follow_their_parameters(lists: dict[str, Any]) -> None:
    read: dict[str, Any] = mocklists.breakdown_reading(
        mockwitness.WORK_BREAKDOWN, 1, mockwitness.CORE
    )
    [lot] = read["work_packages"]
    [item] = lot["order_items"]
    head = {key: lot[key] for key in ("work_package_id", "label")}
    bearer = {"attached_task": lot["attached_task"]}
    searched = lists["work_breakdown_search"]
    # The lot, whose label holds the text in another case, without what it holds.
    assert mocklists.SEARCHED_LABEL not in lot["label"]
    assert mocktext.folded(mocklists.SEARCHED_LABEL) in mocktext.folded(lot["label"])
    assert searched == {
        "work_packages": [{**head, "is_match": True, **bearer, "order_items": []}],
        "lock_version": None,
    }
    items = lists["work_breakdown_order_items"]
    post = {key: item[key] for key in ("order_item_id", "label")}
    assert items == {
        "work_packages": [
            {
                **head,
                "is_match": False,
                **bearer,
                "order_items": [
                    {**post, "is_match": True, "attached_task": None, "deliverables": []}
                ],
            }
        ],
        "lock_version": None,
    }
    # The witness holds a deliverable, which the reading of the posts leaves out.
    assert item["deliverables"] != []
    # Read whole, the witness is its work breakdown, every element retained, with its counter.
    assert set(_marks(read).values()) == {True}
    assert read == fixture("work_breakdown")
    assert read["lock_version"] == 1


def test_the_default_breakdown_bears_the_label_of_its_project() -> None:
    # « En son absence, le lotissement vaut un lot et un poste qui portent le libellé du
    # projet, sans livrable » (WF-PRJ-0020): the project created today.
    [lot] = fixture("work_breakdown_default")["work_packages"]
    [item] = lot["order_items"]
    project = fixture("project_created")
    assert lot["label"] == item["label"] == project["label"]
    assert (project["project_id"], project["label"]) == mockwitness.CREATED_PROJECT
    assert item["deliverables"] == []


def test_the_refusals_of_a_breakdown_written_name_their_field_as_the_contract_declares(
    lists: dict[str, Any],
) -> None:
    contract = (REPOSITORY / "docs/api/paths/projects.yaml").read_text(encoding="utf-8")
    block = contract.split("operationId: setWorkBreakdown\n", 1)[1]
    block = block.split("\n      '422':", 1)[1].split("\n/projects", 1)[0]
    forms = [
        re.compile(re.sub(r"<[ijk]>", r"\\d+", re.escape(form)))
        for form in re.findall(r"`(/work_packages/[^`]+)`", block)
    ]
    common = (REPOSITORY / "docs/api/components/common.yaml").read_text(encoding="utf-8")
    listed = common.split("\nErrorCode:\n", 1)[1].split("\n\n", 1)[0]
    codes = {line.strip()[2:] for line in listed.splitlines() if line.strip().startswith("- ")}
    read, entered = fixture("work_breakdown"), lists["work_breakdown_entered"]
    kinds = {
        each[f"{kind}_id"]: kind
        for lot in read["work_packages"]
        for kind, each in [
            ("work_package", lot),
            *(("order_item", item) for item in lot["order_items"]),
            *(
                ("deliverable", deliverable)
                for item in lot["order_items"]
                for deliverable in item["deliverables"]
            ),
        ]
    }
    # The post added comes after those the reading gives: its index, read from it.
    [lot] = read["work_packages"]
    j = len(lot["order_items"])
    added = f"/work_packages/0/order_items/{j}"
    [first] = lot["order_items"]
    [(delivered, _)] = mockwitness.WORK_BREAKDOWN[0].order_items[0].deliverables
    assert (kinds[delivered], kinds[first["order_item_id"]]) == ("deliverable", "order_item")
    told = {
        "work_breakdown_label_required": [{"pointer": f"{added}/label", "code": "VALUE_REQUIRED"}],
        "work_breakdown_unknown_item": [
            {"pointer": f"{added}/order_item_id", "code": "UNKNOWN_WORK_BREAKDOWN_ITEM"}
        ],
        "work_breakdown_duplicate_item": [
            {"pointer": f"{added}/order_item_id", "code": "DUPLICATE_WORK_BREAKDOWN_ITEM"}
        ],
    }
    for name, fields in told.items():
        refusal = lists[name]
        assert refusal["fields"] == fields, name
        assert refusal["status"] == 422
        for field in fields:
            assert any(form.fullmatch(field["pointer"]) for form in forms), name
            assert field["code"] in codes
    # An identifier the reading bears under another kind is unknown: a lot sent as a post, a
    # post sent as a deliverable.
    as_item = mocklists.entered_with(entered, {"order_item_id": lot["work_package_id"]})
    assert mocklists.breakdown_refusal(read, as_item, "none")["fields"] == [
        {"pointer": f"{added}/order_item_id", "code": "UNKNOWN_WORK_BREAKDOWN_ITEM"}
    ]
    as_deliverable = json.loads(json.dumps(entered))
    item = as_deliverable["work_packages"][0]["order_items"][j]
    item["deliverables"][0] = {"deliverable_id": first["order_item_id"], **item["deliverables"][0]}
    assert mocklists.breakdown_refusal(read, as_deliverable, "none")["fields"] == [
        {
            "pointer": f"{added}/deliverables/0/deliverable_id",
            "code": "UNKNOWN_WORK_BREAKDOWN_ITEM",
        }
    ]
    # The write entered, from the whole reading, is refused nothing.
    assert mocklists.breakdown_refusal(read, entered, "none")["fields"] == []


def test_the_fake_back_serves_the_refusal_of_an_empty_label_first() -> None:
    # Prism answers an invalid request by the first example of the 422: an empty label, which
    # the schema refuses by itself, not a rule the fake back cannot judge.
    contract = (REPOSITORY / "docs/api/paths/projects.yaml").read_text(encoding="utf-8")
    block = contract.split("operationId: setWorkBreakdown\n", 1)[1].split("\n/projects", 1)[0]
    cited = re.findall(r"fixtures/api/(\w+)\.json", block.split("'422':", 1)[1])
    assert cited[0] == "work_breakdown_label_required"
    assert cited == [
        "work_breakdown_label_required",
        "work_breakdown_unknown_item",
        "work_breakdown_duplicate_item",
    ]


def _without_marks(value: Any) -> Any:
    """Return a reading as its write: the same elements, its marks and their tasks left out."""
    if isinstance(value, list):
        return [_without_marks(each) for each in cast("list[Any]", value)]
    if isinstance(value, dict):
        fields = cast("dict[str, Any]", value)
        return {
            key: _without_marks(item)
            for key, item in fields.items()
            if key not in {"is_match", "attached_task"}
        }
    return value


def test_the_work_breakdown_entered_is_the_whole_reading_a_post_added_without_identifier(
    lists: dict[str, Any],
) -> None:
    # The screen writes from the whole reading, its marks and their tasks left; what it adds has
    # no identifier, which the server engenders (WF-DAT-0060): the client forges none.
    read = fixture("work_breakdown")
    entered = lists["work_breakdown_entered"]
    replayed = _without_marks(read)
    replayed["work_packages"][0]["order_items"].append(
        {
            "label": mockwitness.SECOND_ITEM.label,
            "deliverables": [{"label": label} for _, label in mockwitness.SECOND_ITEM.deliverables],
        }
    )
    assert entered == replayed
    assert entered["lock_version"] == read["lock_version"]
    with pytest.raises(ValueError, match="never written back"):
        mocklists.written(lists["work_breakdown_search"])


def test_the_work_breakdown_saved_gives_the_elements_added_their_identifiers_and_a_counter(
    lists: dict[str, Any],
) -> None:
    # The answer of setWorkBreakdown is the whole reading, every element retained; the elements
    # entered without identifier come back with the one the server gave them, the post added
    # borne by no task, the lot by the summary that bore it (#802).
    entered, saved = lists["work_breakdown_entered"], lists["work_breakdown_saved"]
    assert set(_marks(saved).values()) == {True}
    known = set(_marks(fixture("work_breakdown")))
    given = set(_marks(saved)) - known
    assert given == {
        mockwitness.SECOND_ITEM.identifier,
        *(d for d, _ in mockwitness.SECOND_ITEM.deliverables),
    }
    [lot] = saved["work_packages"]
    assert lot["attached_task"] == fixture("work_breakdown")["work_packages"][0]["attached_task"]
    assert [item["attached_task"] for item in lot["order_items"]] == [None, None]

    def anonymous(value: Any) -> Any:
        if isinstance(value, list):
            return [anonymous(each) for each in cast("list[Any]", value)]
        if isinstance(value, dict):
            fields = cast("dict[str, Any]", value)
            return {
                key: anonymous(item)
                for key, item in fields.items()
                if not (key.endswith("_id") and item in given)
            }
        return value

    assert anonymous(_without_marks(saved)) == {
        **entered,
        "lock_version": entered["lock_version"] + 1,
    }


def _examples_of(operation: str, path: str) -> dict[str, str]:
    """Return the fixtures an operation cites before its 401, by the name of their example.

    Those of its request body and of its 200: the write and the reading it answers.
    """
    text = (REPOSITORY / "docs/api/paths" / path).read_text(encoding="utf-8")
    block = text.split(f"operationId: {operation}\n", 1)[1].split("'401'", 1)[0]
    return dict(re.findall(r"(\w+): \{ \$ref: [./]*fixtures/api/(\w+)\.json \}", block))


def test_the_filtered_readings_the_contract_cites_have_no_counter_the_others_have_one() -> None:
    # The reading a write may follow — whole, sorted or not — has its counter; a filtered one,
    # none, so that setWorkBreakdown and setContributors refuse it sent back as it is (#560).
    expected = {
        ("getWorkBreakdown", "projects.yaml"): {
            "witness": True,
            "default": True,
            "search": False,
            "order_items": False,
        },
        # The write, from a whole reading, and its answer, whole: both with their counter.
        ("setWorkBreakdown", "projects.yaml"): {"entered": True, "saved": True},
        ("listContributors", "projects.yaml"): {
            "witness": True,
            "by_name": True,
            "search": False,
            "inactive": False,
            "anonymized": True,
        },
    }
    for (operation, path), counted in expected.items():
        cited = _examples_of(operation, path)
        assert set(cited) == set(counted), operation
        for name, fixture_name in cited.items():
            counter = fixture(fixture_name)["lock_version"]
            assert isinstance(counter, int) is counted[name], (operation, name)
            assert (counter is None) is not counted[name], (operation, name)


def test_the_accounts_are_filtered_by_their_state() -> None:
    rows: list[Row] = [
        {"user_id": "u1", "is_active": True},
        {"user_id": "u2", "is_active": False},
        {"user_id": "u3", "is_active": True},
    ]
    assert _ids(mocklists.in_state(rows, active=True), "user_id") == ["u1", "u3"]
    assert _ids(mocklists.in_state(rows, active=False), "user_id") == ["u2"]


def test_the_reading_of_the_accounts_deactivated_holds_them_alone(lists: dict[str, Any]) -> None:
    written = fixture("users")["items"]
    inactive = lists["users_inactive"]
    assert [mocklists.display_name(row) for row in inactive["items"]] == ["Alix Moreau"]
    assert inactive["items"] == [row for row in written if row["is_active"] is False]
    assert inactive["meta"]["total"] == 1


def _audited(identifier: str, created: str, by: Row, updated_by: Row | None = None) -> Row:
    return {
        "id": identifier,
        "audit": {
            "created_at": created,
            "created_by": by,
            "updated_at": created,
            "updated_by": by if updated_by is None else updated_by,
        },
    }


PLATFORM: Row = {"kind": "platform"}
ANONYMISED: Row = {"kind": "user", "user_id": "u0", "display_name": None}


def _account(name: str) -> Row:
    return {"kind": "user", "user_id": name.lower(), "display_name": name}


def test_the_audit_columns_are_filtered_and_sorted_as_the_contract_says() -> None:
    # #936: the dates by their instant, the authors by their name, the platform after the
    # accounts in the ascending order and before them in the descending one; equals keep the
    # order they came in.
    rows = [
        _audited("r1", "2026-02-01T00:00:00Z", PLATFORM),
        _audited("r2", "2026-01-01T00:00:00Z", _account("Zoé Blanc")),
        _audited("r3", "2026-03-01T00:00:00Z", _account("Ana Roy")),
        _audited("r4", "2026-01-01T00:00:00Z", PLATFORM, _account("Ana Roy")),
    ]
    assert _ids(mocklists.written_by(rows, "created_by", "platform"), "id") == ["r1", "r4"]
    assert _ids(mocklists.written_by(rows, "updated_by", "user"), "id") == ["r2", "r3", "r4"]
    by_date = mocklists.ordered(rows, mocklists.written_at("created_at"))
    assert _ids(by_date, "id") == ["r2", "r4", "r1", "r3"]
    by_author = mocklists.author_name("created_by")
    assert _ids(mocklists.ordered(rows, by_author), "id") == ["r3", "r2", "r1", "r4"]
    descending = mocklists.ordered(rows, by_author, descending=True)
    assert _ids(descending, "id") == ["r1", "r4", "r2", "r3"]
    # An author anonymised would come between the names and the platform: it is refused.
    with pytest.raises(ValueError, match="anonymised"):
        mocklists.ordered([_audited("r5", "2026-01-01T00:00:00Z", ANONYMISED)], by_author)


def test_the_readings_of_the_audit_columns_follow_their_parameters(lists: dict[str, Any]) -> None:
    users = fixture("users")["items"]
    by_platform = lists["users_created_by_platform"]
    assert [mocklists.display_name(row) for row in by_platform["items"]] == [
        "Dominique Bernard",
        "Sacha Lefèvre",
        "Camille Martin",
    ]
    assert by_platform["meta"]["total"] == 3
    assert all(row["audit"]["created_by"] == PLATFORM for row in by_platform["items"])
    created = lists["users_by_created_at"]["items"]
    assert sorted(created, key=lambda row: row["user_id"]) == sorted(
        users, key=lambda row: row["user_id"]
    )
    instants = [row["audit"]["created_at"] for row in created]
    assert instants == sorted(instants)
    # Created at the installation, at one instant: in the order of the list without sort, by name.
    assert [mocklists.display_name(row) for row in created[:2]] == [
        "Dominique Bernard",
        "Camille Martin",
    ]
    roles = lists["access_roles_by_updated_by"]
    assert [row["label"] for row in roles] == [
        "Auditeur",
        "Chiffreur",
        "Direction de projet",
        "Pilotage de projet",
        "Administrateur",
        "Chef de projet",
        "Manager",
    ]
    assert [row["audit"]["updated_by"]["kind"] for row in roles] == ["user"] * 4 + ["platform"] * 3


def test_the_role_alix_moreau_changed_names_her_until_her_account_is_anonymised() -> None:
    # #936: the counterfactual readings filtered on the author of the last change, Alix Moreau
    # (303), deactivated: she stays named; anonymised, her name is null, the change still hers.
    [alix] = [row for row in fixture("users")["items"] if row["user_id"].endswith("000000000303")]
    assert alix["is_active"] is False
    [witness] = [row for row in fixture("access_roles") if row["label"] == "Chef de projet"]
    [named] = fixture("access_roles_updated_by_deactivated")
    [anonymised] = fixture("access_roles_updated_by_anonymized")
    for read, name in ((named, "Alix Moreau"), (anonymised, None)):
        author = read["audit"]["updated_by"]
        assert author == {"kind": "user", "user_id": alix["user_id"], "display_name": name}
        # Changed while she was active: after her creation, before her deactivation.
        changed = read["audit"]["updated_at"]
        assert alix["audit"]["created_at"] < changed < alix["audit"]["updated_at"]
        # The role of the witness otherwise, its version advanced by the change.
        assert read["lock_version"] == witness["lock_version"] + 1
        changed_fields = {"audit", "lock_version"}
        unchanged = {key: value for key, value in read.items() if key not in changed_fields}
        assert unchanged == {
            key: value for key, value in witness.items() if key not in changed_fields
        }
        assert read["audit"]["created_by"] == witness["audit"]["created_by"]
    assert named["audit"]["updated_by"]["display_name"] == mocklists.display_name(alix)
