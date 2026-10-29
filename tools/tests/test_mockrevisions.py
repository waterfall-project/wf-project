# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the revisions and the structures of the witness (US-0701/L2, #1602).

They try the planning start of a structure moved a week earlier against the Vérif of WF-PLA-0020
it illustrates, the calculation date of the workload of a marked revision against that of
WF-DEV-0070, and the attributes the revisions and the structures written by hand carry against the
witness, citing WF-REV-0030-A, WF-REV-0070-A and WF-REV-0090-A where they try their Vérif.
"""

from datetime import date, timedelta
from typing import Any, cast

import pytest

from wftools import (
    mockcore,
    mockcurves,
    mockdata,
    mockhistory,
    mockplanning,
    mocksnapshot,
    mocktoday,
    mockwitness,
)
from wftools.mockstructure import LABOUR_RATES, money
from wftools.mockwitness import AMENDMENT_MERGED, PLANNING_START, fixture

type Node = dict[str, Any]

LISTS = ("revisions", "revisions_marked")
"""The lists of the revisions written by hand, which name every revision of the witness."""

WEEK = timedelta(days=7)


@pytest.fixture(scope="module")
def advanced() -> Node:
    """Return what updateCostStructure answers to the planning start advanced a week."""
    return cast("Node", mockplanning.planning_start_advanced())


@pytest.fixture(scope="module")
def tasks() -> dict[str, Node]:
    """Return the tasks, not summaries, of the main structure the variant reads before the write."""
    rows = mockplanning.reading()
    return {
        cast("str", row.node["node_id"]): row.node
        for row in rows
        if row.kind == mockcore.TASK and not cast("Node", row.node["task"])["is_summary"]
    }


def _day(instant: Any) -> date:
    return date.fromisoformat(cast("dict[str, str]", instant)["date"])


def _automatic(node: Node) -> bool:
    return node["task"]["scheduling_mode"] == "automatic"


@pytest.mark.requirement("WF-PLA-0020-A")
def test_advancing_the_planning_start_a_week_advances_its_tasks_and_their_successors(
    advanced: Node, tasks: dict[str, Node]
) -> None:
    # Vérif : « Une tâche en mode automatique sans prédécesseur commence à la date de début de
    # planning ; avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs
    # automatiques. » The write writes no node; the tasks it redates are in `rescheduled`.
    assert mockplanning.ADVANCED_BY == WEEK
    moved = {entry["node_id"]: entry for entry in cast("list[Node]", advanced["rescheduled"])}
    assert advanced["nodes"] == []
    roots = {
        node_id
        for node_id, node in tasks.items()
        if _automatic(node)
        and not node.get("predecessors")
        and _day(node["task"]["start"]) == PLANNING_START
    }
    assert roots
    for node_id in roots:
        assert _day(moved[node_id]["start"]) == PLANNING_START - WEEK
    followers = [
        node_id
        for node_id, node in tasks.items()
        if _automatic(node)
        and node.get("predecessors")
        and all(link["predecessor_node_id"] in roots for link in node["predecessors"])
    ]
    assert followers
    for node_id in followers:
        assert _day(moved[node_id]["start"]) == _day(tasks[node_id]["task"]["start"]) - WEEK


def test_the_tasks_in_manual_mode_do_not_move(advanced: Node, tasks: dict[str, Node]) -> None:
    moved = {entry["node_id"] for entry in cast("list[Node]", advanced["rescheduled"])}
    manual = {node_id for node_id, node in tasks.items() if not _automatic(node)}
    assert manual
    assert not moved & manual


def test_the_variant_is_read_before_any_task_starts_by_its_dates() -> None:
    first = PLANNING_START - mockplanning.ADVANCED_BY
    assert mockwitness.RISK_752_OCCURRED.on <= mockplanning.ADVANCED_ON < first


def test_the_planning_start_moved_advances_the_counter_of_the_main_structure(
    advanced: Node,
) -> None:
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    assert advanced["structure_lock_version"] == main["lock_version"] + 1


def test_the_witness_structures_start_where_their_tasks_are_dated() -> None:
    # The main structure and the differentials date their tasks from the planning start of the
    # witness (``mockdating.schedule``); a differential takes the main structure's at its creation.
    structures: list[Node] = [
        *fixture("structures"),
        *fixture("structures_amendments"),
        fixture("amendment_created"),
    ]
    for structure in structures:
        if structure["kind"] != "risk":
            assert structure["planning_start_on"] == PLANNING_START.isoformat()


def test_a_report_without_current_revision_carries_the_counters_of_the_reference() -> None:
    # E-10: the merge asked on the reference reads its structures, whose counters its marking
    # froze — the main structure and the amendment 2, not merged, of `structures_amendments`.
    report = fixture("structure_merge_report_without_current_revision")
    structures = fixture("structures_amendments")
    [main] = [each for each in structures if each["kind"] == "main"]
    [amendment] = [
        each for each in structures if each["kind"] == "amendment" and not each["is_merged"]
    ]
    assert report["main_structure_lock_version"] == main["lock_version"]
    assert report["amendment_lock_version"] == amendment["lock_version"]


def _revisions() -> list[Node]:
    return [revision for name in LISTS for revision in fixture(name)["items"]]


def test_a_revision_names_the_marked_revision_it_copies_by_its_version() -> None:
    names = {each["revision_id"]: each["version_name"] for each in _revisions()}
    for revision in _revisions():
        source = revision["source_revision_id"]
        assert revision["source_version_name"] == (None if source is None else names[source])
    first = {each["version_name"] for each in _revisions() if each["source_revision_id"] is None}
    assert first == {"Offre v1.0"}


@pytest.mark.requirement("WF-REV-0090-A")
@pytest.mark.requirement("WF-REV-0070-A")
def test_the_revisions_carry_the_parameters_of_their_project() -> None:
    # The witness never changed its inflation nor its probability: every revision carries the
    # project's. It does not tell « conserved at the marking » from « follows the project », both
    # being equal here: see DECISIONS.md, « Le témoin n'a jamais changé son taux d'inflation ».
    project = fixture("project")
    for revision in _revisions():
        assert revision["inflation_rate"] == project["inflation_rate"]
        assert revision["win_probability"] == project["win_probability"]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_workload_of_a_marked_revision_is_calculated_at_its_marking() -> None:
    # Vérif : « sur une révision marquée, la date de calcul est sa date de marquage ».
    reference = mocktoday.witness().reference
    plan = mockcurves.workload(reference, "marked_remaining")
    context = cast("Node", plan["context"])
    assert context["revision_id"] == mockhistory.REFERENCE
    assert context["computed_at"] == mockhistory.stamp(AMENDMENT_MERGED.instant)


@pytest.fixture(scope="module")
def snapshots() -> dict[str, Node]:
    """Return the reference and the offer as getRevision reads them, with their snapshot."""
    return cast("dict[str, Node]", mocksnapshot.revisions(mockdata.categories()))


@pytest.mark.requirement("WF-REV-0030-A")
@pytest.mark.parametrize("name", ["revision_marked", "revision_offer"])
def test_a_marked_revision_conserves_the_images_of_the_reference_it_employs(
    snapshots: dict[str, Node], name: str
) -> None:
    # E-03, E-11: images without the commands of today, the rates of its reference year alone.
    revision = snapshots[name]
    employed = revision["snapshot"]["employed_reference"]
    for kind in ("resource_roles", "calendars", "cost_categories"):
        assert employed[kind]
        assert all("available_commands" not in image for image in employed[kind])
    rates = employed["hourly_rates"]
    assert {rate["year"] for rate in rates} == {revision["reference_year"]}
    assert all(set(rate) == {"cost_category_id", "year", "amount"} for rate in rates)
    roles = {role["calendar_id"] for role in employed["resource_roles"]}
    calendars = {calendar["calendar_id"] for calendar in employed["calendars"]}
    assert calendars == roles | {mockwitness.default_calendar().calendar_id}


def test_the_reference_conserves_the_rates_of_2026_of_its_labour(
    snapshots: dict[str, Node],
) -> None:
    rates = snapshots["revision_marked"]["snapshot"]["employed_reference"]["hourly_rates"]
    assert {rate["cost_category_id"]: rate["amount"] for rate in rates} == {
        category: money(amount) for category, amount in LABOUR_RATES.items()
    }


def test_the_revision_in_progress_omits_its_snapshot_and_the_lists_too() -> None:
    assert "snapshot" not in fixture("revision")
    assert all("snapshot" not in revision for revision in _revisions())
