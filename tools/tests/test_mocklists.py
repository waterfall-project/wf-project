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
from datetime import UTC, date, datetime, time
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest

from wftools import REPOSITORY, mockdata, mocklists, mocktext, mockwitness
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
    charged = lists["subprojects_with_actual_costs"]
    assert [row["code"] for row in charged] == ["SP-CMD"]
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
    held = {"order_item": "work_packages", "work_package": "deliverables"}
    row: Row = {f"{kind}_id": identifier, "label": label}
    if kind in held:
        row[held[kind]] = below or []
    return row


BREAKDOWN: Row = {
    "order_items": [
        _element(
            "order_item",
            "o1",
            "Études",
            [
                _element("work_package", "w1", "Plans", [_element("deliverable", "d1", "Plan A")]),
                _element("work_package", "w2", "Notes", [_element("deliverable", "d2", "Note")]),
            ],
        ),
        _element(
            "order_item",
            "o2",
            "Montage des plans",
            [_element("work_package", "w3", "Câblage", [_element("deliverable", "d3", "Essai")])],
        ),
    ],
    "lock_version": 7,
}


def _tree(breakdown: dict[str, Any]) -> list[tuple[str, list[tuple[str, list[str]]]]]:
    """Say a work breakdown by its identifiers: order items, their packages, their deliverables."""
    return [
        (
            item["order_item_id"],
            [
                (
                    package["work_package_id"],
                    [each["deliverable_id"] for each in package["deliverables"]],
                )
                for package in item["work_packages"]
            ],
        )
        for item in breakdown["order_items"]
    ]


def test_the_search_of_the_breakdown_retains_its_matches_under_their_parents_alone() -> None:
    found: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, "PLAN")
    # « plan » is in o2 alone — its package w3 is not —, in w1 and in d1, under o1, whose
    # package w2 holds nothing that matches.
    assert _tree(found) == [("o1", [("w1", ["d1"])]), ("o2", [])]
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

    assert kept("order_item") == [("o1", []), ("o2", [])]
    assert kept("work_package") == [("o1", [("w1", []), ("w2", [])]), ("o2", [("w3", [])])]
    assert kept("deliverable") == _tree(BREAKDOWN)
    assert kept() == _tree(BREAKDOWN)
    with pytest.raises(ValueError, match="no kind of an element"):
        mocklists.filtered_breakdown(BREAKDOWN, kinds=("lot",))


def test_the_filters_of_the_breakdown_combine() -> None:
    # The work packages whose label holds « n »: w1 « Plans » and w2 « Notes », under o1, given
    # as their parent; not w3 « Câblage ». o2 « Montage des plans » holds it, but is no work
    # package, and holds none retained: it is left out.
    combined: dict[str, Any] = mocklists.filtered_breakdown(BREAKDOWN, "n", ("work_package",))
    assert _tree(combined) == [("o1", [("w1", []), ("w2", [])])]


def test_the_readings_of_the_breakdown_follow_their_parameters(lists: dict[str, Any]) -> None:
    whole: dict[str, Any] = mocklists.work_breakdown(mockwitness.WORK_BREAKDOWN, 1)
    [item] = whole["order_items"]
    [package] = item["work_packages"]
    searched = lists["work_breakdown_search"]
    # The order item, whose label holds the text in another case, without what it holds.
    assert mocklists.SEARCHED_LABEL not in item["label"]
    assert mocktext.folded(mocklists.SEARCHED_LABEL) in mocktext.folded(item["label"])
    assert searched == {"order_items": [{**item, "work_packages": []}], "lock_version": None}
    packages = lists["work_breakdown_work_packages"]
    assert packages == {
        "order_items": [{**item, "work_packages": [{**package, "deliverables": []}]}],
        "lock_version": None,
    }
    # The witness holds a deliverable, which the reading of the work packages leaves out.
    assert package["deliverables"] != []


def _examples_of(operation: str, path: str) -> dict[str, str]:
    """Return the fixtures the 200 of an operation cites, by the name of their example."""
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
            "work_packages": False,
        },
        ("listContributors", "projects.yaml"): {
            "witness": True,
            "by_name": True,
            "search": False,
            "inactive": False,
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


# --- The backups (#588) -------------------------------------------------------------------------


def _backup(identifier: str, taken: str, size: int, state: tuple[str, str], *, kept: bool) -> Row:
    """Return a backup, `state` its verification and origin, its commands as the contract says."""
    verification, origin = state
    mark = "release" if kept else "retain"
    verified = [] if verification == "passed" else ["backup_verified"]
    return {
        "backup_id": identifier,
        "taken_at": taken,
        "size_bytes": size,
        "verification": verification,
        "is_retained": kept,
        "scope": "database",
        "origin": origin,
        "available_commands": [
            {"command": mark, "is_available": True, "missing_conditions": []},
            {"command": "download", "is_available": not verified, "missing_conditions": verified},
            {"command": "restore", "is_available": not verified, "missing_conditions": verified},
        ],
    }


BACKUPS: list[Row] = [
    _backup("b4", "2026-06-30T22:00:00Z", 400, ("pending", "scheduled"), kept=False),
    _backup("b3", "2026-06-03T01:00:00Z", 300, ("passed", "scheduled"), kept=False),
    _backup("b2", "2026-05-31T22:00:00Z", 350, ("failed", "scheduled"), kept=True),
    _backup("b1", "2026-01-30T17:45:00Z", 100, ("passed", "manual"), kept=True),
]
"""Backups around June in Paris, from 2026-05-31T22:00Z included to 2026-06-30T22:00Z excluded."""


def test_the_orders_of_the_backups_follow_the_enumerations_of_the_contract() -> None:
    assert list(mocklists.BACKUP_ORIGINS) == _enumeration("platform.yaml", "BackupOrigin")
    assert list(mocklists.BACKUP_VERIFICATIONS) == _enumeration(
        "platform.yaml", "BackupVerification"
    )
    # The conditions are listed one a line: the block of the enumeration names the one lacked.
    text = (REPOSITORY / "docs/api/components/schemas/projects.yaml").read_text(encoding="utf-8")
    conditions = text.split("\nCommandCondition:\n", 1)[1].split("\n\n", 1)[0]
    assert f"\n    - {mocklists.RUNNING_BACKUP}\n" in conditions


def test_the_period_of_the_backups_retains_the_instants_taken_from_included_to_excluded() -> None:
    start, end = mocklists.BACKUP_PERIOD
    # b2 at the very start is in, b4 at the very end is out.
    assert _ids(mocklists.taken_within(BACKUPS, start, end), "backup_id") == ["b3", "b2"]
    assert _ids(mocklists.taken_within(BACKUPS, end, None), "backup_id") == ["b4"]
    assert mocklists.taken_within(BACKUPS, start, start) == []
    with pytest.raises(ValueError, match="before it starts"):
        mocklists.taken_within(BACKUPS, end, start)


def test_the_backups_are_filtered_by_their_origin_and_their_marking() -> None:
    assert _ids(mocklists.of_origins(BACKUPS, ("manual",)), "backup_id") == ["b1"]
    assert _ids(mocklists.of_origins(BACKUPS, ()), "backup_id") == ["b4", "b3", "b2", "b1"]
    with pytest.raises(ValueError, match="no origin of a backup"):
        mocklists.of_origins(BACKUPS, ("nightly",))
    assert _ids(mocklists.marked(BACKUPS, retained=True), "backup_id") == ["b2", "b1"]
    assert _ids(mocklists.marked(BACKUPS, retained=False), "backup_id") == ["b4", "b3"]


def test_the_columns_of_the_backups_sort_as_the_contract_says() -> None:
    def sorted_ids(column: str, *, descending: bool = False) -> list[str]:
        return _ids(
            mocklists.ordered(BACKUPS, mocklists.BACKUP_KEYS[column], descending=descending),
            "backup_id",
        )

    assert sorted_ids("size_bytes") == ["b1", "b3", "b2", "b4"]
    assert sorted_ids("taken_at", descending=True) == ["b4", "b3", "b2", "b1"]
    # The enumerations in their order: pending, passed, failed; manual, scheduled. A tie keeps the
    # order of the list without sort.
    assert sorted_ids("verification") == ["b4", "b3", "b1", "b2"]
    assert sorted_ids("origin") == ["b1", "b4", "b3", "b2"]
    # The backups marked to be kept first in the ascending order.
    assert sorted_ids("is_retained") == ["b2", "b1", "b4", "b3"]


def test_a_reader_sees_no_command_and_a_running_backup_withholds_the_restoration() -> None:
    for backup in mocklists.without_commands(BACKUPS):
        assert backup["available_commands"] == []
    [first, *_, last] = mocklists.while_backup_runs(BACKUPS)
    commands = cast("list[Row]", first["available_commands"])
    by_command = {each["command"]: each for each in commands}
    # The restoration of an unverified backup lacks the verification and the running backup.
    assert by_command["restore"] == {
        "command": "restore",
        "is_available": False,
        "missing_conditions": ["backup_verified", "no_backup_running"],
    }
    assert by_command["download"]["missing_conditions"] == ["backup_verified"]
    assert by_command["retain"]["is_available"] is True
    [restore] = [
        each
        for each in cast("list[Row]", last["available_commands"])
        if each["command"] == "restore"
    ]
    assert restore == {
        "command": "restore",
        "is_available": False,
        "missing_conditions": ["no_backup_running"],
    }
    # Nothing else changes: the backups themselves are as they were.
    assert [{k: v for k, v in b.items() if k != "available_commands"} for b in BACKUPS] == [
        {k: v for k, v in b.items() if k != "available_commands"}
        for b in mocklists.while_backup_runs(BACKUPS)
    ]


def test_the_readings_of_the_backups_follow_their_parameters(lists: dict[str, Any]) -> None:
    written = fixture("backups")["items"]
    assert [row["available_commands"] for row in lists["backups_reader"]["items"]] == [
        [] for _ in written
    ]
    during = lists["backups_during_backup"]["items"]
    assert len(during) == len(written)
    for row in during:
        [restore] = [each for each in row["available_commands"] if each["command"] == "restore"]
        assert restore["is_available"] is False
        assert "no_backup_running" in restore["missing_conditions"]
    manual = lists["backups_manual"]
    assert [row["origin"] for row in manual["items"]] == ["manual"]
    assert manual["meta"]["total"] == 1
    kept = lists["backups_retained"]
    assert kept["items"] == [row for row in written if row["is_retained"] is True]
    period = lists["backups_period"]
    # June in Paris: the backups of 1, 2 and 3 June, the most recent first.
    assert [row["taken_at"][:10] for row in period["items"]] == [
        "2026-06-03",
        "2026-06-02",
        "2026-06-01",
    ]
    by_size = lists["backups_by_size"]["items"]
    sizes = [row["size_bytes"] for row in by_size]
    assert sizes == sorted(sizes)
    assert by_size[0]["origin"] == "manual"
    for name in ("backups_reader", "backups_manual", "backups_retained", "backups_period"):
        assert lists[name]["meta"]["total"] == len(lists[name]["items"]), name
