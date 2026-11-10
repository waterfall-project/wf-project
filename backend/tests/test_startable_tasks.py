# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution, by column: the Kanban (``listStartableTasks``, US-1590/L2).

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file; US-1590/L2
writes its tests here ("Les tests du back"). The socle fixes the result EP-10 reads. On the main
structure of the current revision of a project In progress (``remaining_support``), every answer
checked against the contract: the three columns in the order of the plan, the summaries that are
no card but the one that awaits only its own lines, the gestures of each card and what each lacks,
the cards of a caller that may not write, the readings of a terminal project, and the number of
statements the reading takes, which no task changes.
"""

from annotationlib import Format, get_annotations
from dataclasses import fields
from datetime import timedelta
from itertools import product
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, costing
from history_support import link
from nodes_support import Tree, put_risk, refusal
from planning_support import DAY, give_a_task
from projects_support import PROJECTS, READING, Scene, person, put_in_state
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked, task_named
from sqlalchemy import event, update

from waterfall.core.estimate.interface import (
    KanbanTask,
    NotStartedTask,
    StartableTasks,
    startable_tasks,
)
from waterfall.core.estimate.remaining import kanban
from waterfall.core.estimate.remaining.kanban import ENTRY_CONDITIONS
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.revisions.commands import RevisionState, structure_commands_of
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import submit

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

MILESTONE = {"duration": {"value": "0", "unit": "d"}}
BASIS = "reestimated_amount_basis"
TUESDAY = DAY + timedelta(days=1)
FRIDAY = DAY + timedelta(days=4)
TERMINAL = ["completed", "lost", "abandoned"]
# The conditions, in the order of the contract, a task not started that is no milestone lacks.
NOT_STARTED = ["task_is_milestone", "task_without_lines"]
# The statements the Kanban takes, measured at 33; tight enough to catch one more a task.
BOUND = 35


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
    validation, a milestone without a line. The plan: nine tasks, three of them summaries.
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
    # A provision line is the risks' (EP-08): the line of a risk, put around the service.
    provision = line_named(held.tree, "Provision")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(provision["node_id"]))
            .values(cost_category_id=costs.provision)
        )
    put_risk(stage, provision["node_id"], UUID(int=1))
    return held


def material(costs: Costing, label: str, amount: str) -> dict[str, Any]:
    """Give a line of material: one at the amount said."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def gesture(tree: Tree, label: str, state: str, **body: Any) -> Any:
    """Send the state of the card of a task at the counter read; give the answer."""
    node = task_named(tree, label)
    sent = {"progress": state, "lock_version": node["lock_version"], **body}
    path = f"{tree.path}/nodes/{node['node_id']}/progress"
    return tree.api.put(path, headers=tree.stage.manager.headers, json=sent)


def moved(tree: Tree, label: str, state: str, on: Any) -> None:
    """Send a gesture that must be accepted, on the day said."""
    answer = gesture(tree, label, state, occurred_on=on.isoformat())
    assert answer.status_code == 200, answer.text


def zero(tree: Tree, label: str, **body: Any) -> None:
    """Set the line of a label to nought, its quantity at 0; it must be accepted."""
    line = line_named(tree, label)
    sent = {"lock_version": line["lock_version"], BASIS: {"quantity": "0"}, **body}
    path = f"{tree.path}/nodes/{line['node_id']}/remaining"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def read(tree: Tree, who: Any = None) -> Any:
    """Read the Kanban of the project of the tree, as the manager does by default."""
    headers = (who or tree.stage.manager).headers
    path = f"{PROJECTS}/{tree.stage.project['project_id']}/remaining-indicators/startable-tasks"
    return tree.api.get(path, headers=headers)


def board(tree: Tree, who: Any = None) -> dict[str, list[dict[str, Any]]]:
    """Read the Kanban, which must answer: its three columns."""
    answer = read(tree, who)
    assert answer.status_code == 200, answer.text
    columns = answer.json()
    assert list(columns) == ["not_started", "started", "completed"]
    return columns


def labels(columns: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    """Give the labels of the cards of each column, in their order."""
    return {name: [each["task"]["label"] for each in cards] for name, cards in columns.items()}


def card_of(columns: dict[str, list[dict[str, Any]]], label: str) -> dict[str, Any]:
    """Give the card of a task, in whichever column it stands."""
    return next(
        each for cards in columns.values() for each in cards if each["task"]["label"] == label
    )


def gestures(card: dict[str, Any]) -> list[tuple[str, str | None, bool, list[str]]]:
    """Give the gestures of a card: each, the state it sends, whether it is open, what it lacks."""
    return [
        (each["command"], each["progress"], each["is_available"], each["missing_conditions"])
        for each in card["available_commands"]
    ]


def missing(answer: Any) -> str:
    """Give the condition a refusal of 409 names, after checking its code."""
    status, code, params = refusal(answer)
    assert (status, code) == (409, "STATE_FORBIDS_OPERATION"), answer.text
    return params["missing_condition"]


def test_the_board_answers_three_columns_of_whole_nodes_with_their_gestures() -> None:
    # What EP-10 reads from the socle on (EP-09, "Ce que le cadrage laisse à EP-10"): the result is
    # fixed before US-1590/L2 fills it.
    assert get_annotations(startable_tasks, format=Format.FORWARDREF)["return"] is StartableTasks
    assert [field.name for field in fields(StartableTasks)] == [
        "not_started",
        "started",
        "completed",
    ]
    assert [field.name for field in fields(KanbanTask)] == ["node", "available_commands"]
    assert [field.name for field in fields(NotStartedTask)] == [
        "node",
        "available_commands",
        "predecessors_completed",
    ]


# --- The columns and the cards -------------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_kanban_divides_the_tasks_of_the_plan_in_three_columns_none_of_them_a_summary(
    review: Review,
) -> None:
    # « … propre à l'US » : the tasks of the main structure of the current revision in three
    # columns, in the order of the plan, never a summary — its state derives from its
    # subordinates'; each card the whole node, as ``listNodes`` gives it.
    tree = review.tree
    columns = board(tree)
    assert labels(columns) == {
        "not_started": ["Étude", "Jalon", "Essai", "Livraison", "Montage", "Validation"],
        "started": [],
        "completed": [],
    }
    for card in columns["not_started"]:
        whole = {
            name: value
            for name, value in card.items()
            if name not in {"available_commands", "predecessors_completed"}
        }
        assert whole == tree.node(card["node_id"])
    moved(tree, "Montage", "started", DAY)
    moved(tree, "Essai", "started", DAY)
    moved(tree, "Essai", "completed", TUESDAY)
    # The summary above the trial is completed, the one above the assembly's... is none of them.
    after = board(tree)
    assert labels(after) == {
        "not_started": ["Étude", "Jalon", "Livraison", "Validation"],
        "started": ["Montage"],
        "completed": ["Essai"],
    }
    assert card_of(after, "Essai")["task"]["completed_on"] == TUESDAY.isoformat()


@pytest.mark.requirement("WF-RAE-0030-A")
def test_each_card_lists_its_gestures_in_the_order_of_the_contract_with_what_each_lacks(
    review: Review,
) -> None:
    # « … chaque tâche avec ses available_commands dans l'ordre de KanbanCommand, les conditions
    # dans l'ordre du contrat (le geste, puis project_in_progress, no_background_task_running) » :
    # in progress and on a revision in progress, the conditions of the entry are met; a card sends
    # the state its gesture names.
    columns = board(review.tree)
    assert gestures(card_of(columns, "Étude")) == [
        ("start", "started", True, []),
        ("complete", "completed", False, ["task_is_milestone"]),
    ]
    assert gestures(card_of(columns, "Montage")) == [
        ("start", "started", True, []),
        ("complete", "completed", False, NOT_STARTED),
        ("enter_remaining", None, True, []),
    ]
    assert gestures(card_of(columns, "Validation")) == [("complete", "completed", True, [])]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_milestone_whose_predecessors_are_all_completed_is_flagged_and_nothing_completes_it(
    review: Review,
) -> None:
    # « Un jalon dont tous les prédécesseurs sont terminés est signalé et reste non démarré tant
    # que personne ne le termine. » The milestone follows the assembly: not flagged while it is
    # open, flagged once it is completed, and in the column of the tasks not started still.
    tree = review.tree
    validation = task_named(tree, "Validation")
    linked = link(tree, validation, tree.stage.manager, task_named(tree, "Montage"))
    assert linked.status_code == 200, linked.text
    columns = board(tree)
    assert [each["predecessors_completed"] for each in columns["not_started"]] == [
        True,
        True,
        True,
        True,
        True,
        False,
    ]
    zero(tree, "Fixations", completed_on=TUESDAY.isoformat())
    columns = board(tree)
    assert labels(columns)["not_started"] == ["Étude", "Jalon", "Essai", "Livraison", "Validation"]
    flagged = card_of(columns, "Validation")
    assert flagged["predecessors_completed"] is True
    assert flagged["task"]["progress"] == "not_started"
    assert gestures(flagged) == [("complete", "completed", True, [])]
    assert labels(columns)["completed"] == ["Montage"]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_no_card_of_a_task_started_lists_a_gesture_to_not_started_and_a_leaf_without_line_completes(
    review: Review,
) -> None:
    # « Aucune commande ne fait passer une tâche démarrée à l'état non démarré. » « Une tâche
    # feuille démarrée sans ligne de devis est terminée depuis le Kanban. » The cards of the
    # started tasks — a leaf, one that bears a line, the summary its line holds open — send no
    # state back to not started; the leaf without a line lists ``complete`` open.
    tree = review.tree
    moved(tree, "Étude", "started", DAY)
    moved(tree, "Étude", "completed", TUESDAY)
    moved(tree, "Montage", "started", DAY)
    moved(tree, "Essai", "started", DAY)
    columns = board(tree)
    assert labels(columns)["started"] == ["Phase", "Essai", "Montage"]
    sent = [each["progress"] for card in columns["started"] for each in card["available_commands"]]
    assert "not_started" not in sent
    assert gestures(card_of(columns, "Essai")) == [("complete", "completed", True, [])]
    # A task completed is reopened to started; only a milestone is brought back to not started.
    assert gestures(card_of(columns, "Étude")) == [("reopen", "started", True, [])]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_summary_whose_subordinates_are_all_completed_is_a_card_only_while_its_line_holds_it(
    review: Review,
) -> None:
    # « … jamais une récapitulative hors celle qui n'attend plus que ses lignes propres » (#1851):
    # the phase appears in the started tasks once its study is completed, flagged by its facet,
    # its card offering the entry of its remaining and no completion — neither start nor reopen —;
    # the line set to nought completes it, and it leaves the board.
    tree = review.tree
    moved(tree, "Étude", "started", DAY)
    assert "Phase" not in labels(board(tree))["started"] + labels(board(tree))["not_started"]
    moved(tree, "Étude", "completed", TUESDAY)
    columns = board(tree)
    phase = card_of(columns, "Phase")
    assert phase in columns["started"]
    assert phase["task"]["awaiting_own_lines"] is True
    assert phase["task"]["progress"] == "started"
    assert gestures(phase) == [
        ("complete", "completed", False, ["task_without_lines"]),
        ("enter_remaining", None, True, []),
    ]
    assert labels(columns)["completed"] == ["Étude"]
    zero(tree, "Pilotage", completed_on=FRIDAY.isoformat())
    assert labels(board(tree)) == {
        "not_started": ["Jalon", "Essai", "Livraison", "Montage", "Validation"],
        "started": [],
        "completed": ["Étude"],
    }


@pytest.mark.requirement("WF-PLA-0050-A")
def test_the_card_of_a_milestone_bearing_a_line_lacks_task_without_lines_and_enters_the_remaining(
    review: Review,
) -> None:
    # « La terminaison depuis le Kanban d'un jalon portant une ligne est refusée en renvoyant à la
    # saisie de son reste à engager. » The card lists ``complete`` unavailable,
    # ``task_without_lines``, and ``enter_remaining`` available; ``setTaskProgress`` refuses with
    # the same condition, the milestone without a line being completed from the card.
    tree = review.tree
    columns = board(tree)
    assert gestures(card_of(columns, "Livraison")) == [
        ("complete", "completed", False, ["task_without_lines"]),
        ("enter_remaining", None, True, []),
    ]
    assert missing(gesture(tree, "Livraison", "completed")) == "task_without_lines"
    assert gestures(card_of(columns, "Validation")) == [("complete", "completed", True, [])]
    zero(tree, "Acompte", completed_on=TUESDAY.isoformat())
    after = board(tree)
    assert labels(after)["completed"] == ["Livraison"]
    assert gestures(card_of(after, "Livraison")) == [("reopen", "not_started", True, [])]


@pytest.mark.requirement("WF-PLA-0070-A")
def test_a_task_started_is_not_deleted_and_its_card_sends_the_user_to_its_remaining(
    review: Review,
) -> None:
    # « La suppression d'une tâche démarrée est refusée, et l'utilisateur est renvoyé vers la mise
    # à zéro de son reste à engager. » The service refuses (``task_not_started``); the card of the
    # started task, the Kanban's, lists the entry of its remaining, open.
    tree = review.tree
    moved(tree, "Montage", "started", DAY)
    node = task_named(tree, "Montage")
    path = f"{tree.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}"
    refused = tree.api.delete(path, headers=tree.stage.manager.headers)
    assert missing(refused) == "task_not_started"
    assert gestures(card_of(board(tree), "Montage")) == [
        ("complete", "completed", False, ["task_without_lines"]),
        ("enter_remaining", None, True, []),
    ]


# --- Who writes, and when ------------------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_cards_of_a_caller_without_remaining_write_hold_no_gesture(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    # « … vides sans remaining.write » : the reader reads the same cards, in the same columns,
    # without a gesture; one that may write without being a contributor of the project (the
    # permission to view every project) sees them unavailable, the capacity named.
    tree = review.tree
    columns = board(tree)
    reader = board(tree, stage.reader)
    assert [len(card["available_commands"]) for card in reader["not_started"]] == [0] * 6
    assert labels(reader) == labels(columns)
    viewer = person(stage.database, realm, *READING, "remaining.write", name="Zoé")
    outsider = board(tree, viewer)
    assert gestures(card_of(outsider, "Étude")) == [
        ("start", "started", False, ["is_contributor"]),
        ("complete", "completed", False, ["task_is_milestone", "is_contributor"]),
    ]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_conditions_of_the_entry_of_the_remaining_follow_those_of_the_gesture(
    review: Review, stage: Scene
) -> None:
    # « … les conditions dans l'ordre du contrat (le geste, puis project_in_progress,
    # no_background_task_running) » : a project that is not In progress lacks
    # ``project_in_progress`` on every gesture, after the gesture's own.
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    columns = board(review.tree)
    assert gestures(card_of(columns, "Montage")) == [
        ("start", "started", False, ["project_in_progress"]),
        ("complete", "completed", False, [*NOT_STARTED, "project_in_progress"]),
        ("enter_remaining", None, False, ["project_in_progress"]),
    ]


def entry_lacks(tree: Tree, who: Any = None) -> list[str]:
    """Give what the card of a task with a line lacks to enter its remaining, as the Kanban says."""
    card = card_of(board(tree, who), "Montage")
    (entry,) = [each for each in gestures(card) if each[0] == "enter_remaining"]
    return entry[3]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_card_of_a_marked_current_revision_lacks_revision_draft(
    review: Review, stage: Scene
) -> None:
    # « … les conditions dans l'ordre du contrat » : with no revision in progress, the current
    # one is the last marked, and nothing modifies it: ``revision_draft``, as the 409 names it.
    review_marked(stage, review.tree.revision, "v2.0")
    assert entry_lacks(review.tree) == ["revision_draft"]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_card_lacks_no_background_task_running_while_a_task_runs(
    review: Review, stage: Scene, queue: TaskQueue
) -> None:
    # « … les conditions dans l'ordre du contrat » : a background task of the project is queued.
    payload = {
        "project_id": stage.project["project_id"],
        "revision_id": str(UUID(int=1)),
        "version_name": "v1.0",
        "description": None,
    }
    with logging_context(correlation_id="queued-around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, payload)
    assert entry_lacks(review.tree) == ["no_background_task_running"]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_card_of_a_project_out_of_progress_lacks_project_in_progress(
    review: Review, stage: Scene
) -> None:
    # « … les conditions dans l'ordre du contrat » : a project not In progress.
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    assert entry_lacks(review.tree) == ["project_in_progress"]


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_card_names_the_quality_then_the_phase_then_the_revision_in_that_order(
    review: Review, stage: Scene, realm: TestRealm
) -> None:
    # « … les conditions dans l'ordre du contrat » : a caller who is no contributor, on a project
    # not In progress, whose current revision is marked, lacks the three, in the order the
    # structure lists them.
    viewer = person(stage.database, realm, *READING, "remaining.write", name="Zoé")
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    review_marked(stage, review.tree.revision, "v2.0")
    assert entry_lacks(review.tree, viewer) == [
        "is_contributor",
        "project_in_progress",
        "revision_draft",
    ]


def test_the_conditions_a_card_names_are_those_the_entry_of_the_remaining_can_lack() -> None:
    # What ``edit_remaining`` of the main structure can lack, over every caller, phase and
    # revision, is what ``ENTRY_CONDITIONS`` types: a condition added there must be added here.
    found: set[str] = set()
    for kind in (None, "project_manager"):
        for state in ("pricing", "in_progress"):
            for marked, quiet in product((False, True), repeat=2):
                revision = RevisionState(
                    marked=marked,
                    no_task_running=quiet,
                    has_tasks_and_lines=True,
                    reference_correctable=True,
                )
                for command, lacking in structure_commands_of(
                    {"remaining.write"}, kind, state, revision, main=True
                ):
                    if command == "edit_remaining":
                        found.update(lacking)
    assert found == set(ENTRY_CONDITIONS)


@pytest.mark.requirement("WF-CYC-0110-A")
@pytest.mark.parametrize("state", TERMINAL)
def test_the_kanban_is_read_on_a_terminal_project_its_cards_without_a_gesture(
    review: Review, stage: Scene, state: str
) -> None:
    # « Toutes les vues de consultation d'un projet clos s'affichent normalement » : the three
    # columns as they were before the project left its cycle, the cards of the manager and of the
    # reader alike without a gesture — nothing more is written on a terminal project.
    tree = review.tree
    moved(tree, "Montage", "started", DAY)
    before = board(tree)
    put_in_state(stage.owner, stage.project["project_id"], state)
    after = board(tree)
    assert labels(after) == labels(before)
    assert labels(after)["started"] == ["Montage"]
    assert all(card["available_commands"] == [] for cards in after.values() for card in cards)
    reader = read(tree, stage.reader)
    assert reader.status_code == 200, reader.text
    assert labels(reader.json()) == labels(before)


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_kanban_of_a_project_that_does_not_exist_is_not_found(
    review: Review, stage: Scene
) -> None:
    # « … sous remaining.read » : the permissions of the operation are gathered by
    # ``test_access_evaluation.py``; a project that does not exist has no Kanban (404).
    unknown = f"{PROJECTS}/{UUID(int=7)}/remaining-indicators/startable-tasks"
    answer = review.tree.api.get(unknown, headers=stage.manager.headers)
    assert answer.status_code == 404, answer.text


def test_the_kanban_reads_the_tasks_in_a_number_of_statements_that_no_task_changes(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # Criterion of US-1590 of its own: « le temps de réponse de `listStartableTasks` sur les mille
    # tâches de PRJ-001 est mesuré contre le service » — a constant number of statements, whatever
    # the tasks, with their lines, their links, their summaries and their risks, is what keeps
    # that time bounded; the measure is the pull request's.

    def build(tree: Tree, lines: Lines) -> None:
        lines.made(tree.made("Départ"), **material(costs, "Ligne de départ", "10"))

    held = in_progress(api, stage, build)
    grow(held, costs, 0, 1)
    small = statements(held.tree)
    grow(held, costs, 1, 12)
    large = statements(held.tree)
    assert large == small, (small, large)
    assert large <= BOUND, large


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_task_created_while_the_kanban_is_read_is_not_read_and_the_next_reading_has_it(
    api: ContractClient, stage: Scene, costs: Costing, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The Kanban reads the nodes, the tasks that bear a line and the gestures in a transaction
    # frozen at its first read (#2800, #2679): a task committed between the reading of the nodes
    # and that of the lines is in none of them, so no card is made of two moments.

    def build(tree: Tree, lines: Lines) -> None:
        lines.made(tree.made("Départ"), **material(costs, "Ligne de départ", "10"))

    held = in_progress(api, stage, build)
    revision_id = UUID(held.tree.revision["revision_id"])
    before = labels(board(held.tree))
    reading = kanban.bearing_tasks
    created: list[UUID] = []

    def meanwhile(session: Session, project_id: UUID, structure_id: UUID) -> Any:
        with stage.database.engine.begin() as connection:
            created.append(give_a_task(connection, revision_id))
        return reading(session, project_id, structure_id)

    monkeypatch.setattr(kanban, "bearing_tasks", meanwhile)
    during = board(held.tree)
    monkeypatch.undo()
    assert created
    assert labels(during) == before
    after = board(held.tree)
    assert len(after["not_started"]) == len(before["not_started"]) + 1
    assert str(created[0]) in {card["node_id"] for card in after["not_started"]}


def grow(held: Review, costs: Costing, first: int, count: int) -> None:
    """Add groups to the tree: a summary of two tasks, each with a line, linked, one a risk's."""
    tree = held.tree
    for index in range(first, first + count):
        summary = tree.made(f"Récapitulative {index}")
        before = tree.made(f"Avant {index}", parent_id=summary["node_id"])
        after = tree.made(f"Après {index}", parent_id=summary["node_id"])
        held.lines.made(before, **material(costs, f"Ligne avant {index}", "10"))
        held.lines.made(after, **material(costs, f"Ligne après {index}", "10"))
        risk = line_named(tree, f"Ligne après {index}")
        put_risk(tree.stage, risk["node_id"], UUID(int=index + 1))
        answer = link(tree, task_named(tree, f"Après {index}"), tree.stage.manager, before)
        assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_line_is_a_provision_for_the_card_by_its_risk_not_by_its_category(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « Une tâche feuille démarrée sans ligne de devis est terminée depuis le Kanban. » : the card
    # and the refusal of ``setTaskProgress`` judge a line a provision by ``origin_risk_id``
    # (``open_lines`` judges by the category, and meets them once EP-08 gives each its risk): a
    # line of the category of provisions without a risk holds its task, the line of a risk of an
    # ordinary category does not.
    def build(tree: Tree, lines: Lines) -> None:
        lines.made(tree.made("Départ"), **material(costs, "Ligne de départ", "10"))

    held = in_progress(api, stage, build)
    for label in ("Catégorie seule", "Risque seul"):
        held.tree.made(label)
        held.lines.made(task_named(held.tree, label), **material(costs, f"Ligne {label}", "10"))
    categorized = line_named(held.tree, "Ligne Catégorie seule")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(categorized["node_id"]))
            .values(cost_category_id=costs.provision)
        )
    put_risk(stage, line_named(held.tree, "Ligne Risque seul")["node_id"], UUID(int=3))
    columns = board(held.tree)
    assert gestures(card_of(columns, "Catégorie seule"))[-1] == ("enter_remaining", None, True, [])
    assert gestures(card_of(columns, "Risque seul")) == [
        ("start", "started", True, []),
        ("complete", "completed", False, ["task_is_milestone"]),
    ]


def statements(tree: Tree) -> int:
    """Count the statements the service sends to the database to answer the Kanban once."""
    sent: list[str] = []

    def count(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    engine = tree.stage.database.engine
    event.listen(engine, "before_cursor_execute", count)
    try:
        assert read(tree).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", count)
    return len(sent)
