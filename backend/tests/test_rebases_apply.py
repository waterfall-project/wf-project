# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of a differential from the main structure (``rebaseCostStructure``; US-3050/L4).

The update writes what its report presented (``getStructureRebaseReport``), by the same function,
into the differential: the tasks, the links and the lines the main structure received since its
base, its nodes keeping their identifier, the base replaced by a copy of the main structure, the
differential up to date, the main structure never written. What it does not carry, by the four
rules of the report, stays as the differential has it. The refusals are in ``test_rebases_refused``,
the history in ``test_rebases_history``. Every answer is checked against the contract
(``ContractClient``).
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import (
    MAIN_ADDED,
    MAIN_REESTIMATED,
    MAIN_REMOVED,
    MAIN_RENAMED,
    OWN_ADDED,
    OWN_RENAMED,
    OutOfDate,
    deleted,
    listed,
    node_labelled,
    on,
    opened_amendment,
    out_of_date,
)
from estimate_support import Costing, Lines, costing
from history_support import link
from nodes_support import put_facts, work_breakdown
from projects_support import Scene
from projects_support import scene as make_scene
from rebases_support import (
    attachments,
    base_of,
    designations,
    lagged,
    lineages,
    links_of,
    moved_under,
    nodes_of,
    outline,
    rebased,
    state_of,
)
from risks_support import MAKING, STUDY, Costed, costed, declared, material
from sqlalchemy import update

from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the provision's among them."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


@pytest.fixture
def late(api: ContractClient, project: Costed) -> OutOfDate:
    """Give a differential out of date: the main structure moved on, the differential too."""
    return out_of_date(api, project)


def applied(api: ContractClient, late: OutOfDate) -> dict[str, Any]:
    """Update a differential, its report confirmed; the update must be done: give the structure."""
    answer = rebased(api, late)
    assert answer.status_code == 200, answer.text
    return answer.json()


# --- What the update writes -----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_update_writes_what_the_report_presented_and_everything_reads_unchanged(
    api: ContractClient, late: OutOfDate
) -> None:
    # « la tâche ajoutée à la structure principale est dans le différentiel sous sa lignée, à sa
    # place, le libellé et la réestimation qu'il ne désignait pas y sont, la tâche retirée n'y est
    # plus, et tous se lisent unchanged »: Recette follows Formation, as in the main structure,
    # before the task the differential added; Documentation, which the main structure removed, is
    # gone; what the differential designates is its addition, its modification, its removal.
    own = late.amendment
    applied(api, late)
    assert outline(own) == [
        (1, "Étude préalable", "unchanged"),
        (2, "Plans", "unchanged"),
        (1, "Réalisation", "unchanged"),
        (2, "Fabrication", "unchanged"),
        (1, "Montage", "removed"),
        (1, "Formation des équipes", "modified"),
        (1, "Recette", "unchanged"),
        (1, "Essais", "added"),
    ]


@pytest.mark.requirement("WF-REV-0100-A")
def test_what_the_differential_designated_keeps_its_nodes_and_reads_as_before(
    api: ContractClient, late: OutOfDate
) -> None:
    # « les nœuds qu'il désignait se lisent comme avant, sous leur identifiant » : the nodes of the
    # differential keep theirs, a node the main structure added taking a new one under the lineage
    # it has there; what the differential designates, by lineage, is what it was.
    main, own = late.project.tree, late.amendment
    nodes, designated = nodes_of(own, held=True), designations(own)
    assert len(designated) == 3
    applied(api, late)
    after = nodes_of(own, held=True)
    assert {each: node for each, node in after.items() if each in nodes} == {
        each: node for each, node in nodes.items() if each in after
    }
    added = node_labelled(main, MAIN_ADDED)["lineage_id"]
    assert added in after
    assert after[added] != node_labelled(main, MAIN_ADDED)["node_id"]
    assert node_labelled(own, MAIN_ADDED)["node_id"] == after[added]
    assert designations(own) == designated
    assert designated[node_labelled(own, OWN_ADDED)["lineage_id"]][0] == "added"
    assert (
        node_labelled(own, OWN_RENAMED[1])["lineage_id"]
        == node_labelled(main, "Formation")["lineage_id"]
    )


@pytest.mark.requirement("WF-REV-0100-A")
@pytest.mark.requirement("WF-REV-0110-A")
def test_the_main_structure_is_not_written_and_the_differential_is_up_to_date_on_its_base(
    api: ContractClient, late: OutOfDate
) -> None:
    # « le différentiel est à jour, et la structure principale n'est pas écrite »: its counter and
    # its nodes are as they were; the differential, up to date, has the command of its update
    # unavailable, its counter advanced; its base is a copy of the main structure, listed nowhere.
    project, main, own = late.project, late.project.tree, late.amendment
    before = (main.read().json(), state_of(api, project, main.structure_id))
    held = state_of(api, project, late.structure_id)
    assert held["is_up_to_date"] is False
    base = base_of(project, late.structure_id)
    assert lineages(project, base.id) != lineages(project, UUID(main.structure_id))
    done = applied(api, late)
    assert (main.read().json(), state_of(api, project, main.structure_id)) == before
    assert done == state_of(api, project, late.structure_id)
    assert done["is_up_to_date"] is True
    assert done["lock_version"] > held["lock_version"]
    rebase = next(each for each in done["available_commands"] if each["command"] == "rebase")
    assert rebase == {
        "command": "rebase",
        "is_available": False,
        "missing_conditions": ["structure_out_of_date"],
    }
    base = base_of(project, late.structure_id)
    assert lineages(project, base.id) == lineages(project, UUID(main.structure_id))
    assert base.id not in {UUID(each["structure_id"]) for each in listed(api, project)}
    removed = {node_labelled(main, "Montage")["lineage_id"]}
    own_lines = {lineage for lineage, _ in lineages(project, UUID(late.structure_id))}
    main_lines = {lineage for lineage, _ in lineages(project, UUID(main.structure_id))}
    assert {str(each) for each in own_lines ^ main_lines} - removed == {
        node_labelled(own, OWN_ADDED)["lineage_id"]
    }


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_base_takes_the_start_of_the_main_structure_as_the_column_holds_it(
    api: ContractClient, late: OutOfDate
) -> None:
    # [US-3050] The base is a copy of the main structure after the update: a main structure whose
    # start of planning is null (a row the migration did not fill) gives its base a null start,
    # not the day derived for it, which the main structure does not bear.
    project = late.project
    with project.stage.database.transaction() as session:
        session.execute(
            update(CostStructure)
            .where(
                CostStructure.project_id == project.project_id,
                CostStructure.id == UUID(project.tree.structure_id),
            )
            .values(planning_start_on=None)
        )
    assert base_of(project, late.structure_id).planning_start_on is not None
    applied(api, late)
    assert base_of(project, late.structure_id).planning_start_on is None


@pytest.mark.requirement("WF-REV-0100-A")
def test_an_update_leaves_the_differential_out_of_date_again_by_the_next_write_of_the_main(
    api: ContractClient, late: OutOfDate
) -> None:
    # « en retard dès qu'une écriture avance le compteur de la structure principale », after the
    # update as after its opening: a second update carries what the main structure received since,
    # and the first nodes stay.
    project, main, own = late.project, late.project.tree, late.amendment
    applied(api, late)
    nodes = nodes_of(own, held=True)
    assert state_of(api, project, late.structure_id)["is_up_to_date"] is True
    main.made("Livraison")
    assert state_of(api, project, late.structure_id)["is_up_to_date"] is False
    applied(api, late)
    assert state_of(api, project, late.structure_id)["is_up_to_date"] is True
    after = nodes_of(own, held=True)
    assert {each: node for each, node in after.items() if each in nodes} == nodes
    assert [label for _, label, _ in outline(own)][-3:] == ["Recette", "Livraison", "Essais"]


# --- The lines ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_line_the_main_adds_enters_with_its_figures_and_a_figure_it_changes_is_taken(
    api: ContractClient, late: OutOfDate, costs: Costing
) -> None:
    # « tâches, liaisons et lignes ajoutées, modifiées avec leurs champs, retirées »: the line the
    # main structure adds under Étude enters the differential under its lineage, after the line
    # that precedes it there, at the figures and the amounts of the main structure; the line it
    # re-estimated has them too.
    main, own = late.project.tree, late.amendment
    Lines(main).made(node_labelled(main, MAIN_RENAMED[1]), **material(costs, "Grue", "80.00"))
    applied(api, late)
    assert [(label, mark) for _, label, mark in outline(own)][:5] == [
        ("Étude préalable", "unchanged"),
        ("Plans", "unchanged"),
        ("Grue", "unchanged"),
        ("Réalisation", "unchanged"),
        ("Fabrication", "unchanged"),
    ]
    for label in ("Grue", MAIN_REESTIMATED[0]):
        mine, theirs = node_labelled(own, label), node_labelled(main, label)
        assert mine["lineage_id"] == theirs["lineage_id"]
        assert mine["estimate_line"] == theirs["estimate_line"]
    assert node_labelled(own, MAIN_REESTIMATED[0])["estimate_line"]["unit_disbursement"] == "450.00"
    assert node_labelled(own, "Grue")["lock_version"] == 1


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_provision_line_of_the_main_structure_enters_neither_the_differential_nor_its_base(
    api: ContractClient, late: OutOfDate, costs: Costing
) -> None:
    # « la ligne de provision d'un risque de la structure principale n'y est pas présentée
    # retirée » (#4035), and not carried either (#4008): a risk declared since the base is the
    # main structure's alone; the differential and its new base hold none.
    project, main, own = late.project, late.project.tree, late.amendment
    declared(project)
    provisions = [
        each
        for each in main.items()
        if each["estimate_line"]
        and each["estimate_line"]["cost_category_id"] == str(costs.provision)
    ]
    assert len(provisions) == 1
    applied(api, late)
    assert provisions[0]["estimate_line"]["label"] not in {label for _, label, _ in outline(own)}
    base = base_of(project, late.structure_id)
    held = {each for each in lineages(project, base.id) if each[1] == "estimate_line"}
    assert (UUID(provisions[0]["lineage_id"]), "estimate_line") not in held


# --- The places -----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_task_the_main_moves_goes_where_it_puts_it_and_the_task_it_adds_follows_it(
    api: ContractClient, late: OutOfDate
) -> None:
    # The conception of the EPIC (« La mise à jour ») says « un nœud que la principale a ajouté y
    # entre sous sa lignée, à sa place ; une valeur qu'elle a changée y est changée »: the main
    # structure moves Formation under Étude, and a task with a subtask and a line, which enter the
    # differential one under the other, each under the lineage it has there.
    main, own = late.project.tree, late.amendment
    moved_under(main, OWN_RENAMED[0], MAIN_RENAMED[1])
    lot = main.made("Livraison")
    main.made("Colis", parent_id=lot["node_id"])
    Lines(main).made(
        node_labelled(main, "Colis"), **material(late.project.costs, "Caisse", "40.00")
    )
    applied(api, late)
    assert outline(own) == [
        (1, "Étude préalable", "modified"),
        (2, "Plans", "unchanged"),
        (2, "Formation des équipes", "modified"),
        (1, "Réalisation", "unchanged"),
        (2, "Fabrication", "unchanged"),
        (1, "Montage", "removed"),
        (1, "Recette", "unchanged"),
        (1, "Livraison", "unchanged"),
        (2, "Colis", "unchanged"),
        (3, "Caisse", "unchanged"),
        (1, "Essais", "added"),
    ]
    assert node_labelled(own, "Caisse")["lineage_id"] == node_labelled(main, "Caisse")["lineage_id"]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_line_the_main_moves_goes_under_its_new_task_after_the_line_that_precedes_it(
    api: ContractClient, late: OutOfDate
) -> None:
    # The conception of the EPIC says « une valeur qu'elle a changée y est changée »: the main
    # structure moves the line Plans
    # under Réalisation, after Fabrication; the line enters the differential's task there, its
    # parent named by the report as updated.
    main, own = late.project.tree, late.amendment
    moved_under(main, "Plans", MAKING)
    found = rebased(api, late)
    assert found.status_code == 200, found.text
    assert [label for level, label, _ in outline(own) if level == 2] == ["Fabrication", "Plans"]
    assert node_labelled(own, "Plans")["difference"] == "unchanged"
    assert node_labelled(own, "Plans")["parent_id"] == node_labelled(own, MAKING)["node_id"]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_line_the_main_adds_to_a_task_the_differential_removed_enters_under_its_parent(
    api: ContractClient, project: Costed
) -> None:
    # The conception of the EPIC says « un nœud que la principale a ajouté y entre sous sa lignée,
    # à sa place »: a line the main structure adds to a subtask the differential removes enters
    # under the subtask's parent, last of its lines — the differential designating its move, which
    # the base, a copy of the main structure, says —; one it adds to a task of the first level the
    # differential removes does not enter: the base holds it, the differential removed it.
    main = project.tree
    main.made("Montage", parent_id=node_labelled(main, STUDY)["node_id"])
    main.made("Documentation")
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    deleted(own, "Montage", project.stage.manager)
    deleted(own, "Documentation", project.stage.manager)
    Lines(main).made(node_labelled(main, "Montage"), **material(project.costs, "Grue", "80.00"))
    Lines(main).made(
        node_labelled(main, "Documentation"), **material(project.costs, "Notices", "30.00")
    )
    applied(api, OutOfDate(project, structure_id, own))
    assert outline(own) == [
        (1, "Étude", "modified"),
        (2, "Plans", "unchanged"),
        (2, "Grue", "modified"),
        (2, "Montage", "removed"),
        (1, "Réalisation", "unchanged"),
        (2, "Fabrication", "unchanged"),
        (1, "Documentation", "removed"),
        (2, "Notices", "removed"),
    ]


# --- The links ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_main_adds_changes_or_removes_is_written_in_the_differential(
    api: ContractClient, project: Costed
) -> None:
    # « tâches, liaisons et lignes ajoutées, modifiées avec leurs champs, retirées »: a link the
    # main structure adds between two tasks the differential holds, one whose type it changes, one
    # it removes — the differential not having changed them; the pairs are by lineage.
    main, manager = project.tree, project.stage.manager
    main.made("Essais")
    lagged(main, MAKING, {STUDY: "0"})
    lagged(main, "Essais", {MAKING: "0"})
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    late = OutOfDate(project, structure_id, own)
    study, making, trial = (
        node_labelled(main, each)["lineage_id"] for each in (STUDY, MAKING, "Essais")
    )
    pairs = {(UUID(study), UUID(making)), (UUID(making), UUID(trial))}
    assert set(links_of(project, structure_id)) == pairs
    lagged(main, MAKING, {STUDY: "0"}, "start_to_start")
    assert link(main, node_labelled(main, "Essais"), manager).status_code == 200
    main.made("Livraison")
    lagged(main, "Livraison", {"Essais": "1"})
    applied(api, late)
    assert links_of(project, structure_id) == {
        (UUID(study), UUID(making)): "start_to_start",
        (UUID(trial), UUID(node_labelled(main, "Livraison")["lineage_id"])): "finish_to_start",
    }
    assert links_of(project, structure_id) == links_of(project, main.structure_id)


# --- The four rules -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
@pytest.mark.requirement("WF-REV-0110-A")
def test_a_value_both_change_keeps_the_differential_s_after_the_update(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une valeur que le différentiel désigne et que la structure principale a changée depuis
    # garde la valeur du différentiel »: both rename Formation; the unit disbursement of a line
    # both change stays the differential's, the figure the merge gives as the reference
    # (WF-REV-0050); the differential still designates them.
    main, own = late.project.tree, late.amendment
    main.changed(node_labelled(main, OWN_RENAMED[0]), label="Formation interne")
    Lines(own).changed(node_labelled(own, MAIN_REESTIMATED[0]), unit_disbursement="300.00")
    renamed = node_labelled(own, OWN_RENAMED[1])
    applied(api, late)
    # What the update did not write is not counted: its entries of the history stay undoable.
    assert node_labelled(own, OWN_RENAMED[1])["lock_version"] == renamed["lock_version"]
    assert node_labelled(own, OWN_RENAMED[1])["difference"] == "modified"
    assert node_labelled(main, "Formation interne")["task"]["label"] == "Formation interne"
    kept = node_labelled(own, MAIN_REESTIMATED[0])
    assert kept["estimate_line"]["unit_disbursement"] == "300.00"
    assert kept["difference"] == "modified"


@pytest.mark.requirement("WF-REV-0100-A")
@pytest.mark.requirement("WF-REV-0110-A")
def test_a_task_the_differential_modifies_and_the_main_removed_stays_as_an_addition(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche que le différentiel modifie et que la structure principale n'a plus reste au
    # différentiel, qui la présente ensuite added »: the task renamed in the differential and
    # removed from the main structure stays; the line of it the differential did not touch goes
    # with what the main structure removed.
    structure_id = opened_amendment(api, project)
    own = on(project.tree, structure_id)
    own.changed(node_labelled(own, MAKING), label="Réalisation reprise")
    deleted(project.tree, MAKING, project.stage.manager)
    applied(api, OutOfDate(project, structure_id, own))
    assert outline(own) == [
        (1, STUDY, "unchanged"),
        (2, "Plans", "unchanged"),
        (1, "Réalisation reprise", "added"),
    ]


@pytest.mark.requirement("WF-REV-0100-A")
def test_what_the_differential_adds_under_a_task_that_leaves_goes_under_its_nearest_ancestor(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche qu'il ajoute sous une tâche que la structure principale n'a plus passe sous
    # l'ancêtre le plus proche qui reste »: a subtask and a line added under a subtask the main
    # structure removes go under its parent, at the place the subtask held among its siblings; the
    # task above them, whose amounts the line moves, reads modified, as it does for any line added.
    main = project.tree
    lot = node_labelled(main, STUDY)
    main.made("Relevés", parent_id=lot["node_id"])
    main.made("Synthèse", parent_id=lot["node_id"])
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    surveys = node_labelled(own, "Relevés")
    own.made("Relevés complémentaires", parent_id=surveys["node_id"])
    Lines(own).made(surveys, **material(project.costs, "Mire", "20.00"))
    deleted(main, "Relevés", project.stage.manager)
    applied(api, OutOfDate(project, structure_id, own))
    assert outline(own) == [
        (1, STUDY, "modified"),
        (2, "Plans", "unchanged"),
        (2, "Mire", "added"),
        (2, "Relevés complémentaires", "added"),
        (2, "Synthèse", "unchanged"),
        (1, MAKING, "unchanged"),
        (2, "Fabrication", "unchanged"),
    ]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_differential_adds_to_a_task_that_leaves_is_removed_with_it(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une liaison qu'il ajoute vers une tâche que la structure principale n'a plus est retirée »:
    # the link from the task the main structure removed to the task the differential adds is not
    # in the differential after the update; the task it adds stays.
    project, own = late.project, late.amendment
    essais = node_labelled(own, OWN_ADDED)
    documentation = node_labelled(own, MAIN_REMOVED)
    assert link(own, essais, project.stage.manager, documentation).status_code == 200
    assert len(links_of(project, late.structure_id)) == 1
    applied(api, late)
    assert links_of(project, late.structure_id) == {}
    assert node_labelled(own, OWN_ADDED)["difference"] == "added"


# --- The dates, the attachments -------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_dates_of_the_differential_are_computed_again_once(
    api: ContractClient, late: OutOfDate
) -> None:
    # The conception of the EPIC says « Le moteur de dates est rejoué une fois sur le
    # différentiel »: a duration the main structure lengthens is carried, and the finish of the
    # task, computed on the differential, is the one the main structure computes — as its
    # successor's, which the engine moves with it.
    main, own = late.project.tree, late.amendment
    lagged(main, "Recette", {MAKING: "0"})
    task = node_labelled(main, MAKING)["task"]
    main.changed(node_labelled(main, MAKING), duration={"value": "20", "unit": "d"})
    assert node_labelled(main, MAKING)["task"]["finish"] != task["finish"]
    applied(api, late)
    for label in (MAKING, "Recette"):
        mine, theirs = node_labelled(own, label)["task"], node_labelled(main, label)["task"]
        assert (mine["start"], mine["finish"], mine["duration"]) == (
            theirs["start"],
            theirs["finish"],
            theirs["duration"],
        )


@pytest.mark.requirement("WF-PLA-0170-A")
def test_a_task_the_main_adds_enters_without_the_attachments_a_differential_never_bears(
    api: ContractClient, late: OutOfDate
) -> None:
    # A differential bears no attachment (#4221): the task the main structure adds,
    # attached to a work package, enters the differential unattached, as the fusion never takes an
    # attachment of a differential; the main structure keeps its own.
    project, main = late.project, late.project.tree
    package, _ = work_breakdown(project.stage)
    put_facts(project.stage, node_labelled(main, MAIN_ADDED)["node_id"], work_package_id=package)
    assert (package, None) in attachments(project, main.structure_id)
    applied(api, late)
    assert set(attachments(project, late.structure_id)) == {(None, None)}
    assert (package, None) in attachments(project, main.structure_id)
