# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own lines that hold a task open: the summary task, the leaf it becomes.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1590/L1 writes its tests here ("Les tests du back"): on the main structure of the current
revision of a project In progress, its reference written, marked and designated through the service
(``remaining_support``), a summary whose subordinates are all completed stays started and signalled
(``awaiting_own_lines``, #1775) while an own line besides the provisions keeps a remaining to
commit, the entry that sets the last to nought completes it at the latest date, and the leaf it
becomes stays started; the gestures of a card (``progress_commands``) name what ``setTaskProgress``
refuses, and the task a remaining set to nought completes goes straight to completed. Every answer
is checked against the contract.
"""

from annotationlib import Format, get_annotations
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Literal, TypeAliasType, get_args, get_origin
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, costing
from history_support import delete, redone, undone
from nodes_support import Tree, entries, faults, refusal, signed_in
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, task_named
from sqlalchemy import select, update

import waterfall.core.estimate.interface as estimate_interface
from waterfall.api.contract.models import CommandCondition
from waterfall.api.contract.models import KanbanCommand as ContractCommand
from waterfall.api.contract.models import TaskProgress as ContractProgress
from waterfall.core.estimate.interface import KanbanTask
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import (
    KanbanCommand,
    KanbanCommandAvailability,
    KanbanCondition,
    NodeFilters,
    Place,
    TaskProgress,
    list_nodes,
    progress_commands,
)
from waterfall.core.planning.tables import Task
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.core.planning.interface import TaskView
    from waterfall.platform.database import Database

MILESTONE = {"duration": {"value": "0", "unit": "d"}}
BASIS = "reestimated_amount_basis"
TUESDAY = DAY + timedelta(days=1)
FRIDAY = DAY + timedelta(days=4)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name."""
    return costing(stage.database)


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give the project In progress, its tasks and their lines.

    The phase, its own line of steering at 500 over its study; the batch, its own line of
    acceptance at 500 over its one milestone; the hazards, a provision of 40 over its trial; the
    delivery, a milestone and its instalment at 10; the assembly and its fixings at 50; the
    validation, a milestone without a line.
    """

    def build(tree: Tree, lines: Lines) -> None:
        phase = tree.made("Phase")
        lines.made(phase, **material(costs, "Pilotage", "500"))
        tree.made("Étude", parent_id=phase["node_id"])
        batch = tree.made("Lot")
        lines.made(batch, **material(costs, "Recette", "500"))
        tree.made("Jalon", parent_id=batch["node_id"], task=MILESTONE)
        hazards = tree.made("Aléas")
        lines.made(hazards, **material(costs, "Provision", "40"))
        tree.made("Essai", parent_id=hazards["node_id"])
        delivery = tree.made("Livraison", task=MILESTONE)
        lines.made(delivery, **material(costs, "Acompte", "10"))
        assembly = tree.made("Montage")
        lines.made(assembly, **material(costs, "Fixations", "50"))
        tree.made("Validation", task=MILESTONE)

    held = in_progress(api, stage, build)
    # A provision line is the risks' (EP-08): its category of the provision kind, put around the
    # service, is what the question asked of the lines leaves out.
    provision = line_named(held.tree, "Provision")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(provision["node_id"]))
            .values(cost_category_id=costs.provision)
        )
    return held


def material(costs: Costing, label: str, amount: str) -> dict[str, Any]:
    """Give a line of material: one at the amount said."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def gesture(tree: Tree, label: str, state: str, who: Any = None, **body: Any) -> Any:
    """Send the state of the card of a task at the counter read; give the answer."""
    node = task_named(tree, label)
    sent = {"progress": state, "lock_version": node["lock_version"], **body}
    path = f"{tree.path}/nodes/{node['node_id']}/progress"
    return tree.api.put(path, headers=(who or tree.stage.manager).headers, json=sent)


def moved(tree: Tree, label: str, state: str, on: Any) -> dict[str, Any]:
    """Send a gesture that must be accepted, on the day said; give what is answered."""
    answer = gesture(tree, label, state, occurred_on=on.isoformat())
    assert answer.status_code == 200, answer.text
    return answer.json()


def zero(tree: Tree, label: str, who: Any = None, **body: Any) -> Any:
    """Set the line of a label to nought, its quantity at 0; give the answer."""
    line = line_named(tree, label)
    sent = {"lock_version": line["lock_version"], BASIS: {"quantity": "0"}, **body}
    headers = (who or tree.stage.manager).headers
    return tree.api.put(
        f"{tree.path}/nodes/{line['node_id']}/remaining", headers=headers, json=sent
    )


def done(tree: Tree, label: str) -> None:
    """Start then complete a leaf without a line, from the Kanban, on Monday then Tuesday."""
    moved(tree, label, "started", DAY)
    moved(tree, label, "completed", TUESDAY)


def state(node: dict[str, Any]) -> tuple[str, str | None, str | None, bool]:
    """Give the state of a task, its two dates and whether it awaits only its own lines."""
    task = node["task"]
    return task["progress"], task["started_on"], task["completed_on"], task["awaiting_own_lines"]


def views(tree: Tree) -> dict[str, TaskView]:
    """Read the tasks of the structure by the interface of the planning, by their label."""
    stage = tree.stage
    place = Place(
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
    )
    with stage.database.transaction() as session:
        read = list_nodes(session, place, NodeFilters())
    return {item.task.label: item.task for item in read.items if item.task is not None}


def card(tree: Tree, label: str, *, bears_lines: bool) -> list[tuple[str, str | None, list[str]]]:
    """Give the gestures of the card of a task: each, the state it sends, what it lacks."""
    return [
        (each.command, each.progress, list(each.missing_conditions))
        for each in progress_commands(views(tree)[label], bears_lines=bears_lines)
    ]


def missing(answer: Any) -> str:
    """Give the condition a refusal of 409 names, after checking its code."""
    status, code, params = refusal(answer)
    assert (status, code) == (409, "STATE_FORBIDS_OPERATION"), answer.text
    return params["missing_condition"]


def counter(tree: Tree) -> int:
    """Read the counter of the structure, which every write of its tree advances."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


# --- The summary its own lines hold open --------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_done_below_whose_own_line_keeps_500_is_started_and_signalled(
    review: Review,
) -> None:
    # « Une récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre
    # porte un reste à engager de 500 est démarrée et signalée » (#1775): in the ancestors the
    # completion of its last subordinate gives back, and at the reading; its line stays open.
    tree = review.tree
    moved(tree, "Étude", "started", DAY)
    answer = moved(tree, "Étude", "completed", TUESDAY)
    [phase] = answer["ancestors"]
    assert state(phase) == ("started", DAY.isoformat(), None, True)
    assert state(task_named(tree, "Phase")) == ("started", DAY.isoformat(), None, True)
    line = line_named(tree, "Pilotage")["estimate_line"]
    assert line["reestimated_amount"] == "500.00"
    assert line["remaining_entry"] == {"is_available": True, "missing_conditions": []}
    # The filters read the state the reading derives: the summary is among the started.
    started = tree.items("?progress=started")
    assert "Phase" in [each["task"]["label"] for each in started if each["kind"] == "task"]
    # Its card offers the entry of its remaining, and no completion: neither start nor reopen.
    assert card(tree, "Phase", bears_lines=True) == [
        ("complete", "completed", ["task_without_lines"]),
        ("enter_remaining", None, []),
    ]


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_the_last_own_line_set_to_nought_completes_the_summary_and_puts_out_its_signal(
    review: Review,
) -> None:
    # « … la saisie d'un reste nul sur cette ligne la termine. » At the date sent, asked for as a
    # leaf's is, never before the start of the summary, the first of its subordinates'; the latest
    # of that date and of its subordinates' completions is its own (WF-PLA-0130).
    tree = review.tree
    done(tree, "Étude")
    phase = task_named(tree, "Phase")
    line = line_named(tree, "Pilotage")
    assert faults(zero(tree, "Pilotage")) == [
        ("/completed_on", "COMPLETION_DATE_REQUIRED", {"task_node_id": phase["node_id"]})
    ]
    early = zero(tree, "Pilotage", completed_on=(DAY - timedelta(days=1)).isoformat())
    assert faults(early) == [("/completed_on", "VALUE_OUT_OF_RANGE", {"minimum": DAY.isoformat()})]
    assert line_named(tree, "Pilotage") == line
    answer = zero(tree, "Pilotage", completed_on=FRIDAY.isoformat())
    assert answer.status_code == 200, answer.text
    task, written = answer.json()["nodes"]
    assert (task["node_id"], written["node_id"]) == (phase["node_id"], line["node_id"])
    assert state(task) == ("completed", DAY.isoformat(), FRIDAY.isoformat(), False)
    assert task["lock_version"] == phase["lock_version"] + 1
    assert state(task_named(tree, "Phase")) == state(task)
    assert line_named(tree, "Pilotage")["estimate_line"]["remaining_entry"] == {
        "is_available": False,
        "missing_conditions": ["task_not_completed"],
    }


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_summary_set_to_nought_dated_before_its_last_subordinate_takes_the_later_date(
    review: Review,
) -> None:
    # « … pour date de terminaison la plus tardive de celles de ses subordonnées et de la mise à
    # zéro de ses lignes propres. » The subordinate completed on Tuesday, then the line set to
    # nought, dated Monday, before it: the summary is completed on the later, Tuesday.
    tree = review.tree
    done(tree, "Étude")
    answer = zero(tree, "Pilotage", completed_on=DAY.isoformat())
    assert answer.status_code == 200, answer.text
    task, _ = answer.json()["nodes"]
    assert state(task) == ("completed", DAY.isoformat(), TUESDAY.isoformat(), False)


@pytest.mark.requirement("WF-PLA-0040-A")
def test_own_lines_set_to_nought_first_let_the_last_subordinate_complete_the_summary(
    review: Review,
) -> None:
    # « … elle n'est terminée qu'après la dernière. » The own line set to nought while a
    # subordinate is open completes nothing and asks for no date; the subordinate completed then
    # completes the summary, which nothing holds any more.
    tree = review.tree
    moved(tree, "Étude", "started", DAY)
    answer = zero(tree, "Pilotage")
    assert answer.status_code == 200, answer.text
    assert [node["kind"] for node in answer.json()["nodes"]] == ["estimate_line"]
    assert state(task_named(tree, "Phase")) == ("started", DAY.isoformat(), None, False)
    [phase] = moved(tree, "Étude", "completed", TUESDAY)["ancestors"]
    assert state(phase) == ("completed", DAY.isoformat(), TUESDAY.isoformat(), False)


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_whose_only_own_line_is_a_provision_is_completed_and_not_signalled(
    review: Review,
) -> None:
    # « Une récapitulative dont toutes les subordonnées sont terminées et dont la seule ligne propre
    # est une provision de 40 est terminée et n'est pas signalée. » The provision is EP-08's, which
    # closes the criterion; here, the question asked of the lines leaves it out.
    tree = review.tree
    moved(tree, "Essai", "started", DAY)
    [hazards] = moved(tree, "Essai", "completed", TUESDAY)["ancestors"]
    assert state(hazards) == ("completed", DAY.isoformat(), TUESDAY.isoformat(), False)
    assert line_named(tree, "Provision")["estimate_line"]["reestimated_amount"] == "40.00"


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_completion_of_a_summary_by_its_line_is_undone_whole_and_signals_it_again(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    tree = review.tree
    writer = signed_in(stage, realm)
    done(tree, "Étude")
    phase = task_named(tree, "Phase")
    answer = zero(tree, "Pilotage", writer, completed_on=FRIDAY.isoformat())
    assert answer.status_code == 200, answer.text
    whole = entries(stage)[-1]
    assert whole.node_ids == [UUID(line_named(tree, "Pilotage")["node_id"]), UUID(phase["node_id"])]
    undone(tree, writer)
    assert state(task_named(tree, "Phase")) == ("started", DAY.isoformat(), None, True)
    assert line_named(tree, "Pilotage")["estimate_line"]["reestimated_amount"] == "500.00"


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_summary_closed_by_its_line_then_reopened_below_loses_the_day_it_was_closed_at(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    # « … pour date de terminaison la plus tardive de celles de ses subordonnées et de la mise à
    # zéro de ses lignes propres. » Closed on Friday by its line, a subordinate reopened then
    # completed on Tuesday again: the Friday is stale, the summary is completed on Tuesday. The
    # reopening is one entry of the history with the summary above: undone, the summary is
    # completed again on its Friday; redone, it is started again and the Friday is gone (#2768).
    tree = review.tree
    writer = signed_in(stage, realm)
    done(tree, "Étude")
    answer = zero(tree, "Pilotage", completed_on=FRIDAY.isoformat())
    assert answer.status_code == 200, answer.text
    closed = ("completed", DAY.isoformat(), FRIDAY.isoformat(), False)
    assert state(task_named(tree, "Phase")) == closed
    reopening = gesture(tree, "Étude", "started", writer, occurred_on=DAY.isoformat())
    assert reopening.status_code == 200, reopening.text
    [reopened] = reopening.json()["ancestors"]
    stale = ("started", DAY.isoformat(), None, False)
    assert state(reopened) == stale
    undone(tree, writer)
    assert state(task_named(tree, "Phase")) == closed
    assert state(task_named(tree, "Étude"))[0] == "completed"
    redone(tree, writer)
    assert state(task_named(tree, "Phase")) == stale
    assert state(task_named(tree, "Étude"))[0] == "started"
    [again] = moved(tree, "Étude", "completed", TUESDAY)["ancestors"]
    assert state(again) == ("completed", DAY.isoformat(), TUESDAY.isoformat(), False)
    assert state(task_named(tree, "Phase")) == state(again)


def kept(stage: Scene, tree: Tree, label: str) -> tuple[str, str | None]:
    """Read what the facet of a task keeps of its state, as the base holds it: state and day."""
    node_id = UUID(task_named(tree, label)["node_id"])
    with stage.database.transaction() as session:
        row = session.execute(
            select(Task.progress, Task.completed_on).where(Task.node_id == node_id)
        ).one()
    return row.progress, None if row.completed_on is None else row.completed_on.isoformat()


@pytest.fixture
def closed_phase(review: Review, stage: Scene) -> Review:
    """Give the phase completed by its own line on Friday, its study done on Tuesday."""
    tree = review.tree
    done(tree, "Étude")
    answer = zero(tree, "Pilotage", completed_on=FRIDAY.isoformat())
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        FRIDAY.isoformat(),
        False,
    )
    assert kept(stage, tree, "Phase") == ("completed", FRIDAY.isoformat())
    return review


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_created_under_a_summary_closed_by_its_line_reopens_it_and_clears_the_day(
    closed_phase: Review, stage: Scene, realm: TestRealm
) -> None:
    # « … elle n'est terminée qu'après la dernière » : a subordinate created under the phase
    # completed by its line leaves it started, and the facet keeps no state and no day of the
    # closure (#2769); the new one completed on Tuesday completes it then, not on the stale
    # Friday. The creation is undone whole — the phase is closed on Friday again —, then redone.
    tree = closed_phase.tree
    writer = signed_in(stage, realm)
    phase = task_named(tree, "Phase")
    created = tree.create("Contrôle", writer, parent_id=phase["node_id"])
    assert created.status_code == 201, created.text
    [above] = created.json()["ancestors"]
    assert state(above) == ("started", DAY.isoformat(), None, False)
    assert kept(stage, tree, "Phase") == ("started", None)
    undone(tree, writer)
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        FRIDAY.isoformat(),
        False,
    )
    assert kept(stage, tree, "Phase") == ("completed", FRIDAY.isoformat())
    redone(tree, writer)
    assert kept(stage, tree, "Phase") == ("started", None)
    done(tree, "Contrôle")
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        TUESDAY.isoformat(),
        False,
    )


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_created_under_a_summary_closed_by_its_subordinates_alone_reopens_it(
    review: Review, stage: Scene
) -> None:
    # The hazards, whose only own line is a provision, are completed by their trial alone: nothing
    # of a closure is kept on their facet, and a task created under them leaves them started.
    tree = review.tree
    done(tree, "Essai")
    assert state(task_named(tree, "Aléas"))[0] == "completed"
    assert kept(stage, tree, "Aléas") == ("not_started", None)
    hazards = task_named(tree, "Aléas")
    created = tree.create("Relevé", parent_id=hazards["node_id"])
    assert created.status_code == 201, created.text
    assert state(task_named(tree, "Aléas")) == ("started", DAY.isoformat(), None, False)
    assert kept(stage, tree, "Aléas") == ("not_started", None)


def moved_under(tree: Tree, label: str, parent: str, who: Any = None) -> Any:
    """Move a task under another, after its last subordinate; give the answer."""
    sent = {
        "node_ids": [task_named(tree, label)["node_id"]],
        "parent_id": task_named(tree, parent)["node_id"],
        "lock_version": counter(tree),
    }
    headers = (who or tree.stage.manager).headers
    return tree.api.post(f"{tree.path}/nodes/move", headers=headers, json=sent)


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_moved_under_a_summary_closed_by_its_line_reopens_it_and_clears_the_day(
    closed_phase: Review, stage: Scene, realm: TestRealm
) -> None:
    # A task not completed moved under the phase completed by its line: as a task created there,
    # it leaves the phase started and the facet without a closure; the move is undone whole, then
    # redone, and the task completed on Tuesday completes the phase then, not on the stale Friday.
    tree = closed_phase.tree
    writer = signed_in(stage, realm)
    answer = moved_under(tree, "Montage", "Phase", writer)
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == ("started", DAY.isoformat(), None, False)
    assert kept(stage, tree, "Phase") == ("started", None)
    undone(tree, writer)
    assert kept(stage, tree, "Phase") == ("completed", FRIDAY.isoformat())
    assert task_named(tree, "Montage")["parent_id"] is None
    redone(tree, writer)
    assert kept(stage, tree, "Phase") == ("started", None)
    zero(tree, "Fixations", completed_on=TUESDAY.isoformat())
    assert state(task_named(tree, "Phase"))[1:3] == (DAY.isoformat(), TUESDAY.isoformat())


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_completed_moved_under_a_summary_closed_by_its_line_leaves_it_closed(
    closed_phase: Review, stage: Scene
) -> None:
    # Only a task not completed reopens the summary: the milestone completed on Tuesday by its
    # remaining, moved under the phase, leaves it completed on its Friday.
    tree = closed_phase.tree
    zero(tree, "Acompte", completed_on=TUESDAY.isoformat())
    answer = moved_under(tree, "Livraison", "Phase")
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        FRIDAY.isoformat(),
        False,
    )
    assert kept(stage, tree, "Phase") == ("completed", FRIDAY.isoformat())


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_subordinate_deleted_under_a_summary_that_was_closed_reads_the_zeroing_of_its_line(
    closed_phase: Review, stage: Scene, realm: TestRealm
) -> None:
    # « … pour date de terminaison la plus tardive de celles de ses subordonnées et de la mise à
    # zéro de ses lignes propres » : the phase closed by its line, a subordinate created under it
    # (which clears the day, #2769) then deleted, the phase is completed again by its study and its
    # line, on the day of the zeroing read on the line (``reestimated_at``, option B of #2803),
    # later than the study's Tuesday — the day of the entry, not the Friday it declared, which the
    # reopening cleared. The deletion is undone (the phase is started again), then redone.
    tree = closed_phase.tree
    writer = signed_in(stage, realm)
    phase = task_named(tree, "Phase")
    zeroed = zeroing_day(stage, tree, "Pilotage")
    assert zeroed > TUESDAY
    created = tree.create("Contrôle", parent_id=phase["node_id"])
    assert created.status_code == 201, created.text
    assert kept(stage, tree, "Phase") == ("started", None)
    node = task_named(tree, "Contrôle")
    answer = delete(tree, node, writer)
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        zeroed.isoformat(),
        False,
    )
    assert kept(stage, tree, "Phase") == ("completed", zeroed.isoformat())
    undone(tree, writer)
    assert state(task_named(tree, "Phase")) == ("started", DAY.isoformat(), None, False)
    assert kept(stage, tree, "Phase") == ("started", None)
    redone(tree, writer)
    assert state(task_named(tree, "Phase"))[1:3] == (DAY.isoformat(), zeroed.isoformat())
    assert kept(stage, tree, "Phase") == ("completed", zeroed.isoformat())


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_subordinate_deleted_under_a_started_summary_takes_the_later_of_done_and_zeroing(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    # « … pour date de terminaison la plus tardive de celles de ses subordonnées et de la mise à
    # zéro de ses lignes propres. » The phase never closed: its study done on Tuesday, a second
    # subordinate open, its own line set to nought afterwards (nothing completes it, a subordinate
    # is open). Deleting the open one completes the phase on the later of the two, the day of the
    # zeroing (``reestimated_at``), not on the study's Tuesday.
    tree = review.tree
    writer = signed_in(stage, realm)
    done(tree, "Étude")
    phase = task_named(tree, "Phase")
    created = tree.create("Contrôle", parent_id=phase["node_id"])
    assert created.status_code == 201, created.text
    answer = zero(tree, "Pilotage")
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase"))[0] == "started"
    zeroed = zeroing_day(stage, tree, "Pilotage")
    assert zeroed > TUESDAY
    answer = delete(tree, task_named(tree, "Contrôle"), writer)
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        zeroed.isoformat(),
        False,
    )


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_subordinate_moved_out_of_a_summary_that_was_closed_reads_the_zeroing_of_its_line(
    closed_phase: Review, stage: Scene, realm: TestRealm
) -> None:
    # The same path by a move: the assembly, not started, moved under the phase reopens it; moved
    # back to the first level, it leaves the phase completed by its study and its line, on the day
    # of the zeroing read on the line (option B of #2803). Undone, the phase is started again.
    tree = closed_phase.tree
    writer = signed_in(stage, realm)
    zeroed = zeroing_day(stage, tree, "Pilotage")
    answer = moved_under(tree, "Montage", "Phase", writer)
    assert answer.status_code == 200, answer.text
    assert kept(stage, tree, "Phase") == ("started", None)
    assembly = task_named(tree, "Montage")
    sent = {"node_ids": [assembly["node_id"]], "parent_id": None, "lock_version": counter(tree)}
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=writer.headers, json=sent)
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == (
        "completed",
        DAY.isoformat(),
        zeroed.isoformat(),
        False,
    )
    assert kept(stage, tree, "Phase") == ("completed", zeroed.isoformat())
    undone(tree, writer)
    assert kept(stage, tree, "Phase") == ("started", None)


@pytest.mark.requirement("WF-PLA-0040-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_subordinate_deleted_under_a_summary_whose_line_keeps_a_remaining_leaves_it_held(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    # The line of the phase never set to nought: its study done, the phase awaits its line; a
    # subordinate created then deleted leaves it so, started, its facet untouched.
    tree = review.tree
    writer = signed_in(stage, realm)
    done(tree, "Étude")
    phase = task_named(tree, "Phase")
    created = tree.create("Contrôle", parent_id=phase["node_id"])
    assert created.status_code == 201, created.text
    answer = delete(tree, task_named(tree, "Contrôle"), writer)
    assert answer.status_code == 200, answer.text
    assert state(task_named(tree, "Phase")) == ("started", DAY.isoformat(), None, True)
    assert kept(stage, tree, "Phase")[1] is None


def zeroing_day(stage: Scene, tree: Tree, label: str) -> date:
    """Read the day a line of a label was last re-estimated, as the base holds it."""
    node_id = UUID(line_named(tree, label)["node_id"])
    with stage.database.transaction() as session:
        instant = session.scalar(
            select(EstimateLine.reestimated_at).where(EstimateLine.node_id == node_id)
        )
    assert instant is not None
    return instant.date()


@pytest.fixture
def held_phase(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give a project In progress whose phase is held open by its line, its only subtask done.

    The phase bears its own line of steering at 500 and its subtask, the last node of the structure.
    """

    def build(tree: Tree, lines: Lines) -> None:
        phase = tree.made("Phase")
        lines.made(phase, **material(costs, "Pilotage", "500"))
        tree.made("Étude", parent_id=phase["node_id"])

    held = in_progress(api, stage, build)
    done(held.tree, "Étude")
    assert state(task_named(held.tree, "Phase")) == ("started", DAY.isoformat(), None, True)
    return held


def pasted(tree: Tree, target: dict[str, Any], rows: list[list[str]]) -> dict[str, Any]:
    """Preview then confirm a block pasted from the label of a node; give what is answered."""
    headers = tree.stage.manager.headers
    sent = {"target_node_id": target["node_id"], "target_column": "label", "rows": rows}
    previewed = tree.api.post(f"{tree.path}/nodes/paste-preview", headers=headers, json=sent)
    assert previewed.status_code == 200, previewed.text
    plan = previewed.json()
    assert plan["rejected"] == [], plan
    confirmed = {"paste_id": plan["paste_id"], "confirmed": True, "lock_version": counter(tree)}
    answer = tree.api.post(f"{tree.path}/nodes/paste", headers=headers, json=confirmed)
    assert answer.status_code == 200, answer.text
    assert answer.json()["rejected"] == []
    return plan


@pytest.mark.requirement("WF-PLA-0040-A")
def test_two_lines_pasted_under_a_summary_held_open_by_its_line_are_both_accepted(
    held_phase: Review,
) -> None:
    # « … est démarrée » : the summary is not completed, so a line is accepted under it on the
    # main structure; the second row is judged on the ground the first leaves, which keeps the
    # summaries the tree holds open (``Tree.held``) as the first did.
    tree = held_phase.tree
    rows = [
        ["Pilotage"],
        ["Étude"],
        ["Suivi", "Matériel électrique", "", "1", "", "10"],
        ["Revue", "Matériel électrique", "", "1", "", "10"],
    ]
    plan = pasted(tree, line_named(tree, "Pilotage"), rows)
    assert (plan["accepted"], plan["created"]) == (4, 2)
    lines = [each for each in tree.items() if each["kind"] == "estimate_line"]
    assert [each["estimate_line"]["label"] for each in lines] == ["Pilotage", "Suivi", "Revue"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_subtask_created_by_a_paste_under_a_summary_held_open_by_its_line_is_accepted(
    held_phase: Review,
) -> None:
    # The block is aimed at the last node, the subtask: the rows past it create tasks beside it,
    # under the summary the tree holds open. Nothing a creation judges reads ``Tree.held`` — the
    # tree a creation traces (``traced_creation``) carries it for the rows that do, the lines —,
    # so that this test holds the acceptance, and removing that carry is seen by the one above.
    tree = held_phase.tree
    plan = pasted(tree, task_named(tree, "Étude"), [["Étude"], ["Essais"]])
    assert (plan["accepted"], plan["created"]) == (2, 1)
    assert state(task_named(tree, "Phase"))[0] == "started"
    assert task_named(tree, "Essais")["parent_id"] == task_named(tree, "Phase")["node_id"]


# --- The leaf a summary becomes ------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_held_by_its_line_losing_its_milestone_is_a_started_leaf_of_a_day(
    review: Review,
) -> None:
    # « Une récapitulative dont la seule subordonnée est un jalon terminé et dont une ligne propre
    # garde un reste à engager, privée de ce jalon, est une feuille démarrée d'un jour, non un
    # jalon. » Its card goes to the started tasks without the signal, which is a summary's alone.
    tree = review.tree
    [batch] = moved(tree, "Jalon", "completed", DAY)["ancestors"]
    assert state(batch) == ("started", DAY.isoformat(), None, True)
    milestone = task_named(tree, "Jalon")
    sent = {"node_ids": [milestone["node_id"]], "parent_id": None, "lock_version": counter(tree)}
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
    [leaf] = [each for each in answer.json()["ancestors"] if each["task"]["label"] == "Lot"]
    assert state(leaf) == ("started", DAY.isoformat(), None, False)
    facet = leaf["task"]
    assert (facet["is_summary"], facet["is_milestone"]) == (False, False)
    assert facet["duration"] == {"value": "1", "unit": "d"}
    assert state(task_named(tree, "Lot")) == ("started", DAY.isoformat(), None, False)
    assert card(tree, "Lot", bears_lines=True) == [
        ("complete", "completed", ["task_without_lines"]),
        ("enter_remaining", None, []),
    ]


# --- The cards, and the completion by the remaining to commit -----------------------------------


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_milestone_bearing_a_line_is_completed_by_its_remaining_not_from_the_kanban(
    review: Review,
) -> None:
    # « Un jalon portant une ligne de devis passe de non démarré à terminé par la saisie d'un reste
    # à engager nul ; un jalon sans ligne est terminé depuis le Kanban. La terminaison depuis le
    # Kanban d'un jalon portant une ligne est refusée en renvoyant à la saisie de son reste à
    # engager. » The card and the refusal name the same condition.
    tree = review.tree
    assert card(tree, "Livraison", bears_lines=True) == [
        ("complete", "completed", ["task_without_lines"]),
        ("enter_remaining", None, []),
    ]
    assert missing(gesture(tree, "Livraison", "completed")) == "task_without_lines"
    answer = zero(tree, "Acompte", completed_on=TUESDAY.isoformat())
    assert answer.status_code == 200, answer.text
    milestone = answer.json()["nodes"][0]
    assert state(milestone) == ("completed", TUESDAY.isoformat(), TUESDAY.isoformat(), False)
    assert card(tree, "Validation", bears_lines=False) == [("complete", "completed", [])]
    validation = moved(tree, "Validation", "completed", FRIDAY)["nodes"][0]
    assert state(validation) == ("completed", FRIDAY.isoformat(), FRIDAY.isoformat(), False)
    assert card(tree, "Livraison", bears_lines=True) == [("reopen", "not_started", [])]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_task_not_started_goes_straight_to_completed_by_its_remaining_set_to_nought(
    review: Review,
) -> None:
    # « Le passage direct de non démarrée à terminée n'est possible que pour un jalon, ou par la
    # saisie d'un reste à engager nul sur toutes les lignes d'une tâche non démarrée. » The card
    # names, in the order of the refusal, what the gesture lacks; the entry completes the task,
    # started that same day.
    tree = review.tree
    assert card(tree, "Montage", bears_lines=True) == [
        ("start", "started", []),
        ("complete", "completed", ["task_is_milestone", "task_without_lines"]),
        ("enter_remaining", None, []),
    ]
    assert missing(gesture(tree, "Montage", "completed")) == "task_is_milestone"
    answer = zero(tree, "Fixations", completed_on=TUESDAY.isoformat())
    assert answer.status_code == 200, answer.text
    task = answer.json()["nodes"][0]
    assert state(task) == ("completed", TUESDAY.isoformat(), TUESDAY.isoformat(), False)
    # « Aucune commande ne fait passer une tâche démarrée à l'état non démarré » : a task reopened
    # is started again, and the card of a started task lists no gesture to not started.
    assert card(tree, "Montage", bears_lines=True) == [("reopen", "started", [])]
    moved(tree, "Étude", "started", DAY)
    assert card(tree, "Étude", bears_lines=False) == [("complete", "completed", [])]


def literals(alias: Any) -> tuple[Any, ...]:
    """Give the values of a type alias of literals, through the aliases and unions it names."""
    if isinstance(alias, TypeAliasType):
        return literals(alias.__value__)
    if get_origin(alias) is Literal:
        return get_args(alias)
    return tuple(value for member in get_args(alias) for value in literals(member))


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_gestures_of_a_card_have_one_type_the_planning_s_which_the_board_reads() -> None:
    # #2714, no criterion of its own: the card of WF-RAE-0030 names its gestures, the states they
    # send and the conditions they lack by the enumerations of the contract; the planning types
    # them once, in ``Literal``, and the board of the estimate holds no type of its own.
    assert literals(KanbanCommand) == tuple(each.value for each in ContractCommand)
    assert literals(TaskProgress) == tuple(each.value for each in ContractProgress)
    conditions = {each.value for each in CommandCondition}
    kanban = set(literals(KanbanCondition))
    assert kanban <= conditions
    assert {"project_in_progress", "no_background_task_running"} <= kanban
    annotations = get_annotations(KanbanTask, format=Format.STRING)
    assert annotations["available_commands"] == "tuple[KanbanCommandAvailability, ...]"
    assert not hasattr(estimate_interface, "KanbanCommandAvailability")
    fields = get_annotations(KanbanCommandAvailability, format=Format.STRING)
    assert fields == {
        "command": "KanbanCommand",
        "progress": "TaskProgress | None",
        "missing_conditions": "tuple[KanbanCondition, ...]",
    }
