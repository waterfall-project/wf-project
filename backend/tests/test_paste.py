# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste of a block of cells in the planning: ``previewPaste`` then ``applyPaste`` (US-1450/L2).

Every answer checked against the contract, on the main structure of a revision a project's manager
opened. A block pasted from a task fills the columns of its facet in the order of ``NodeColumn``,
one row per node in the order of the plan: previewed — what will be written and what will be
refused, the reason of each refusal, nothing written —, then confirmed, the rows accepted written
in one operation and one entry of the history; abandoned, the grid unchanged. The cells are judged
by the very functions of the entry of a cell; a structure that moved since the preview is refused
(412), a plan judged again at its confirmation, an element of the work breakdown gone since a
refusal. The rows past the last node create tasks, siblings of it, by the function of the creation
of ``createNode`` — counted by the preview, created by the confirmation, deleted by an undoing and
created again by a redoing (US-1450/L5, #2559).

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from decimal import Decimal
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from history_support import counter, plans, redone, undone
from nodes_support import (
    SATURDAY,
    Tree,
    entries,
    instant,
    mark,
    opened,
    refusal,
    signed_in,
    work_breakdown,
)
from planning_support import DAY, node_row
from projects_support import scene as make_scene
from sqlalchemy import insert, inspect, update

from waterfall.core.planning.attachments import Attached
from waterfall.core.planning.entries import Facet
from waterfall.core.planning.interface import (
    PasteBlock,
    Place,
    Writer,
    apply_cell,
    preview_paste,
    traced,
)
from waterfall.core.planning.interface.nodes import (
    CreationJudged,
    Ground,
    NodeCreation,
    TaskEntry,
    judge_creation,
    traced_creation,
)
from waterfall.core.planning.scheduling import Duration
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.tree import Tree as PlanTree
from waterfall.core.projects.tables import WorkPackage
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MILESTONE = {"duration": {"value": "0", "unit": "d"}}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def preview(
    tree: Tree,
    target: dict[str, Any],
    column: str,
    rows: list[list[str]],
    who: Person | None = None,
) -> Any:
    """Preview a block pasted on a cell of a task; give the answer."""
    sent = {"target_node_id": target["node_id"], "target_column": column, "rows": rows}
    headers = (who or tree.stage.manager).headers
    return tree.api.post(f"{tree.path}/nodes/paste-preview", headers=headers, json=sent)


def planned(
    tree: Tree,
    target: dict[str, Any],
    column: str,
    rows: list[list[str]],
    who: Person | None = None,
) -> dict[str, Any]:
    """Preview a block that must be previewed; give the plan."""
    answer = preview(tree, target, column, rows, who)
    assert answer.status_code == 200, answer.text
    return answer.json()


def apply(
    tree: Tree, plan: dict[str, Any], who: Person | None = None, lock_version: int | None = None
) -> Any:
    """Confirm a plan at the counter of the structure unless one is sent; give the answer."""
    sent = {
        "paste_id": plan["paste_id"],
        "confirmed": True,
        "lock_version": counter(tree) if lock_version is None else lock_version,
    }
    headers = (who or tree.stage.manager).headers
    return tree.api.post(f"{tree.path}/nodes/paste", headers=headers, json=sent)


def applied(tree: Tree, plan: dict[str, Any], who: Person | None = None) -> dict[str, Any]:
    """Confirm a plan that must be confirmed; give what is answered."""
    answer = apply(tree, plan, who)
    assert answer.status_code == 200, answer.text
    return answer.json()


def reasons(plan: dict[str, Any]) -> list[tuple[int, str | None, str]]:
    """Give the refusals of a plan: the row, the column if there is one, the code."""
    return [(each["row"], each.get("column"), each["code"]) for each in plan["rejected"]]


def labels_of(tree: Tree) -> list[str]:
    """Read the labels of the tasks, in the order of the plan."""
    return tree.labels()


# --- The two steps of a paste -------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_block_previewed_then_confirmed_writes_its_rows_in_one_operation_and_one_entry(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Vérif : « Un bloc de trois lignes et quatre colonnes collé depuis un tableur produit un compte
    # rendu avant écriture, puis les trois lignes attendues après confirmation. » : trois tâches
    # dans l'ordre du plan — dont une sous la première, récapitulative, qui dérive son mode et sa
    # durée —, de leur libellé à leur durée.
    study = tree.made("Étude", who=who)
    note = tree.made("Note", who=who, parent_id=study["node_id"])
    works = tree.made("Travaux", who=who)
    before = counter(tree)
    block = [
        ["Études de détail", "Les calculs", "", ""],
        ["Note de calcul", "", "automatic", "2,5 h"],
        ["Travaux de câblage", "Le poste", "automatic", "3 w"],
    ]
    plan = planned(tree, study, "label", block, who)
    assert (plan["accepted"], plan["rejected"]) == (3, [])
    # The preview writes nothing: neither the tasks, nor the counter, nor the history.
    assert labels_of(tree) == ["Étude", "Note", "Travaux"]
    assert counter(tree) == before
    assert [each.kind for each in entries(stage)] == ["node_create"] * 3
    assert len(plans(stage)) == 1

    body = applied(tree, plan, who)
    assert body["rejected"] == []
    assert body["structure_lock_version"] == before + 1
    written = [each["node_id"] for each in body["nodes"]]
    assert sorted(written) == sorted([study["node_id"], note["node_id"], works["node_id"]])
    assert labels_of(tree) == ["Études de détail", "Note de calcul", "Travaux de câblage"]
    read = {each["node_id"]: each["task"] for each in tree.items()}
    assert read[note["node_id"]]["description"] is None
    assert read[works["node_id"]]["description"] == "Le poste"
    assert (read[note["node_id"]]["duration"], read[works["node_id"]]["duration"]) == (
        {"value": "2.5", "unit": "h"},
        {"value": "3", "unit": "w"},
    )
    # One entry of the history, kind paste; the plan is dropped once applied.
    last = entries(stage)[-1]
    assert (last.kind, len(entries(stage))) == ("paste", 4)
    assert sorted(map(str, last.node_ids)) == sorted(written)
    assert plans(stage) == []
    # The three rows are undone by one undoing, and redone by one.
    first = undone(tree, who)
    assert first["undone"]["kind"] == "paste"
    assert labels_of(tree) == ["Étude", "Note", "Travaux"]
    assert tree.node(works["node_id"])["task"]["duration"] == {"value": "1", "unit": "d"}


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_paste_abandoned_leaves_the_grid_unchanged(tree: Tree, stage: Scene, who: Person) -> None:
    # Vérif : « abandonné, il ne modifie aucune ligne. » : a plan not confirmed writes nothing.
    task = tree.made("Câblage", who=who)
    before = (tree.items(), counter(tree), entries(stage))
    plan = planned(tree, task, "label", [["Autre libellé"]], who)
    assert plan["accepted"] == 1
    assert (tree.items(), counter(tree)) == before[:2]
    assert [each.id for each in entries(stage)] == [each.id for each in before[2]]
    # Another write leaves the plan to its hour; applied after it, it is refused, nothing written.
    assert tree.change(tree.node(task["node_id"]), None, description="Repris").status_code == 200
    assert apply(tree, plan, who).status_code == 412
    assert tree.node(task["node_id"])["task"]["label"] == "Câblage"


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_cells_empty_write_nothing_and_a_row_of_empty_cells_is_not_a_row_to_write(
    tree: Tree, who: Person
) -> None:
    first = tree.made("Étude", who=who)
    second = tree.made("Travaux", who=who)
    tree.made("Essais", who=who)
    plan = planned(
        tree, first, "label", [["", "Une description"], ["", ""], ["Essais finaux"]], who
    )
    assert (plan["accepted"], plan["rejected"]) == (2, [])
    body = applied(tree, plan, who)
    assert [each["node_id"] for each in body["nodes"]] == [
        first["node_id"],
        tree.items()[2]["node_id"],
    ]
    read = tree.node(first["node_id"])["task"]
    assert (read["label"], read["description"]) == ("Étude", "Une description")
    assert tree.node(second["node_id"])["task"]["label"] == "Travaux"
    assert labels_of(tree) == ["Étude", "Travaux", "Essais finaux"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_dates_of_a_manual_task_pasted_are_written_with_the_hours_of_its_calendar(
    tree: Tree, who: Person
) -> None:
    task = tree.made(
        "Montage",
        who=who,
        task={
            "scheduling_mode": "manual",
            "start": instant(DAY, "0"),
            "finish": instant(DAY, "8"),
        },
    )
    block = [["", "", "", "", "2026-11-04", "2026-11-05"]]
    plan = planned(tree, task, "label", block, who)
    assert plan["accepted"] == 1
    applied(tree, plan, who)
    read = tree.node(task["node_id"])["task"]
    assert (read["start"], read["finish"]) == (
        instant(DAY.replace(day=4), "0"),
        instant(DAY.replace(day=5), "8"),
    )
    assert read["duration"] == {"value": "2", "unit": "d"}


# --- What a cell is refused for -------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_cell_refused_is_named_by_its_row_and_its_column_and_its_row_is_not_written(
    tree: Tree, who: Person
) -> None:
    # Vérif : « Un bloc dont une cellule porte une catégorie inconnue signale cette ligne ;
    # confirmé, il écrit les autres lignes et non celle-ci. » : here a value computed, a column that
    # no write carries, a value that is no number, and the others written.
    first = tree.made("Étude", who=who)
    tree.made("Travaux", who=who)
    tree.made("Essais", who=who)
    tree.made("Recette", who=who)
    block = [
        ["Études", "", "", "", "", "", "50"],
        ["Travaux 2", "", "", "", "", "", "", "", "", "2026-11-03"],
        ["Essais 2", "", "", "dix"],
        ["Recette 2", "Finale"],
    ]
    plan = planned(tree, first, "label", block, who)
    assert plan["accepted"] == 1
    assert reasons(plan) == [
        (0, "physical_progress", "COMPUTED_VALUE"),
        (1, "started_on", "FIELD_NOT_ACCEPTED"),
        (2, "duration", "NUMBER_INVALID"),
    ]
    body = applied(tree, plan, who)
    assert body["rejected"] == plan["rejected"]
    assert len(body["nodes"]) == 1
    assert labels_of(tree) == ["Étude", "Travaux", "Essais", "Recette 2"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_values_that_are_no_date_no_mode_nor_label_are_refused_by_their_reason(
    tree: Tree, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    tree.made("Travaux", who=who)
    tree.made("Essais", who=who)
    tree.made("Recette", who=who)
    block = [
        ["", "", "hybrid"],
        ["x" * 301],
        ["", "", "", "3 parsecs"],
        ["", "", "", "", "11/05/2026"],
    ]
    plan = planned(tree, task, "label", block, who)
    assert plan["accepted"] == 0
    assert [(each["row"], each["column"], each["code"]) for each in plan["rejected"]] == [
        (0, "scheduling_mode", "VALIDATION_FAILED"),
        (1, "label", "VALUE_TOO_LONG"),
        (2, "duration", "VALIDATION_FAILED"),
        (3, "start", "DATE_INVALID"),
    ]
    assert plan["rejected"][1]["params"] == {"max_length": 300}


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_manual_date_pasted_on_a_day_without_hours_names_the_next_working_day(
    tree: Tree, who: Person
) -> None:
    task = tree.made(
        "Montage",
        who=who,
        task={"scheduling_mode": "manual", "start": instant(DAY, "0"), "finish": instant(DAY, "8")},
    )
    plan = planned(tree, task, "start", [[SATURDAY.isoformat(), "2026-11-04"]], who)
    assert plan["accepted"] == 0
    [refused] = plan["rejected"]
    assert (refused["row"], refused["column"], refused["code"]) == (0, "start", "NON_WORKING_DAY")
    assert refused["params"] == {"date": SATURDAY.isoformat(), "next_working_day": "2026-11-09"}


@pytest.mark.requirement("WF-PLA-0040-A")
def test_what_a_summary_and_a_milestone_derive_or_refuse_is_refused_in_a_paste_as_in_an_entry(
    tree: Tree, who: Person
) -> None:
    summary = tree.made("Étude", who=who)
    child = tree.made("Note", who=who, parent_id=summary["node_id"])
    milestone = tree.made("Livraison", who=who, task=MILESTONE)
    block = [["", "", "manual", "3", "2026-11-04"], ["", "", "", "2"], ["", "", "", "4"]]
    plan = planned(tree, summary, "label", block, who)
    assert plan["accepted"] == 1
    assert [(each["row"], each["column"], each["code"]) for each in plan["rejected"]] == [
        (0, "scheduling_mode", "COMPUTED_VALUE"),
        (0, "duration", "COMPUTED_VALUE"),
        (0, "start", "SUMMARY_TASK_DERIVED"),
        (2, "duration", "FIELD_NOT_ACCEPTED"),
    ]
    assert plan["rejected"][2]["params"] == {"subordinate_node_ids": [child["node_id"]]}
    body = applied(tree, plan, who)
    assert [each["node_id"] for each in body["nodes"]] == [child["node_id"]]
    assert tree.node(child["node_id"])["task"]["duration"] == {"value": "2", "unit": "d"}
    assert tree.node(milestone["node_id"])["task"]["is_milestone"] is True


@pytest.mark.requirement("WF-PLA-0170-A")
def test_the_rules_of_the_attachment_judge_the_cells_of_the_work_breakdown_column(
    tree: Tree, stage: Scene, who: Person
) -> None:
    package, item = work_breakdown(stage)
    first = tree.made("Étude", who=who)
    second = tree.made("Travaux", who=who)
    third = tree.made("Essais", who=who)
    block = [["", "", "", "", "", "", "", "", "", "", "", "", "Lot"], [""] * 12 + ["Absent"]]
    plan = planned(tree, first, "label", block, who)
    assert (plan["accepted"], reasons(plan)) == (
        1,
        [(1, "work_breakdown", "UNKNOWN_WORK_BREAKDOWN_ITEM")],
    )
    body = applied(tree, plan, who)
    assert [each["node_id"] for each in body["nodes"]] == [first["node_id"]]
    assert tree.node(first["node_id"])["task"]["work_package_id"] == str(package)
    # The element is borne by one task of the structure; a task bears one of the two at a time.
    again = planned(tree, second, "work_breakdown", [["Lot"]], who)
    assert reasons(again) == [(0, "work_breakdown", "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED")]
    [held] = again["rejected"]
    assert held["params"] == {
        "conflicting_object_id": first["node_id"],
        "conflicting_object_label": "Étude",
    }
    exclusive = planned(tree, first, "work_breakdown", [["Poste"]], who)
    assert reasons(exclusive) == [(0, "work_breakdown", "WORK_BREAKDOWN_ITEMS_EXCLUSIVE")]
    # The task of an order item lies in the subtree of the task of its work package.
    outside = planned(tree, third, "work_breakdown", [["Poste"]], who)
    assert reasons(outside) == [(0, "work_breakdown", "ORDER_ITEM_OUTSIDE_WORK_PACKAGE")]
    assert outside["rejected"][0]["params"]["work_package_task"] == {
        "node_id": first["node_id"],
        "label": "Étude",
    }
    # An order item pasted under the task of its work package is written, and borne by that task.
    child = tree.made("Sous-étude", who=who, parent_id=first["node_id"])
    inside = applied(tree, planned(tree, child, "work_breakdown", [["Poste"]], who), who)
    assert [each["node_id"] for each in inside["nodes"]] == [child["node_id"]]
    assert tree.node(child["node_id"])["task"]["order_item_id"] == str(item)


@pytest.mark.requirement("WF-IHM-0050-A")
def test_two_rows_naming_the_same_element_are_judged_by_the_preview_as_the_confirmation_does(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # The confirmation writes the rows one after the other, each judged on what the one before
    # wrote: the preview does the same, so that no refusal is found only once confirmed.
    package, _ = work_breakdown(stage)
    first = tree.made("Étude", who=who)
    second = tree.made("Travaux", who=who)
    plan = planned(tree, first, "work_breakdown", [["Lot"], ["Lot"]], who)
    assert (plan["accepted"], reasons(plan)) == (
        1,
        [(1, "work_breakdown", "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED")],
    )
    body = applied(tree, plan, who)
    assert reasons(body) == reasons(plan)
    assert [each["node_id"] for each in body["nodes"]] == [first["node_id"]]
    assert tree.node(first["node_id"])["task"]["work_package_id"] == str(package)
    assert tree.node(second["node_id"])["task"]["work_package_id"] is None


def estimate_line(stage: Scene, tree: Tree, task: dict[str, Any]) -> UUID:
    """Write an estimate line under a task around the service, as EP-07 will; give its id."""
    row = node_row(
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
        kind="estimate_line",
        parent_id=UUID(task["node_id"]),
    )
    with stage.owner.begin() as connection:
        connection.execute(insert(Node).values(**row))
    return cast("UUID", row["id"])


# --- The rows past the last node: the paste that creates (#2559) ---------------------------------


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_rows_past_the_last_node_are_counted_by_the_preview_then_created_beside_it(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Vérif : « Un bloc de trois lignes et quatre colonnes collé depuis un tableur produit un compte
    # rendu avant écriture, puis les trois lignes attendues après confirmation. » — critère
    # d'US-1450 : chaque ligne au-delà du dernier nœud de la structure crée une tâche, sœur du
    # dernier nœud (même parent), le compte rendu dit combien de lignes créent (`created`), et
    # `applyPaste` écrit les lignes existantes et créées en une opération et une seule entrée
    # d'historique.
    study = tree.made("Étude", who=who)
    note = tree.made("Note", who=who, parent_id=study["node_id"])
    before, kept = counter(tree), len(entries(stage))
    block = [
        ["Note de calcul", "", "", ""],
        ["Plan", "Les plans", "automatic", "3"],
        ["Recette", "", "", ""],
    ]
    plan = planned(tree, note, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (3, 2, [])
    # The preview creates nothing: neither the tasks, nor the counter, nor the history.
    assert labels_of(tree) == ["Étude", "Note"]
    assert (counter(tree), len(entries(stage))) == (before, kept)

    body = applied(tree, plan, who)
    assert body["rejected"] == []
    assert (body["structure_lock_version"], body["totals"]["task_count"]) == (before + 1, 4)
    assert labels_of(tree) == ["Étude", "Note de calcul", "Plan", "Recette"]
    items = tree.items()
    made = [each["node_id"] for each in items[2:]]
    assert [each["node_id"] for each in body["nodes"]] == [note["node_id"], *made]
    # Siblings of the anchor, under its parent, at their first version.
    assert [each["parent_id"] for each in items[1:]] == [study["node_id"]] * 3
    assert [each["lock_version"] for each in body["nodes"][1:]] == [1, 1]
    # The values of a creation, then the cells pasted (WF-DEV-0050): automatic, a day by default.
    plan_task, acceptance = items[2]["task"], items[3]["task"]
    assert (plan_task["description"], plan_task["duration"]) == (
        "Les plans",
        {"value": "3", "unit": "d"},
    )
    assert (acceptance["scheduling_mode"], acceptance["duration"]) == (
        "automatic",
        {"value": "1", "unit": "d"},
    )
    assert (acceptance["description"], items[3]["predecessors"]) == (None, [])
    # One entry of the history, kind paste, naming the node written and the tasks created.
    last = entries(stage)[-1]
    assert (last.kind, len(entries(stage))) == ("paste", kept + 1)
    assert sorted(map(str, last.node_ids)) == sorted([note["node_id"], *made])
    assert plans(stage) == []


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_row_past_the_last_node_without_a_label_is_refused_on_its_label_and_creates_nothing(
    tree: Tree, who: Person
) -> None:
    # Critère d'US-1450 : le libellé d'une tâche créée est requis — la ligne dont il manque est
    # refusée, sa colonne nommée. A row created after one refused follows the anchor.
    task = tree.made("Étude", who=who)
    block = [["Étude 2"], ["", "Sans libellé"], ["Travaux"]]
    plan = planned(tree, task, "label", block, who)
    assert (plan["accepted"], plan["created"]) == (2, 1)
    assert reasons(plan) == [(1, "label", "VALIDATION_FAILED")]
    body = applied(tree, plan, who)
    assert reasons(body) == reasons(plan)
    assert labels_of(tree) == ["Étude 2", "Travaux"]
    assert len(body["nodes"]) == 2
    # A block that does not start at the label column has no label to create a task with.
    described = planned(tree, tree.items()[-1], "description", [["Une"], ["Deux"]], who)
    assert (described["accepted"], described["created"]) == (1, 0)
    assert reasons(described) == [(1, "label", "VALIDATION_FAILED")]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_cell_refused_on_a_row_past_the_last_node_refuses_the_row_as_an_entry_would(
    tree: Tree, who: Person
) -> None:
    # Critère propre à US-1450, dans l'esprit du Vérif de WF-IHM-0050-A (« Un bloc dont une cellule
    # porte une catégorie inconnue signale cette ligne ; confirmé, il écrit les autres lignes et
    # non celle-ci. ») : les autres cellules d'une tâche créée se jugent comme celles d'une tâche
    # qui s'écrit — mode inconnu, date calculée, jour non ouvré. The anchor's own
    # row is refused: it is the anchor still, and the task created is its sibling.
    first = tree.made("Étude", who=who)
    anchor = tree.made("Travaux", who=who)
    block = [
        ["", "", "", "", "", "", "50"],
        ["Essais", "", "hybrid"],
        ["Recette", "", "", "", "2026-11-04"],
        ["Réglage", "", "manual", "", SATURDAY.isoformat()],
        ["Mise en service", "", "manual", "", "2026-11-04", "2026-11-05"],
    ]
    plan = planned(tree, anchor, "label", block, who)
    assert (plan["accepted"], plan["created"]) == (1, 1)
    assert reasons(plan) == [
        (0, "physical_progress", "COMPUTED_VALUE"),
        (1, "scheduling_mode", "VALIDATION_FAILED"),
        (2, "start", "COMPUTED_VALUE"),
        (3, "start", "NON_WORKING_DAY"),
    ]
    assert plan["rejected"][3]["params"] == {
        "date": SATURDAY.isoformat(),
        "next_working_day": "2026-11-09",
    }
    body = applied(tree, plan, who)
    assert reasons(body) == reasons(plan)
    items = tree.items()
    assert [each["task"]["label"] for each in items] == ["Étude", "Travaux", "Mise en service"]
    assert items[2]["parent_id"] is None
    assert [each["node_id"] for each in body["nodes"]] == [items[2]["node_id"]]
    created = items[2]["task"]
    assert (created["scheduling_mode"], created["start"], created["finish"]) == (
        "manual",
        instant(DAY.replace(day=4), "0"),
        instant(DAY.replace(day=5), "8"),
    )
    assert created["duration"] == {"value": "2", "unit": "d"}
    assert tree.node(first["node_id"])["task"]["label"] == "Étude"


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_row_that_creates_is_judged_again_and_refused_since_it_is_not_created(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Critère d'US-1450 : à l'application, une ligne qui crée est rejugée ; refusée, elle passe
    # dans `rejected` et sa tâche n'est pas créée (an element removed since the preview).
    package, _ = work_breakdown(stage)
    task = tree.made("Étude", who=who)
    block = [["Études"], ["Plan", *[""] * 11, "Lot"], ["Recette"]]
    plan = planned(tree, task, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (3, 2, [])
    with stage.owner.begin() as connection:
        connection.execute(
            update(WorkPackage).where(WorkPackage.id == package).values(deleted_at=utc_now())
        )
    body = applied(tree, plan, who)
    assert reasons(body) == [(1, "work_breakdown", "UNKNOWN_WORK_BREAKDOWN_ITEM")]
    assert labels_of(tree) == ["Études", "Recette"]
    assert len(body["nodes"]) == 2
    assert body["totals"]["task_count"] == 2


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_plan_that_creates_creates_nothing_abandoned_or_stale(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Vérif : « abandonné, il ne modifie aucune ligne. » — and a plan stale (412) writes nothing:
    # the tasks a plan holds are created by its confirmation alone.
    task = tree.made("Étude", who=who)
    before = (tree.items(), counter(tree), len(entries(stage)))
    abandoned = planned(tree, task, "label", [["Étude"], ["Plan"]], who)
    assert abandoned["created"] == 1
    assert (tree.items(), counter(tree), len(entries(stage))) == before
    assert tree.change(tree.node(task["node_id"]), None, description="Repris").status_code == 200
    assert refusal(apply(tree, abandoned, who))[:2] == (412, "STALE_LOCK_VERSION")
    assert labels_of(tree) == ["Étude"]
    assert [each.kind for each in entries(stage)] == ["node_create"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_plan_names_the_node_it_creates_and_the_cell_of_the_work_breakdown_is_judged_on_it(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Critère d'US-1450 : le plan garde, pour chaque ligne, le nœud qu'elle crée, que la
    # confirmation crée sous cet identifiant ; la cellule `work_breakdown` d'une ligne créée sous
    # un parent rattaché se juge comme celle d'une tâche écrite (an order item under its package).
    package, item = work_breakdown(stage)
    parent = tree.made("Étude", who=who)
    child = tree.made("Sous-étude", who=who, parent_id=parent["node_id"])
    applied(tree, planned(tree, parent, "work_breakdown", [["Lot"]], who), who)
    assert tree.node(parent["node_id"])["task"]["work_package_id"] == str(package)
    block = [["Sous-étude"], ["Plan", *[""] * 11, "Poste"]]
    plan = planned(tree, child, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (2, 1, [])
    [kept] = plans(stage)
    [created] = [each["node_id"] for each in kept.rows["rows"] if each["creates"]]
    body = applied(tree, plan, who)
    assert [each["node_id"] for each in body["nodes"]] == [child["node_id"], created]
    made = tree.node(created)
    assert made["parent_id"] == parent["node_id"]
    assert made["task"]["order_item_id"] == str(item)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_paste_that_creates_is_undone_by_deleting_its_tasks_and_redone_by_creating_them(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Vérif : « Cinquante modifications successives s’annulent une par une, puis se rétablissent
    # dans l’ordre. » (WF-IHM-0110-A) : ici une seule entrée, celle du collage — critère d'US-1450 :
    # annuler le collage supprime les tâches qu'il a créées, le rétablir les recrée. As the undoing
    # of a creation, it names the nodes it deletes, and gives back none of them among the nodes
    # written.
    task = tree.made("Étude", who=who)
    plan = planned(tree, task, "label", [["Étude 2"], ["Plan", "", "", "2"], ["Recette"]], who)
    body = applied(tree, plan, who)
    made = [each["node_id"] for each in body["nodes"][1:]]
    assert len(made) == 2

    first = undone(tree, who)
    assert first["undone"]["kind"] == "paste"
    assert sorted(first["undone"]["node_ids"]) == sorted([task["node_id"], *made])
    assert [each["node_id"] for each in first["written"]["nodes"]] == [task["node_id"]]
    assert first["written"]["totals"]["task_count"] == 1
    assert labels_of(tree) == ["Étude"]

    again = redone(tree, who)
    assert again["undone"]["kind"] == "paste"
    assert [each["node_id"] for each in again["written"]["nodes"]] == [task["node_id"], *made]
    assert again["written"]["totals"]["task_count"] == 3
    assert labels_of(tree) == ["Étude 2", "Plan", "Recette"]
    assert tree.node(made[0])["task"]["duration"] == {"value": "2", "unit": "d"}
    assert [each.undone for each in entries(stage)][-1] is False


@pytest.mark.requirement("WF-PLA-0050-A")
def test_the_creation_a_paste_calls_refuses_a_task_under_a_milestone_naming_it() -> None:
    # Vérif : « Une tâche feuille de durée nulle ne peut recevoir de sous-tâche. » — écart #1772 au
    # collage : la création du collage passe par la fonction de `createNode`, qui porte ce refus, et
    # un test unitaire l'éprouve ; aucun geste d'EP-06 ne l'atteint (US-1560, EP-07, clôt).
    milestone_id, project_id = uuid4(), uuid4()
    node = Node(id=milestone_id, kind="task", parent_id=None, rank=1)
    task = Task(node_id=milestone_id, label="Livraison", duration_value=0)
    ground = Ground(
        cast("Any", None),
        project_id,
        PlanTree({milestone_id: node}, {milestone_id: task}),
        is_main=True,
    )
    creation = NodeCreation(
        parent_id=milestone_id, after_node_id=None, after_given=False, task=TaskEntry(label="Pose")
    )
    with pytest.raises(UnprocessableError) as refused:
        judge_creation(ground, creation, uuid4())
    assert refused.value.code == "VALIDATION_FAILED"
    assert [(each.pointer, each.code, each.params) for each in refused.value.fields] == [
        (
            "/parent_id",
            "MILESTONE_HAS_NO_SUBTASK",
            {"node_id": str(milestone_id), "label": "Livraison"},
        )
    ]


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_row_past_a_line_of_a_milestone_is_refused_naming_the_milestone(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # The site of #1772 in a paste, reached here by a line written around the service: the anchor
    # is a line of a milestone, whose sibling would be a subtask of the milestone. The row is
    # refused whole, the milestone named (`PasteRejection`) — by the label the row before gives it,
    # each row being judged on what the rows before leave —, and creates nothing.
    milestone = tree.made("Livraison", who=who, task=MILESTONE)
    estimate_line(stage, tree, milestone)
    plan = planned(tree, milestone, "label", [["Livraison finale"], [""], ["Pose"]], who)
    assert (plan["accepted"], plan["created"]) == (1, 0)
    [refused] = plan["rejected"]
    assert refused == {
        "row": 2,
        "code": "MILESTONE_HAS_NO_SUBTASK",
        "params": {"node_id": milestone["node_id"], "label": "Livraison finale"},
    }


# --- What a block may not be -------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_block_wider_than_the_columns_of_the_facet_from_the_targeted_one_is_refused(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # Vérif : « Un collage plus large que la grille est refusé en le disant. »
    task = tree.made("Étude", who=who)
    for column, columns in (("label", 13), ("description", 12), ("work_breakdown", 1)):
        answer = preview(tree, task, column, [["x"] * (columns + 1)], who)
        assert refusal(answer) == (422, "PASTE_TOO_WIDE", {"max_columns": columns}), column
        assert preview(tree, task, column, [["x"] * columns, []], who).status_code == 200, column
    assert len(plans(stage)) == 3
    assert labels_of(tree) == ["Étude"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_target_that_is_unknown_or_a_column_of_an_estimate_line_is_refused(
    tree: Tree, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    ghost = preview(tree, {"node_id": str(uuid4())}, "label", [["x"]], who)
    assert refusal(ghost)[:2] == (404, "NOT_FOUND")
    answer = preview(tree, task, "cost_category", [["x"]], who)
    assert answer.status_code == 422
    assert [(each["pointer"], each["code"]) for each in answer.json()["fields"]] == [
        ("/target_column", "FIELD_NOT_ACCEPTED")
    ]


# --- The confirmation ----------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_plan_is_refused_when_the_structure_moved_since_its_preview_whatever_counter_is_sent(
    tree: Tree, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    plan = planned(tree, task, "label", [["Études"]], who)
    previewed = counter(tree)
    assert tree.change(tree.node(task["node_id"]), None, description="Repris").status_code == 200
    current = counter(tree)
    assert current == previewed + 1
    for sent in (previewed, current):
        answer = apply(tree, plan, who, lock_version=sent)
        assert refusal(answer) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": current})
    assert counter(tree) == current
    assert tree.node(task["node_id"])["task"]["label"] == "Étude"
    # A fresh plan at a counter that is stale is refused too, and nothing is written.
    fresh = planned(tree, task, "label", [["Études"]], who)
    stale = apply(tree, fresh, who, lock_version=previewed)
    assert refusal(stale)[:2] == (412, "STALE_LOCK_VERSION")
    assert applied(tree, fresh, who)["structure_lock_version"] == current + 1


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_plan_is_applied_once_by_the_account_that_previewed_it_on_its_structure(
    tree: Tree, stage: Scene, realm: TestRealm, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    plan = planned(tree, task, "label", [["Études"]], who)
    other = signed_in(stage, realm)
    assert refusal(apply(tree, plan, other))[:2] == (404, "NOT_FOUND")
    assert refusal(apply(tree, {"paste_id": str(uuid4())}, who))[:2] == (404, "NOT_FOUND")
    applied(tree, plan, who)
    assert refusal(apply(tree, plan, who))[:2] == (404, "NOT_FOUND")
    assert labels_of(tree) == ["Études"]


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_paste_confirmed_on_a_revision_marked_since_is_refused_by_the_state(
    tree: Tree, stage: Scene, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    plan = planned(tree, task, "label", [["Études"]], who)
    mark(stage, tree.revision)
    answer = apply(tree, plan, who)
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_rows_of_a_plan_are_judged_again_and_a_row_refused_since_moves_into_the_refusals(
    tree: Tree, stage: Scene, who: Person
) -> None:
    # The reference data has no counter: a row accepted at the preview may be refused at the
    # confirmation, and is not written; the others are.
    package, _ = work_breakdown(stage)
    first = tree.made("Étude", who=who)
    second = tree.made("Travaux", who=who)
    block = [["Études"], [""] * 12 + ["Lot"]]
    plan = planned(tree, first, "label", block, who)
    assert (plan["accepted"], plan["rejected"]) == (2, [])
    with stage.owner.begin() as connection:
        connection.execute(
            update(WorkPackage).where(WorkPackage.id == package).values(deleted_at=utc_now())
        )
    before = counter(tree)
    body = applied(tree, plan, who)
    assert reasons(body) == [(1, "work_breakdown", "UNKNOWN_WORK_BREAKDOWN_ITEM")]
    assert [each["node_id"] for each in body["nodes"]] == [first["node_id"]]
    assert body["structure_lock_version"] == before + 1
    assert tree.node(second["node_id"])["task"]["work_package_id"] is None
    assert plans(stage) == []
    # The entry of the history names the nodes written, not those of the plan.
    assert entries(stage)[-1].node_ids == [UUID(first["node_id"])]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_plan_with_no_row_left_to_write_writes_nothing_leaves_the_counter_and_keeps_no_entry(
    tree: Tree, stage: Scene, who: Person
) -> None:
    package, _ = work_breakdown(stage)
    task = tree.made("Étude", who=who)
    plan = planned(tree, task, "work_breakdown", [["Lot"]], who)
    assert plan["accepted"] == 1
    with stage.owner.begin() as connection:
        connection.execute(
            update(WorkPackage).where(WorkPackage.id == package).values(deleted_at=utc_now())
        )
    before, kept = counter(tree), len(entries(stage))
    body = applied(tree, plan, who)
    assert (body["nodes"], body["ancestors"], body["rescheduled"]) == ([], [], [])
    assert (body["structure_lock_version"], counter(tree)) == (before, before)
    assert body["totals"]["task_count"] == 1
    assert reasons(body) == [(0, "work_breakdown", "UNKNOWN_WORK_BREAKDOWN_ITEM")]
    assert len(entries(stage)) == kept
    assert plans(stage) == []
    # A plan all of whose rows were refused at the preview is the same: nothing to write.
    refused = planned(tree, task, "physical_progress", [["50"]], who)
    assert refused["accepted"] == 0
    again = applied(tree, refused, who)
    assert (again["nodes"], again["structure_lock_version"]) == ([], before)
    assert reasons(again) == [(0, "physical_progress", "COMPUTED_VALUE")]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_paste_is_the_act_of_an_account_never_of_the_platform(tree: Tree, stage: Scene) -> None:
    task = tree.made("Étude")
    block = PasteBlock(UUID(task["node_id"]), "label", (("x",),))
    project, revision = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    where = Place(project, revision, UUID(tree.structure_id))
    with stage.database.transaction() as session, pytest.raises(RuntimeError):
        preview_paste(
            session, where, block, Writer(Act(None, utc_now()), None), ("planning.write",)
        )


class _Recorder:
    """A stand-in for a task that keeps the names of the attributes written on it."""

    written: set[str]

    def __init__(self) -> None:
        object.__setattr__(self, "written", set())

    def __setattr__(self, name: str, value: object) -> None:
        self.written.add(name)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_copy_of_a_paste_previewed_holds_every_attribute_a_cell_writes() -> None:
    # The guard of ``traced``: it rebuilds each task from its columns, so that an attribute
    # ``apply_cell`` wrote beside them would be lost in the preview without a sound.
    attached = SimpleNamespace(work_package_id=uuid4(), order_item_id=uuid4())
    entry = SimpleNamespace(sent={"label", "description"}, label="Essais", description="d")
    day = SimpleNamespace(day=None, hours=None)
    duration = SimpleNamespace(value=1, unit="d")
    facet = SimpleNamespace(scheduling_mode="manual", duration=duration, start=day, finish=day)
    recorder = _Recorder()
    apply_cell(cast("Any", recorder), cast("Any", entry), cast("Any", (facet, attached)))
    columns = {attr.key for attr in inspect(Task).column_attrs}
    assert recorder.written
    assert recorder.written <= columns

    task = Task(**dict.fromkeys(columns))
    node_id = uuid4()
    ground = Ground(cast("Any", None), uuid4(), PlanTree({}, {node_id: task}), is_main=True)
    copy = traced(ground).tree.tasks[node_id]
    assert copy is not task
    assert {column: getattr(copy, column) for column in columns} == {
        column: getattr(task, column) for column in columns
    }


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_creation_traced_in_a_preview_leaves_the_ground_it_comes_from_as_it_was() -> None:
    # The guard of ``traced_creation``: the siblings a creation moves down and its parent made a
    # summary are copies, so that a row refused once its task is traced leaves no trace on the rows
    # after it, and the preview writes nothing.
    parent_id, sibling_id, node_id = uuid4(), uuid4(), uuid4()
    nodes = {
        parent_id: Node(id=parent_id, kind="task", parent_id=None, rank=1),
        sibling_id: Node(id=sibling_id, kind="task", parent_id=parent_id, rank=1),
    }
    parent = Task(node_id=parent_id, label="Montage", scheduling_mode="manual", duration_value=1)
    sibling = Task(node_id=sibling_id, label="Pose", scheduling_mode="automatic", duration_value=1)
    tasks = {parent_id: parent, sibling_id: sibling}
    ground = Ground(cast("Any", None), uuid4(), PlanTree(nodes, tasks), is_main=True)
    creation = NodeCreation(
        parent_id=parent_id, after_node_id=None, after_given=True, task=TaskEntry(label="Réglage")
    )
    facet = Facet("automatic", Duration(Decimal(1), "d"), None, None)
    held = (facet, Attached(None, None))
    judged = CreationJudged(node_id, creation, held, 1, (sibling_id,), made_summary=True)
    place = Place(uuid4(), uuid4(), uuid4())
    grown = traced_creation(ground, (place, Act(uuid4(), utc_now()), DAY), judged)
    assert grown.tree.subtasks(parent_id) == [node_id, sibling_id]
    assert grown.tree.nodes[sibling_id].rank == 2
    assert grown.tree.tasks[parent_id].scheduling_mode == "automatic"
    assert grown.tree.tasks[node_id].start_date == DAY
    # The ground it comes from is unchanged.
    assert (nodes[sibling_id].rank, parent.scheduling_mode) == (1, "manual")
    assert ground.tree.subtasks(parent_id) == [sibling_id]
