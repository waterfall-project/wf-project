# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the Kanban of the witness: the gestures of its cards, and what they answer (US-0540).

They try the simplifications of the fake back against the readings of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
from typing import Any, cast

import pytest

from wftools import mockcore, mockdata, mockkanban, mockwitness
from wftools.mockcore import READ_ON
from wftools.mockids import universe
from wftools.mockstructure import described
from wftools.mockwitness import N
from wftools.mockwrites import amended, on_task

type Node = dict[str, Any]

SENT = {"start": "started", "complete": "completed", "enter_remaining": None}
"""The progress each gesture sends, but the reopening, which depends on the nature of the task."""


@pytest.fixture(scope="module")
def examples() -> dict[str, Any]:
    """Read the examples of the gestures back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mockkanban.examples().items()
    }


@pytest.fixture(scope="module")
def cards() -> dict[str, Node]:
    """Return every card of the Kanban of the witness today, by its node."""
    answer = mockkanban.kanban(mockcore.current())
    return {
        card["node_id"]: card
        for column in ("not_started", "started", "completed")
        for card in cast("list[Node]", answer[column])
    }


def _gestures(card: Node) -> list[tuple[str, bool, list[str], str | None]]:
    return [
        (each["command"], each["is_available"], each["missing_conditions"], each["progress"])
        for each in card["available_commands"]
    ]


def test_the_cards_of_the_core_list_the_gestures_their_state_and_their_lines_admit(
    cards: dict[str, Node],
) -> None:
    # A milestone without a line completes without starting; a task not started starts, and
    # completes only by its remaining; a task started without a line completes; one started
    # with lines but its provision line completes by its remaining; a completed task reopens to
    # started, a completed milestone to not started.
    def of(number: int) -> list[tuple[str, bool, list[str], str | None]]:
        return _gestures(cards[universe(number)])

    assert of(N.FACTORY_ACCEPTANCE) == [("complete", True, [], "completed")]
    none: list[str] = []
    remaining = ("enter_remaining", True, none, None)
    held = ("complete", False, ["task_is_milestone", "task_without_lines"], "completed")
    assert of(N.MOUNTING) == [("start", True, [], "started"), held, remaining]
    assert of(N.DESKS) == [("complete", True, [], "completed")]
    assert of(N.WIRING) == [("complete", False, ["task_without_lines"], "completed"), remaining]
    assert of(N.DETAILED_STUDIES) == [("reopen", True, [], "started")]
    assert of(N.STUDIES_RECEIVED) == [("reopen", True, [], "not_started")]


def test_every_card_lists_its_gestures_in_order_each_with_the_progress_it_sends(
    cards: dict[str, Node],
) -> None:
    order = ["start", "complete", "reopen", "enter_remaining"]
    for card in cards.values():
        task, gestures = card["task"], _gestures(card)
        names = [name for name, *_ in gestures]
        assert names == sorted(names, key=order.index)
        assert ("start" in names) == (
            task["progress"] == "not_started" and not task["is_milestone"]
        )
        assert ("reopen" in names) == (task["progress"] == "completed")
        assert ("complete" in names) == (task["progress"] != "completed")
        for name, available, missing, sent in gestures:
            assert available == (not missing)
            reopened = "not_started" if task["is_milestone"] else "started"
            assert sent == (reopened if name == "reopen" else SENT[name])


def test_a_provision_line_holds_no_task_from_completing_from_the_kanban() -> None:
    # The wiring bears its labour, its terminal blocks and the provision of the risk 751: without
    # the two first, the provision alone does not send it to its remaining (WF-PLA-0050).
    def provision_only(line: mockwitness.Line) -> mockwitness.Line | None:
        return None if line.number in {N.LABOUR, N.BLOCKS} else line

    roots = amended(mockwitness.CORE, line=provision_only)
    answer = mockkanban.kanban(mockcore.current(described(roots)))
    started = cast("list[Node]", answer["started"])
    [card] = [each for each in started if each["node_id"] == universe(N.WIRING)]
    assert _gestures(card) == [("complete", True, [], "completed")]


def test_a_started_task_is_one_version_further_than_its_predecessors_left_it(
    examples: dict[str, Any],
) -> None:
    # #421: the mounting, written by predecessor_set, is started one version further; the day of
    # the gesture is its date of start, its dates do not move, and its summary is started with it.
    [linked] = mockwitness.fixture("predecessor_set")["nodes"]
    [started] = examples["task_started"]["nodes"]
    assert started["node_id"] == linked["node_id"] == universe(N.MOUNTING)
    assert started["lock_version"] == linked["lock_version"] + 1
    assert started["task"]["progress"] == "started"
    assert started["task"]["started_on"] == READ_ON.isoformat()
    assert {key: started["task"][key] for key in ("start", "finish")} == {
        key: linked["task"][key] for key in ("start", "finish")
    }
    [installation] = examples["task_started"]["ancestors"]
    assert installation["task"]["progress"] == "started"


def test_the_lines_of_a_task_started_change_their_editable_fields_the_answer_rendering_none(
    examples: dict[str, Any],
) -> None:
    # #1154: the lines of the mounting, on the control station charged with actual costs, no
    # longer name their subproject among the fields they accept once their task is started; the
    # answer does not render them, and the grid reads them again.
    before = {row.number: row for row in mockcore.current(described(mockkanban.linked()))}
    gesture = on_task(N.MOUNTING, progress="started", declared_on=READ_ON)
    roots = amended(mockkanban.linked(), gesture)
    after = {row.number: row for row in mockcore.current(described(roots))}
    lines = [
        number
        for number, row in before.items()
        if row.parent == N.MOUNTING and row.kind == mockcore.ESTIMATE_LINE
    ]
    assert lines == [N.WIRING_ON_SITE, N.TESTS_LINE]
    for number in lines:
        was = cast("list[str]", before[number].node["editable_fields"])
        now = cast("list[str]", after[number].node["editable_fields"])
        assert "estimate_line.subproject_id" in was
        assert "estimate_line.subproject_id" not in now
    rendered = {node["node_id"] for node in examples["task_started"]["nodes"]}
    assert rendered == {universe(N.MOUNTING)}


def test_a_milestone_completes_at_the_date_entered_without_starting(
    examples: dict[str, Any],
) -> None:
    [attached] = mockwitness.fixture("task_attached")["nodes"]
    [completed] = examples["milestone_completed"]["nodes"]
    assert completed["lock_version"] == attached["lock_version"] + 1
    assert completed["task"]["progress"] == "completed"
    assert completed["task"]["completed_on"] == READ_ON.isoformat()
    assert "started_on" not in completed["task"]
    assert completed["task"]["finish"] == attached["task"]["finish"]
    assert completed["task"]["order_item_id"] == attached["task"]["order_item_id"]


def test_a_reopening_sends_what_the_card_says_and_erases_the_date_of_completion(
    examples: dict[str, Any], cards: dict[str, Node]
) -> None:
    # The task reopens to started, the milestone to not started, as their cards say.
    reopened = (("task_reopened", N.DETAILED_STUDIES), ("milestone_reopened", N.STUDIES_RECEIVED))
    for name, number in reopened:
        [node] = examples[name]["nodes"]
        [(_, _, _, sent)] = _gestures(cards[universe(number)])
        assert node["node_id"] == universe(number)
        assert node["lock_version"] == cards[universe(number)]["lock_version"] + 1
        assert node["task"]["progress"] == sent
        assert "completed_on" not in node["task"]


def test_a_task_but_a_completed_milestone_is_refused_back_to_not_started(
    examples: dict[str, Any], cards: dict[str, Node]
) -> None:
    refused = examples["task_reopen_not_started_refused"]
    assert refused["status"] == 409
    assert refused["code"] == "STATE_FORBIDS_OPERATION"
    assert refused["params"] == {"missing_condition": "completed_milestone"}
    # The detailed studies its summary names are completed, and no milestone.
    task = cards[universe(N.DETAILED_STUDIES)]["task"]
    assert (task["progress"], task["is_milestone"]) == ("completed", False)
