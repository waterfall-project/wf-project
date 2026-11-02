# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the common tree as the witness renders it after US-0701/L3 (#1603).

The float and the criticality of a summary (WF-PLA-0100, F-01), the link a task in manual mode
and its predecessor name in conflict (WF-PLA-0020, F-02), the columns of the planning grid
(WF-PLA-0080, F-07), the label a line receives and the category it holds from its role
(WF-DEV-0020, F-08, F-09), the line of provision that takes no re-estimate (F-10), the completed
milestone dated (WF-PLA-0130, F-13), the mode of a summary (WF-PLA-0040, F-14), and the bounds of a
column (WF-IHM-0130, F-06).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

import pytest
from witnessreadings import ACCEPTANCE, LABOUR, PROVISION, STUDIES, facet, nodes

from wftools import mockcore, mockdating, mockgestures, mockids, mockwitness, mockwrites
from wftools.mockcalendar import START_TO_START
from wftools.mockwitness import Link, Task

if TYPE_CHECKING:
    from collections.abc import Mapping

START = date(2026, 3, 2)
"""The planning start of the structures declared here, a Monday."""

PREDECESSOR, MANUAL, SUMMARY = 901, 902, 903


def _declared(link_type: str, manual: tuple[date, date]) -> Mapping[int, mockdating.Dated]:
    """Return a declared structure, dated.

    A summary over a task of ten days, in automatic mode, linked to a task in manual mode at the
    dates given.
    """
    predecessor = Task(PREDECESSOR, "Prédécesseur", days=10)
    successor = Task(
        MANUAL, "Tâche manuelle", days=5, links=(Link(PREDECESSOR, link_type),), manual=manual
    )
    summary = Task(SUMMARY, "Récapitulative", children=(predecessor,))
    return mockdating.schedule((summary, successor), START)


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_summary_with_a_critical_subordinate_is_critical_and_shows_its_float(
    readings: dict[str, Any],
) -> None:
    # « Une récapitulative dont une subordonnée est critique est critique et affiche la marge de
    # cette subordonnée, nulle ou négative. »
    studies = facet(nodes(readings["nodes_planning.json"])[STUDIES])
    assert (studies["total_float"], studies["is_critical"]) == ({"value": "0", "unit": "d"}, True)
    late = _declared("finish_to_start", (date(2026, 3, 9), date(2026, 3, 13)))
    negative = mockdating.float_of(late, PREDECESSOR)
    assert negative is not None
    assert negative < 0
    assert mockdating.float_of(late, SUMMARY) == negative
    # A task in manual mode shows no float (WF-PLA-0100).
    assert mockdating.float_of(late, MANUAL) is None


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_manual_task_dated_before_its_predecessor_finishes_is_signalled_with_it() -> None:
    # « Une tâche manuelle datée avant la fin calculée de son prédécesseur est signalée dans la
    # grille et dans le Gantt, avec ce prédécesseur ; la retarder au-delà de cette fin […] fait
    # disparaître le signalement. »
    early = _declared("finish_to_start", (date(2026, 3, 9), date(2026, 3, 13)))
    conflict = mockdating.Conflict(PREDECESSOR, MANUAL, "finish_to_start")
    assert early[PREDECESSOR].conflicts == [conflict]
    assert early[MANUAL].conflicts == [conflict]
    late = _declared("finish_to_start", (date(2026, 3, 16), date(2026, 3, 20)))
    assert late[PREDECESSOR].conflicts == []
    assert late[MANUAL].conflicts == []


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_start_to_start_predecessor_that_cannot_start_first_is_negative_and_signalled() -> None:
    # « Un prédécesseur lié début à début à une tâche manuelle, et qui ne peut pas commencer avant
    # elle, porte une marge négative et est signalé. »
    before = _declared(START_TO_START, (date(2026, 2, 26), date(2026, 3, 4)))
    total = before[PREDECESSOR].total_float
    assert total is not None
    assert total < 0
    assert before[PREDECESSOR].conflicts == [
        mockdating.Conflict(PREDECESSOR, MANUAL, START_TO_START)
    ]


@pytest.mark.requirement("WF-PLA-0020-A")
def test_the_example_of_a_conflict_names_the_link_on_both_tasks() -> None:
    written = mockwitness.fixture("task_dates_conflicting")
    [manual] = written["nodes"]
    [conflict] = manual["task"]["link_conflicts"]
    assert conflict["successor_node_id"] == manual["node_id"]
    assert manual["task"]["total_float"] is None
    redated = {entry["node_id"]: entry for entry in written["rescheduled"]}
    predecessor = redated[conflict["predecessor_node_id"]]
    assert predecessor["link_conflicts"] == [conflict]
    assert Decimal(predecessor["total_float"]["value"]) < 0
    assert predecessor["is_critical"] is True
    # Every other task the write redates bears no conflict.
    assert [entry for entry in written["rescheduled"] if entry["link_conflicts"]] == [predecessor]


@pytest.mark.requirement("WF-PLA-0080-A")
def test_the_columns_of_the_planning_grid_are_those_it_cites() -> None:
    # « Chacune des colonnes citées est présente » ; the state is « signalé par une marque
    # visuelle et non par une colonne ».
    columns = mockwrites.node_columns()
    task = columns[: columns.index("work_breakdown") + 1]
    assert task == [
        "label",
        "description",
        "scheduling_mode",
        "duration",
        "start",
        "finish",
        "physical_progress",
        "total_float",
        "is_critical",
        "started_on",
        "completed_on",
        "predecessors",
        "work_breakdown",
    ]
    assert "progress" not in columns


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_milestone_completed_without_starting_starts_the_day_it_completes(
    readings: dict[str, Any],
) -> None:
    # « Une tâche terminée sans avoir été démarrée prend pour date de démarrage celle de sa
    # terminaison » ; reopened, it bears neither.
    reception = facet(nodes(readings["nodes_planning.json"])[ACCEPTANCE])
    assert reception["started_on"] == reception["completed_on"] == "2026-04-24"
    [reopened] = mockwitness.fixture("milestone_reopened")["nodes"]
    assert "started_on" not in reopened["task"]
    assert "completed_on" not in reopened["task"]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_the_category_of_a_labour_line_is_its_role_and_not_entered(
    readings: dict[str, Any],
) -> None:
    # « La catégorie d'une ligne de main-d'œuvre n'est pas saisissable : c'est celle de son rôle. »
    labour = nodes(readings["nodes_estimate.json"])[LABOUR]
    assert "estimate_line.cost_category_id" in labour["computed_fields"]
    assert "estimate_line.cost_category_id" not in labour["editable_fields"]
    depends = mockwitness.fixture("dependencies_labour_category")
    assert depends["depends_on"] == ["resource_role"]
    refused = mockwitness.fixture("estimate_line_category_mismatch")
    assert refused["fields"] == [
        {"pointer": "/estimate_line/cost_category_id", "code": "COMPUTED_VALUE"}
    ]


@pytest.mark.requirement("WF-DEV-0020-A")
def test_a_line_created_without_a_label_is_labelled_by_its_task_and_its_role() -> None:
    # « À la création d'une ligne, Waterfall compose son libellé à partir de celui de la tâche qui
    # la porte et, s'il existe, de celui de son rôle de ressource ; ce libellé reste modifiable. »
    [line] = mockwitness.fixture("estimate_line_created_labelled")["nodes"]
    facet_ = cast("dict[str, Any]", line["estimate_line"])
    assert facet_["label"] == "Mise en service — Technicien de mise en service"
    assert "estimate_line.label" in line["editable_fields"]
    assert facet_["cost_category_label"] == "Mise en service"
    assert line["computed_fields"] == ["estimate_line.cost_category_id"]


@pytest.mark.requirement("WF-RAE-0010-A")
def test_a_line_of_provision_takes_no_reestimate(readings: dict[str, Any]) -> None:
    provision = facet(nodes(readings["nodes_estimate.json"])[PROVISION])
    assert provision["remaining_entry"] == {
        "is_available": False,
        "missing_conditions": ["line_not_provision"],
    }
    refused = mockwitness.fixture("remaining_provision_refused")
    assert refused["params"] == {"missing_condition": "line_not_provision"}


@pytest.mark.requirement("WF-PLA-0040-A")
def test_the_mode_of_a_summary_is_computed_never_entered(readings: dict[str, Any]) -> None:
    # « Une tâche récapitulative est toujours en mode automatique ; son mode n'est pas
    # saisissable. »
    for node in readings["nodes_planning.json"]["items"]:
        task = facet(node)
        if task["is_summary"]:
            assert task["scheduling_mode"] == "automatic"
            assert "task.scheduling_mode" in node["computed_fields"]
            assert "task.scheduling_mode" not in node["editable_fields"]


@pytest.mark.requirement("WF-IHM-0130-A")
def test_a_bound_of_a_column_of_a_line_retains_the_lines_within_it() -> None:
    # « Toute table se filtre sur chacune de ses colonnes, et le filtre s'applique aux totaux
    # qu'elle présente. »
    reading = mockwitness.fixture("nodes_estimate_filtered")
    items = cast("list[dict[str, Any]]", reading["items"])
    lines = [item["estimate_line"] for item in items if item["kind"] == mockcore.ESTIMATE_LINE]
    amounts = [Decimal(line["reestimated_amount"]) for line in lines]
    assert amounts
    assert all(Decimal(1000) <= amount <= Decimal(10_000) for amount in amounts)
    assert Decimal(reading["totals"]["reestimated_amount"]) == sum(amounts)
    assert reading["totals"]["task_count"] == 0


@pytest.mark.requirement("WF-PLA-0040-A")
def test_deleting_the_only_subordinate_of_a_summary_leaves_a_leaf_of_its_duration() -> None:
    # « La suppression de la seule subordonnée d'une récapitulative de dix jours laisse une tâche
    # feuille de dix jours » : the witness has no summary of ten days with one subordinate; the
    # one of a day its creation example makes (node_created_child) stands for it.
    summary_id = mockids.universe(mockgestures.CREATED)
    created = mockwitness.fixture("node_created_child")["ancestors"]
    summary = {node["node_id"]: node["task"] for node in created}[summary_id]
    assert summary["is_summary"] is True
    emptied = mockwitness.fixture("node_summary_emptied")
    assert emptied["nodes"] == []
    leaf_node = {node["node_id"]: node for node in emptied["ancestors"]}[summary_id]
    leaf = leaf_node["task"]
    assert leaf["is_summary"] is False
    assert leaf["scheduling_mode"] == "automatic"
    assert leaf["duration"] == summary["duration"]
    assert (leaf["start"], leaf["finish"]) == (summary["start"], summary["finish"])
    assert "task.duration" in leaf_node["editable_fields"]
    assert "task.duration" not in leaf_node["computed_fields"]
    assert emptied["structure_lock_version"] == 4
