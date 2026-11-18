# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of the summaries in the grid of the planning, by ``listNodes`` (US-1680).

A summary over three subordinates bearing lines of material of 100, 100 and 200, written through the
service: in a project In progress, the subordinates completed as their manager completes them
(``setTaskProgress``, then their line set to nought); before In progress, and in a revision marked,
their state put around the service. Each reading — whole, the tasks alone, filtered, a marked
revision read from its reading kept — gives the summary the share of the budgeted amounts of its
subtree its completed tasks earn (WF-IND-0060), a leaf and a milestone none; every answer is checked
against the contract by the client of the tests.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from day_indicators_support import completed, line_of, material
from estimate_support import Costing, Lines, costing
from indicators_support import progressed, zeroed
from nodes_support import Tree, mark, opened, set_progress
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_support import in_progress, line_named, task_named
from sqlalchemy import select, update
from test_inert_writes import listened

from waterfall.api.contract.models import TaskFacetUpdate, TaskFacetWrite
from waterfall.api.nodes import FORMAT
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import StructureReading

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

LOT = "Lot"
# The three subordinates of the sentence, and the amounts of their lines of material.
SUBORDINATES = {"Études": "100.00", "Câblage": "100.00", "Essais": "200.00"}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories of the lines: material, and the provision of the reference."""
    return costing(stage.database)


def build(costs: Costing, own: str | None = None) -> Any:
    """Give what writes the summary and its subordinates with their lines, its own one if said."""

    def write(tree: Tree, lines: Lines) -> None:
        lot = tree.made(LOT)
        if own is not None:
            lines.made(lot, **material(costs, line_of(LOT), own, None))
        for label, amount in SUBORDINATES.items():
            task = tree.made(label, parent_id=lot["node_id"])
            lines.made(task, **material(costs, line_of(label), amount, None))

    return write


def progress_of(tree: Tree, label: str, query: str = "") -> Any:
    """Read the physical progress of the task of a label, as the reading the query asks gives it."""
    return next(
        item["task"]["physical_progress"]
        for item in tree.items(query)
        if item["kind"] == "task" and item["task"]["label"] == label
    )


def share(value: str) -> dict[str, Any]:
    """Give a physical progress computed, as the contract writes it."""
    return {"is_computable": True, "value": value, "reason": None}


def ids_of(tree: Tree) -> dict[str, str]:
    """Give the node of each task of the structure, by its label."""
    return {
        item["task"]["label"]: item["node_id"]
        for item in tree.items("?kinds=task")
        if item["kind"] == "task"
    }


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.requirement("WF-PLA-0130-A")
@pytest.mark.parametrize(
    ("done", "shown"), [(("Études", "Câblage"), "0.5"), (("Études", "Essais"), "0.75")]
)
def test_a_summary_of_100_100_200_shows_50_percent_then_75_percent_in_every_reading(
    api: ContractClient, stage: Scene, costs: Costing, done: tuple[str, str], shown: str
) -> None:
    # « Une récapitulative sans ligne propre dont les deux premières de trois subordonnées, de
    # montants budgétés 100, 100 et 200, sont terminées affiche 50 % ; si la troisième est
    # terminée à la place de la deuxième, 75 %. » « La marge totale, la criticité et l'avancement
    # physique s'affichent et ne sont pas saisissables. » Completed by their manager, read whole,
    # the tasks alone, and a reading that gives the summary alone.
    tree = in_progress(api, stage, build(costs)).tree
    for label in done:
        completed(tree, label, DAY)
    assert progress_of(tree, LOT) == share(shown)
    assert progress_of(tree, LOT, "?kinds=task") == share(shown)
    assert progress_of(tree, LOT, "?summaries_only=true") == share(shown)
    for label in SUBORDINATES:
        assert progress_of(tree, label) is None


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_subordinate_started_counts_nought_and_400_of_1000_completed_show_40_percent(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « Sur un budget de 1 000 dont 400 sont portés par des tâches terminées, l'avancement
    # physique vaut 40 %. » « Une tâche démarrée à 90 % de son temps ne contribue pas. » A summary
    # over 400 completed and 600 started.
    def write(tree: Tree, lines: Lines) -> None:
        lot = tree.made(LOT)
        for label, amount in {"Études": "400.00", "Câblage": "600.00"}.items():
            task = tree.made(label, parent_id=lot["node_id"])
            lines.made(task, **material(costs, line_of(label), amount, None))

    tree = in_progress(api, stage, write).tree
    completed(tree, "Études", DAY)
    progressed(tree, task_named(tree, "Câblage"), "started", DAY)
    assert progress_of(tree, LOT) == share("0.4")
    assert progress_of(tree, LOT, "?kinds=task") == share("0.4")


@pytest.mark.requirement("WF-IND-0060-A")
def test_the_own_lines_of_a_summary_count_in_its_total_and_are_earned_when_it_is_completed(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « … ses lignes propres comprises … » The summary bears 100 of its own: its subordinates
    # completed, it awaits its own line, 400 earned of 500; its line set to nought, it is
    # completed, and earns the whole.
    tree = in_progress(api, stage, build(costs, own="100.00")).tree
    for label in SUBORDINATES:
        completed(tree, label, DAY)
    held = task_named(tree, LOT)["task"]
    assert (held["progress"], held["awaiting_own_lines"]) == ("started", True)
    assert progress_of(tree, LOT) == share("0.8")
    assert progress_of(tree, LOT, "?kinds=task") == share("0.8")
    zeroed(tree, line_named(tree, line_of(LOT)), DAY)
    assert task_named(tree, LOT)["task"]["progress"] == "completed"
    assert progress_of(tree, LOT) == share("1")
    assert progress_of(tree, LOT, "?kinds=task") == share("1")


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_provision_line_counts_neither_in_the_total_nor_in_what_is_earned(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « … hors lignes de provision … » A line of 1 000 under the first subordinate, its category
    # made a provision around the service (a provision is never entered): 100 of 400, as without.
    tree = Tree(api, stage, opened(api, stage))
    build(costs)(tree, Lines(tree))
    ids = ids_of(tree)
    line = Lines(tree).made(ids["Études"], **material(costs, "Provision", "1000.00", None))
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(line["nodes"][0]["node_id"]))
            .values(cost_category_id=costs.provision)
        )
    set_progress(stage, ids["Études"], "completed", DAY)
    assert progress_of(tree, LOT) == share("0.25")
    assert progress_of(tree, LOT, "?kinds=task") == share("0.25")


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.requirement("WF-PLA-0130-A")
def test_before_in_progress_a_summary_is_computed_a_leaf_and_a_milestone_bear_none(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # A project before In progress: no task is completed, the summary shows 0; one without any
    # budgeted amount is not computable; a leaf and a milestone bear none. The physical progress is
    # no field a write sends.
    tree = Tree(api, stage, opened(api, stage))
    build(costs)(tree, Lines(tree))
    empty = tree.made("Réception")
    tree.made("Recette", parent_id=empty["node_id"])
    tree.made("Jalon", task={"duration": {"value": "0", "unit": "d"}})
    assert progress_of(tree, LOT) == share("0")
    assert progress_of(tree, LOT, "?kinds=task") == share("0")
    not_computable = {"is_computable": False, "value": None, "reason": "no_budgeted_amount"}
    assert progress_of(tree, "Réception") == not_computable
    assert progress_of(tree, "Réception", "?kinds=task") == not_computable
    assert progress_of(tree, "Études") is None
    assert progress_of(tree, "Jalon") is None
    assert "physical_progress" not in TaskFacetWrite.model_fields
    assert "physical_progress" not in TaskFacetUpdate.model_fields


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_bound_on_the_physical_progress_judges_the_value_computed(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # The first subordinate completed: the summary at 0.25 is retained between 0.2 and 0.3, not
    # above 0.3; a leaf, which bears none, never; the tasks read alone judge alike.
    tree = Tree(api, stage, opened(api, stage))
    build(costs)(tree, Lines(tree))
    set_progress(stage, ids_of(tree)["Études"], "completed", DAY)
    within = "physical_progress_min=0.2&physical_progress_max=0.3"
    assert tree.labels(f"?kinds=task&{within}") == [LOT]
    assert [
        item["task"]["label"] for item in tree.items(f"?{within}") if item["kind"] == "task"
    ] == [LOT]
    assert tree.labels("?kinds=task&physical_progress_min=0.3") == []
    assert tree.labels("?kinds=task&physical_progress_max=1") == [LOT]


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_marked_revision_is_computed_on_its_own_states_and_kept_with_its_reading(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « … sur une révision marquée, le calcul se fait sur ses propres lignes et états … » Two
    # subordinates completed, then the revision marked: its reading, made and kept at its first
    # whole reading in the format of the code, gives 0.5, as its tasks read alone and its reading
    # kept projected by ``fields``.
    tree = Tree(api, stage, opened(api, stage))
    build(costs)(tree, Lines(tree))
    ids = ids_of(tree)
    for label in ("Études", "Câblage"):
        set_progress(stage, ids[label], "completed", DAY)
    mark(stage, tree.revision)
    assert progress_of(tree, LOT) == share("0.5")
    with stage.database.transaction() as session:
        kept = session.scalar(
            select(StructureReading.format).where(
                StructureReading.structure_id == UUID(tree.structure_id)
            )
        )
    assert kept == FORMAT
    assert progress_of(tree, LOT, "?kinds=task") == share("0.5")
    assert progress_of(tree, LOT, "?fields=kind,task.label,task.physical_progress") == share("0.5")


def progress_in(answer: dict[str, Any], node_id: str) -> Any:
    """Read the physical progress of a task among the nodes and the ancestors an answer gives."""
    return next(
        item["task"]["physical_progress"]
        for item in (*answer["nodes"], *answer["ancestors"])
        if item["node_id"] == node_id
    )


def zeroing(tree: Tree, label: str) -> Any:
    """Start a task of a label, then set its line to nought; give the answer of the second write."""
    progressed(tree, task_named(tree, label), "started", DAY)
    line = line_named(tree, line_of(label))
    sent = {
        "lock_version": line["lock_version"],
        "reestimated_amount_basis": {"quantity": "0"},
        "completed_on": DAY.isoformat(),
    }
    written = tree.api.put(
        f"{tree.path}/nodes/{line['node_id']}/remaining",
        headers=tree.stage.manager.headers,
        json=sent,
    )
    assert written.status_code == 200, written.text
    return written.json()


@pytest.mark.requirement("WF-IND-0060-A")
def test_the_answer_of_a_write_gives_the_summary_above_with_the_progress_it_now_has(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « … sur une récapitulative, la part des montants budgétés de son sous-arbre que gagnent ses
    # tâches terminées … » The answers are given one by one, not in the reading of the structure:
    # the summary above a subordinate a write moves is given back with the value it now has. Two
    # subordinates completed by their line (the write of a line), 100 then 200 of 400; the second
    # reopened by the gesture of its card (``setTaskProgress``), 100 of 400. A task that bears lines
    # is completed by its line alone: the card refuses it.
    tree = in_progress(api, stage, build(costs)).tree
    lot = ids_of(tree)[LOT]
    assert progress_in(zeroing(tree, "Études"), lot) == share("0.25")
    assert progress_in(zeroing(tree, "Câblage"), lot) == share("0.5")
    task = task_named(tree, "Câblage")
    reopened = api.put(
        f"{tree.path}/nodes/{task['node_id']}/progress",
        headers=stage.manager.headers,
        json={"progress": "started", "lock_version": task["lock_version"]},
    )
    assert reopened.status_code == 200, reopened.text
    assert progress_in(reopened.json(), lot) == share("0.25")
    # The label of a subordinate changed, a write of the short path: the summary is given alike.
    renamed = tree.changed(reopened.json()["nodes"][0], label="Câblage de la baie")
    assert progress_in(renamed, lot) == share("0.25")


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.parametrize("named", ["kind,task.label", "task.label,estimate_line.label"])
def test_a_projection_that_names_no_physical_progress_asks_nothing_for_it(
    api: ContractClient, stage: Scene, costs: Costing, named: str
) -> None:
    # A reading projected by ``fields`` that leaves the physical progress out does not pay for it:
    # the same reading naming it, or the facet that holds it, sends the statements of the tallies
    # and of the categories of provision more, and none of the projection does.
    tree = in_progress(api, stage, build(costs)).tree
    sent: dict[str, int] = {}
    for name, fields in {
        "without": named,
        "field": f"{named},task.physical_progress",
        "facet": f"{named},task",
    }.items():
        with listened() as statements:
            answer = tree.read(f"?fields={fields}")
        assert answer.status_code == 200, answer.text
        sent[name] = len(statements)
    assert sent["without"] < sent["field"]
    assert sent["without"] < sent["facet"]


@pytest.mark.requirement("WF-IND-0060-A")
def test_the_physical_progress_of_a_summary_depends_on_the_whole_subtree(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # The share weighs the amounts of the lines and counts the tasks completed of the whole subtree,
    # not of the first level: a summary of a summary names every line and every task under it, in
    # the order of the plan, and not itself, and no line of provision.
    tree = Tree(api, stage, opened(api, stage))
    lines = Lines(tree)
    top = tree.made(LOT)
    own = lines.made(top, **material(costs, line_of(LOT), "50.00", None))
    middle = tree.made("Sous-lot", parent_id=top["node_id"])
    studies = tree.made("Études", parent_id=middle["node_id"])
    studied = lines.made(studies, **material(costs, line_of("Études"), "100.00", None))
    wiring = tree.made("Câblage", parent_id=middle["node_id"])
    # A line of provision under the lower task weighs nothing: it is not one of the rows.
    held = lines.made(wiring, **material(costs, "Provision", "300.00", None))
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(held["nodes"][0]["node_id"]))
            .values(cost_category_id=costs.provision)
        )
    # A line not of a provision at nought weighs nothing today, and is one of the rows all the same:
    # the share depends on it as soon as it is given an amount.
    nought = lines.made(wiring, **material(costs, line_of("Nul"), "0.00", None))
    path = f"{tree.path}/nodes/{top['node_id']}/dependencies?field=task.physical_progress"
    answer = api.get(path, headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["depends_on"] == ["lines_and_subordinates"]
    assert held["nodes"][0]["node_id"] not in [row["node_id"] for row in body["rows"]]
    assert [row["node_id"] for row in body["rows"]] == [
        own["nodes"][0]["node_id"],
        middle["node_id"],
        studies["node_id"],
        studied["nodes"][0]["node_id"],
        wiring["node_id"],
        nought["nodes"][0]["node_id"],
    ]
    assert [row["row_number"] for row in body["rows"]] == sorted(
        row["row_number"] for row in body["rows"]
    )
