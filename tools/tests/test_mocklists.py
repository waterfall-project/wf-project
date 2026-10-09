# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the readings of the list of the projects, of the subprojects and of the contributors.

They try the rules of sort, search and filter the fake back applies (#536) on rows made for them,
and the examples against the lists written by hand and the contract they illustrate — not the
Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from wftools import REPOSITORY, mockdata, mocklists
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
    # Whatever the sort and the filters, the counter is that of the whole list.
    for name in ("contributors_by_name", "contributors_search", "contributors_inactive"):
        assert lists[name]["lock_version"] == written["lock_version"]


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
