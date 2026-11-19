# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report before the update of a differential (``getStructureRebaseReport``; US-3050/L3).

A read that writes nothing: what the update would carry from the main structure into the
differential — tasks, lines and links added, updated with their fields, removed —, what the
differential keeps against it by the four rules (``kept``), the reasons that refuse it, judged once
on the differential the update leaves, and the counters of the two structures read; a structure that
is not a differential out of date of the current revision has the 409 of its update. The three
structures — the main one, the differential, its base — are matched by lineage. Every answer is
checked against the contract (``ContractClient``), and the parts of the modules against its models.
"""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import (
    MAIN_ADDED,
    MAIN_REESTIMATED,
    MAIN_REMOVED,
    MAIN_RENAMED,
    OWN_ADDED,
    OWN_REMOVED,
    OWN_RENAMED,
    OutOfDate,
    deleted,
    listed,
    node_labelled,
    on,
    opened_amendment,
    out_of_date,
    revision_path,
    started_marking,
)
from estimate_support import Costing, Lines, add_role, costing
from history_support import link
from nodes_support import mark, put_facts
from projects_support import Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed, material
from sqlalchemy import select, update

from waterfall.api.contract.models import ImportDifference, ReportRefusal
from waterfall.core.planning.interface import designated, rebased_lines
from waterfall.core.planning.rebasing import rebase_plan
from waterfall.core.revisions.commands import RebaseState, rebase_conditions
from waterfall.core.revisions.interface import (
    StructureRebasing,
    differential_base,
    rebase_report,
)
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.core.planning.rebasing import RebasePlan
    from waterfall.platform.database import Database

REFUSED = "STATE_FORBIDS_OPERATION"
FORMATION = "Formation"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


@pytest.fixture
def late(api: ContractClient, project: Costed) -> OutOfDate:
    """Give a differential out of date: the main structure moved on, the differential too."""
    return out_of_date(api, project)


def asked(api: ContractClient, project: Costed, structure_id: object) -> Any:
    """Ask for the report of the update of a structure of the current revision; give the answer."""
    path = f"{revision_path(project)}/structures/{structure_id}/rebase"
    return api.get(path, headers=project.stage.manager.headers)


def report(api: ContractClient, late: OutOfDate) -> dict[str, Any]:
    """Read the report of the update of the differential out of date, which must be given."""
    answer = asked(api, late.project, late.structure_id)
    assert answer.status_code == 200, answer.text
    return answer.json()


def difference(
    change: str, target: str, named: tuple[str, str], fields: list[str] | None = None
) -> dict[str, Any]:
    """Write a difference as the report gives it, of a task or of a line."""
    lineage_id, label = named
    return {
        "change": change,
        "target": target,
        "lineage_id": lineage_id,
        "label": label,
        "predecessor_label": None,
        "fields": fields or [],
    }


def linked(change: str, successor: tuple[str, str], predecessor: str) -> dict[str, Any]:
    """Write a difference of a link, named by its successor, its predecessor's label beside."""
    return {**difference(change, "link", successor), "predecessor_label": predecessor}


def lineage(tree: Any, label: str) -> str:
    """Give the lineage of a node of a structure, by its label."""
    return node_labelled(tree, label)["lineage_id"]


def counters(api: ContractClient, project: Costed) -> dict[str, int]:
    """Read the counter of each structure of the current revision, by its identifier."""
    return {each["structure_id"]: each["lock_version"] for each in listed(api, project)}


def refusal(answer: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = answer.json()
    return answer.status_code, body["code"], body.get("params", {})


def rebasing(project: Costed, structure_id: str, session: Any) -> StructureRebasing:
    """Give the update of a differential of the current revision, as its report asks it."""
    base = differential_base(session, project.project_id, UUID(structure_id))
    assert base is not None
    return StructureRebasing(
        session,
        project.project_id,
        project.revision_id,
        project.structure_id,
        UUID(structure_id),
        base,
        Act(None, utc_now()),
        applying=False,
    )


def planned(project: Costed, structure_id: str) -> RebasePlan:
    """Give the plan of the update of a differential, every task it places held once.

    The tasks the plan orders are those it places, and the ends of each link it leaves among them.
    """
    with project.stage.database.transaction() as session:
        plan = rebase_plan(rebasing(project, structure_id, session))
    assert sorted(plan.order) == sorted(plan.parents)
    assert {end for pair in plan.links for end in pair} <= set(plan.order)
    return plan


def placed_under(api: ContractClient, project: Costed, tree: Any, label: str, parent: str) -> None:
    """Move the node of a structure that bears a label under the task that bears another."""
    sent = {
        "node_ids": [node_labelled(tree, label)["node_id"]],
        "parent_id": node_labelled(tree, parent)["node_id"],
        "lock_version": counters(api, project)[tree.structure_id],
    }
    moved = api.post(f"{tree.path}/nodes/move", headers=project.stage.manager.headers, json=sent)
    assert moved.status_code == 200, moved.text


# --- What the update carries ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_report_gives_what_the_main_structure_received_and_writes_nothing(
    api: ContractClient, late: OutOfDate
) -> None:
    # « getStructureRebaseReport est une lecture qui n'écrit rien : ce que la mise à jour
    # reporterait de la structure principale dans le différentiel — tâches, liaisons et lignes
    # ajoutées, modifiées avec leurs champs, retirées —, […] et les compteurs lus des deux
    # structures »: the task the main structure added, under its lineage, the label it changed, the
    # line it re-estimated, the task it removed; nothing of what the differential designates.
    project, main = late.project, late.project.tree
    held = counters(api, project)
    headers = project.stage.manager.headers
    before = (main.read().json(), late.amendment.read().json())
    revision = api.get(revision_path(project), headers=headers).json()
    found = report(api, late)
    assert found == {
        "main_structure_lock_version": held[main.structure_id],
        "structure_lock_version": held[late.structure_id],
        "differences": [
            difference("added", "task", (lineage(main, MAIN_ADDED), MAIN_ADDED)),
            difference(
                "updated", "task", (lineage(main, MAIN_RENAMED[1]), MAIN_RENAMED[1]), ["label"]
            ),
            difference(
                "updated",
                "estimate_line",
                (lineage(main, MAIN_REESTIMATED[0]), MAIN_REESTIMATED[0]),
                ["unit_disbursement"],
            ),
            difference("removed", "task", (lineage(late.amendment, MAIN_REMOVED), MAIN_REMOVED)),
        ],
        "refusals": [],
    }
    # Nothing is written: the structures, their counters, their nodes and the revision.
    assert counters(api, project) == held
    assert (main.read().json(), late.amendment.read().json()) == before
    assert api.get(revision_path(project), headers=headers).json() == revision


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_parts_of_the_modules_are_those_of_the_contract(late: OutOfDate) -> None:
    # « chaque réponse est validée contre le contrat dans les tests du service »: what the planning
    # and the estimate give of an update, before the API reads it, is of the models of the
    # contract, each key one they declare — a kept link among them.
    project = late.project
    essais = node_labelled(late.amendment, OWN_ADDED)
    documentation = node_labelled(late.amendment, MAIN_REMOVED)
    assert link(late.amendment, essais, project.stage.manager, documentation).status_code == 200
    with project.stage.database.transaction() as session:
        found = rebase_report(
            session,
            (project.project_id, project.revision_id, UUID(late.structure_id)),
            Act(project.stage.manager.user_id, utc_now()),
        ).found
    assert found.differences
    for part in found.differences:
        ImportDifference.model_validate(part)
        assert set(part) <= set(ImportDifference.model_fields), part
    for part in found.refusals:
        ReportRefusal.model_validate(part)


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_main_structure_adds_changes_or_removes_is_carried(
    api: ContractClient, project: Costed
) -> None:
    # « tâches, liaisons et lignes ajoutées, modifiées avec leurs champs, retirées »: a link the
    # main structure adds between two tasks the differential holds; one whose lag it changes, by
    # the column that presents it; then the same removed, the differential not having changed it.
    main, manager = project.tree, project.stage.manager
    main.made("Essais")
    assert (
        link(main, node_labelled(main, MAKING), manager, node_labelled(main, STUDY)).status_code
        == 200
    )
    structure_id = opened_amendment(api, project)
    late = OutOfDate(project, structure_id, on(main, structure_id))
    making = node_labelled(main, MAKING)
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": node_labelled(main, STUDY)["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "2", "unit": "d"},
            }
        ],
        "lock_version": making["lock_version"],
    }
    path = f"{main.path}/nodes/{making['node_id']}/predecessors"
    assert api.put(path, headers=manager.headers, json=sent).status_code == 200
    assert (
        link(main, node_labelled(main, "Essais"), manager, node_labelled(main, MAKING)).status_code
        == 200
    )
    assert report(api, late)["differences"] == [
        linked("added", (lineage(main, "Essais"), "Essais"), MAKING),
        {**linked("updated", (lineage(main, MAKING), MAKING), STUDY), "fields": ["predecessors"]},
    ]
    assert link(main, node_labelled(main, MAKING), manager).status_code == 200
    assert report(api, late)["differences"] == [
        linked("added", (lineage(main, "Essais"), "Essais"), MAKING),
        linked("removed", (lineage(main, MAKING), MAKING), STUDY),
    ]


# --- The four rules -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_value_both_change_keeps_the_differential_s_and_the_report_names_it(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une valeur que le différentiel désigne et que la structure principale a changée depuis
    # garde la valeur du différentiel, et le compte rendu la nomme (kept, ses champs) »: the label
    # of a task both rename, the unit disbursement of a line both change — the main structure's
    # re-estimate kept there, the differential's figure the reference of the merge (WF-REV-0050);
    # a value both change alike is no conflict, and is not named.
    main, own = late.project.tree, late.amendment
    main.changed(node_labelled(main, OWN_RENAMED[0]), label="Formation interne")
    Lines(own).changed(node_labelled(own, MAIN_REESTIMATED[0]), unit_disbursement="300.00")
    Lines(own).changed(node_labelled(own, "Plans"), label="Plans d'ensemble")
    Lines(main).changed(node_labelled(main, "Plans"), label="Plans d'ensemble")
    found = report(api, late)["differences"]
    kept = [each for each in found if each["change"] == "kept"]
    assert kept == [
        difference("kept", "task", (lineage(own, OWN_RENAMED[1]), OWN_RENAMED[1]), ["label"]),
        difference(
            "kept",
            "estimate_line",
            (lineage(own, MAIN_REESTIMATED[0]), MAIN_REESTIMATED[0]),
            ["unit_disbursement"],
        ),
    ]
    updated = [each["label"] for each in found if each["change"] == "updated"]
    assert updated == [MAIN_RENAMED[1]]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_task_the_differential_modifies_and_the_main_removes_stays_signalled(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche que le différentiel modifie et que la structure principale n'a plus reste au
    # différentiel, qui la présente ensuite added, signalée de même »: the task renamed in the
    # differential, removed from the main structure, is kept, not removed; the update leaves it.
    # Its line, which the differential did not touch, leaves with what the main structure removed.
    structure_id = opened_amendment(api, project)
    own = on(project.tree, structure_id)
    own.changed(node_labelled(own, MAKING), label="Réalisation reprise")
    deleted(project.tree, MAKING, project.stage.manager)
    late = OutOfDate(project, structure_id, own)
    found = report(api, late)["differences"]
    assert found == [
        difference("removed", "estimate_line", (lineage(own, "Fabrication"), "Fabrication")),
        difference("kept", "task", (lineage(own, "Réalisation reprise"), "Réalisation reprise")),
    ]
    with project.stage.database.transaction() as session:
        where = rebased_lines(rebasing(project, structure_id, session))
    assert UUID(lineage(own, "Réalisation reprise")) in where.tasks


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_line_the_differential_modifies_and_the_main_removes_stays_signalled(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche ou une ligne que le différentiel modifie et que la principale n'a plus reste au
    # différentiel »: the line whose quantity the differential changes stays, signalled, under its
    # task, which both still hold.
    structure_id = opened_amendment(api, project)
    own = on(project.tree, structure_id)
    Lines(own).changed(node_labelled(own, "Plans"), quantity="2")
    deleted(project.tree, "Plans", project.stage.manager)
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [difference("kept", "estimate_line", (lineage(own, "Plans"), "Plans"))]


@pytest.mark.requirement("WF-REV-0100-A")
def test_what_the_differential_adds_under_a_task_that_leaves_goes_to_its_nearest_ancestor(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche qu'il ajoute sous une tâche que la structure principale n'a plus passe sous
    # l'ancêtre le plus proche qui reste, signalée »: a subtask and a line the differential adds
    # under a subtask the main structure removes go under its parent, each kept, at the place the
    # subtask held among its siblings; the subtask removed is the main structure's removal.
    main, manager = project.tree, project.stage.manager
    lot = node_labelled(main, STUDY)
    main.made("Relevés", parent_id=lot["node_id"])
    main.made("Synthèse", parent_id=lot["node_id"])
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    surveys = node_labelled(own, "Relevés")
    own.made("Relevés complémentaires", parent_id=surveys["node_id"])
    Lines(own).made(surveys, **material(project.costs, "Mire", "20.00"))
    deleted(main, "Relevés", manager)
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [
        difference("removed", "task", (lineage(own, "Relevés"), "Relevés")),
        difference(
            "kept",
            "task",
            (lineage(own, "Relevés complémentaires"), "Relevés complémentaires"),
        ),
        difference("kept", "estimate_line", (lineage(own, "Mire"), "Mire")),
    ]
    with project.stage.database.transaction() as session:
        updating = rebasing(project, structure_id, session)
        where = rebased_lines(updating)
    study = UUID(lineage(own, STUDY))
    assert where.staying[UUID(lineage(own, "Relevés"))] == study
    assert UUID(lineage(own, "Relevés complémentaires")) in where.tasks
    plan = planned(project, structure_id)
    labels = [plan.label_of(each) for each in plan.order]
    assert labels == [STUDY, "Relevés complémentaires", "Synthèse", MAKING]
    assert plan.parents[UUID(lineage(own, "Relevés complémentaires"))] == study


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_task_the_differential_adds_under_a_first_level_task_that_leaves_goes_to_the_top(
    api: ContractClient, late: OutOfDate
) -> None:
    # « passe sous l'ancêtre le plus proche qui reste, ou au premier niveau »: the subtask the
    # differential adds under the task the main structure removes, of the first level, is kept at
    # the first level.
    own = late.amendment
    own.made("Notice", parent_id=node_labelled(own, MAIN_REMOVED)["node_id"])
    found = report(api, late)["differences"]
    assert difference("kept", "task", (lineage(own, "Notice"), "Notice")) in found
    assert difference("removed", "task", (lineage(own, MAIN_REMOVED), MAIN_REMOVED)) in found


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_differential_adds_to_a_task_that_leaves_is_removed_signalled(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une liaison qu'il ajoute vers une tâche que la structure principale n'a plus est retirée,
    # signalée »: the link from the task the main structure removes to the task the differential
    # adds is kept — removed from the differential, signalled —, named by its successor.
    own = late.amendment
    essais = node_labelled(own, OWN_ADDED)
    documentation = node_labelled(own, MAIN_REMOVED)
    assert link(own, essais, late.project.stage.manager, documentation).status_code == 200
    found = report(api, late)["differences"]
    assert linked("kept", (lineage(own, OWN_ADDED), OWN_ADDED), MAIN_REMOVED) in found
    assert found[-1] == linked("kept", (lineage(own, OWN_ADDED), OWN_ADDED), MAIN_REMOVED)


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_differential_adds_to_a_task_it_keeps_by_the_rule_2_stays(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une liaison qu'il ajoute vers une tâche que la structure principale n'a plus est retirée,
    # signalée », judged on the differential the update leaves: the task the main structure
    # removes, which the differential renames, stays (« une tâche que le différentiel modifie et
    # que la structure principale n'a plus reste au différentiel »), and the link to it with it.
    own = late.amendment
    own.changed(node_labelled(own, MAIN_REMOVED), label="Documentation reprise")
    essais = node_labelled(own, OWN_ADDED)
    documentation = node_labelled(own, "Documentation reprise")
    assert link(own, essais, late.project.stage.manager, documentation).status_code == 200
    found = report(api, late)["differences"]
    named = (lineage(own, "Documentation reprise"), "Documentation reprise")
    assert difference("kept", "task", named) in found
    assert not [each for each in found if each["target"] == "link"]
    plan = planned(late.project, late.structure_id)
    assert (UUID(named[0]), UUID(lineage(own, OWN_ADDED))) in plan.links


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_differential_retypes_and_the_main_removes_stays_signalled(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche ou une ligne que le différentiel modifie et que la principale n'a plus reste au
    # différentiel », for a link: the differential makes the link from Étude to Réalisation start
    # to start, the main structure removes it; the update leaves the differential's, signalled.
    main = project.tree
    lagged(main, MAKING, {STUDY: "0"})
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    lagged(own, MAKING, {STUDY: "0"}, "start_to_start")
    lagged(main, MAKING, {})
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [linked("kept", (lineage(main, MAKING), MAKING), STUDY)]
    plan = planned(project, structure_id)
    pair = (UUID(lineage(main, STUDY)), UUID(lineage(main, MAKING)))
    assert plan.links[pair].link_type == "start_to_start"


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_line_the_main_adds_to_a_task_the_differential_removes_goes_to_its_nearest_ancestor(
    api: ContractClient, project: Costed
) -> None:
    # « un nœud que la principale a ajouté y entre sous sa lignée, à sa place »: a line the main
    # structure adds to a subtask the differential removes enters under the subtask's parent, as a
    # task would; one it adds to a task of the first level the differential removes has no task
    # to enter under, and does not enter, as a link to it does not.
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
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [difference("added", "estimate_line", (lineage(main, "Grue"), "Grue"))]
    with project.stage.database.transaction() as session:
        where = rebased_lines(rebasing(project, structure_id, session))
    assert where.staying[UUID(lineage(main, "Montage"))] == UUID(lineage(main, STUDY))
    assert where.staying[UUID(lineage(main, "Documentation"))] is None


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_dates_the_main_changes_of_a_task_the_differential_makes_automatic_are_not_carried(
    api: ContractClient, project: Costed
) -> None:
    # « une valeur qu'elle a changée y est changée »: the dates of a task are its own in manual
    # mode only; the differential makes Réalisation automatic, the main structure moves its
    # finish, and its duration with it: the update, which leaves it automatic, carries the
    # duration, and no date of it, nor names one.
    main = project.tree
    task = node_labelled(main, MAKING)["task"]
    start, finish = task["start"], task["finish"]
    main.changed(node_labelled(main, MAKING), scheduling_mode="manual", start=start, finish=finish)
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    own.changed(node_labelled(own, MAKING), scheduling_mode="automatic")
    later = date.fromisoformat(finish["date"]) + timedelta(days=7)
    main.changed(node_labelled(main, MAKING), finish={**finish, "date": later.isoformat()})
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [difference("updated", "task", (lineage(own, MAKING), MAKING), ["duration"])]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_node_both_remove_is_not_signalled(api: ContractClient, project: Costed) -> None:
    # « Un nœud que le différentiel retire et que la principale n'a plus ne se signale pas. »: the
    # task removed on both sides is named by no difference, nor its line.
    structure_id = opened_amendment(api, project)
    own = on(project.tree, structure_id)
    deleted(own, MAKING, project.stage.manager)
    deleted(project.tree, MAKING, project.stage.manager)
    assert report(api, OutOfDate(project, structure_id, own))["differences"] == []


def lagged(
    tree: Any, successor: str, lags: dict[str, str], link_type: str = "finish_to_start"
) -> None:
    """Give a task of a structure its predecessors, of a type, each with its lag in days."""
    node = node_labelled(tree, successor)
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": node_labelled(tree, label)["node_id"],
                "link_type": link_type,
                "lag": {"value": lag, "unit": "d"},
            }
            for label, lag in lags.items()
        ],
        "lock_version": node["lock_version"],
    }
    path = f"{tree.path}/nodes/{node['node_id']}/predecessors"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_both_change_keeps_the_differential_s_and_one_it_changes_stays(
    api: ContractClient, project: Costed
) -> None:
    # « une valeur que le différentiel désigne et que la structure principale a changée depuis
    # garde la valeur du différentiel […] (kept, ses champs) », for the lag of a link, by the
    # column that presents it; a link the differential changes and the main structure removes
    # stays, signalled as a task or a line the differential modifies does; a link both add alike
    # is no difference, one both add otherwise keeps the differential's.
    main = project.tree
    main.made("Essais")
    main.made("Recette")
    lagged(main, MAKING, {STUDY: "0"})
    lagged(main, "Essais", {MAKING: "0"})
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    lagged(own, MAKING, {STUDY: "2"})
    lagged(own, "Essais", {MAKING: "1"})
    lagged(own, "Recette", {"Essais": "0", STUDY: "1"})
    lagged(main, MAKING, {STUDY: "3"})
    lagged(main, "Essais", {})
    lagged(main, "Recette", {"Essais": "0", STUDY: "2"})
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert sorted(found, key=lambda each: each["label"]) == [
        linked("kept", (lineage(main, "Essais"), "Essais"), MAKING),
        {
            **linked("kept", (lineage(main, "Recette"), "Recette"), STUDY),
            "fields": ["predecessors"],
        },
        {**linked("kept", (lineage(main, MAKING), MAKING), STUDY), "fields": ["predecessors"]},
    ]


@pytest.mark.requirement("WF-REV-0100-A")
def test_what_the_main_adds_to_a_task_the_differential_removes_goes_to_its_nearest_ancestor(
    api: ContractClient, late: OutOfDate
) -> None:
    # « un nœud que la principale a ajouté y entre sous sa lignée, à sa place »: a task the main
    # structure adds under a task the differential removed enters it under the nearest ancestor
    # that remains, the first level here, and its line with it; a link the main structure adds to
    # the task the differential removed does not enter it, and is not named.
    project, main = late.project, late.project.tree
    removed = node_labelled(main, "Montage")
    lifting = main.made("Levage", parent_id=removed["node_id"])
    Lines(main).made(lifting, **material(project.costs, "Grue", "80.00"))
    lagged(main, FORMATION, {"Montage": "0"})
    found = report(api, late)["differences"]
    assert difference("added", "task", (lifting["lineage_id"], "Levage")) in found
    assert difference("added", "estimate_line", (lineage(main, "Grue"), "Grue")) in found
    assert not [each for each in found if each["target"] == "link"]
    with project.stage.database.transaction() as session:
        plan = rebase_plan(rebasing(project, late.structure_id, session))
        where = rebased_lines(rebasing(project, late.structure_id, session))
    assert plan.parents[UUID(lifting["lineage_id"])] is None
    assert UUID(lifting["lineage_id"]) in where.tasks


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_task_the_main_adds_takes_its_place_after_the_sibling_that_precedes_it(
    api: ContractClient, late: OutOfDate
) -> None:
    # « un nœud que la principale a ajouté y entre sous sa lignée, à sa place »: the main
    # structure's task, last of its first level, follows in the differential the last of its
    # siblings the differential still holds, before the task the differential added; a task the
    # main structure moves under another is placed there likewise.
    project, main, own = late.project, late.project.tree, late.amendment
    sent = {
        "node_ids": [node_labelled(main, FORMATION)["node_id"]],
        "parent_id": node_labelled(main, MAIN_RENAMED[1])["node_id"],
        "lock_version": counters(api, project)[main.structure_id],
    }
    moved = api.post(f"{main.path}/nodes/move", headers=project.stage.manager.headers, json=sent)
    assert moved.status_code == 200, moved.text
    found = report(api, late)["differences"]
    assert difference("kept", "task", (lineage(own, OWN_RENAMED[1]), OWN_RENAMED[1])) not in found
    with project.stage.database.transaction() as session:
        plan = rebase_plan(rebasing(project, late.structure_id, session))
    labels = [plan.label_of(each) for each in plan.order]
    assert labels == [MAIN_RENAMED[1], OWN_RENAMED[1], MAKING, MAIN_ADDED, OWN_ADDED]
    assert plan.parents[UUID(lineage(own, OWN_RENAMED[1]))] == UUID(lineage(own, STUDY))


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_move_of_the_main_that_would_close_a_loop_of_the_hierarchy_keeps_the_differential_s(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une valeur que le différentiel désigne et que la structure principale a changée depuis
    # garde la valeur du différentiel, et le compte rendu la nomme (kept, ses champs) », for a
    # parent the two moves would make a loop of: the differential moves Formation under
    # Réalisation, the main structure Réalisation under Formation. The differential's move wins;
    # Réalisation stays at the first level, kept, its parent named; both stay in the plan.
    project, main, own = late.project, late.project.tree, late.amendment
    placed_under(api, project, own, OWN_RENAMED[1], MAKING)
    placed_under(api, project, main, MAKING, OWN_RENAMED[0])
    found = report(api, late)["differences"]
    making = (lineage(own, MAKING), MAKING)
    assert difference("kept", "task", making, ["parent"]) in found
    assert difference("updated", "task", making, ["parent"]) not in found
    plan = planned(project, late.structure_id)
    assert plan.parents[UUID(making[0])] is None
    assert plan.parents[UUID(lineage(own, OWN_RENAMED[1]))] == UUID(making[0])


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_task_the_differential_moves_under_a_task_that_leaves_goes_to_its_nearest_ancestor(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche qu'il ajoute sous une tâche que la structure principale n'a plus passe sous
    # l'ancêtre le plus proche qui reste, signalée », for a task of the base the differential moves
    # under a subtask the main structure removes: it goes under the subtask's parent, kept, its
    # parent named.
    main = project.tree
    main.made("Montage", parent_id=node_labelled(main, STUDY)["node_id"])
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    placed_under(api, project, own, MAKING, "Montage")
    deleted(main, "Montage", project.stage.manager)
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [
        difference("removed", "task", (lineage(own, "Montage"), "Montage")),
        difference("kept", "task", (lineage(own, MAKING), MAKING), ["parent"]),
    ]
    plan = planned(project, structure_id)
    assert plan.parents[UUID(lineage(own, MAKING))] == UUID(lineage(own, STUDY))


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_line_the_differential_moves_under_a_task_that_leaves_goes_to_its_nearest_ancestor(
    api: ContractClient, project: Costed
) -> None:
    # « une tâche ou une ligne que le différentiel ajoute sous une tâche que la principale n'a
    # plus […] passe sous l'ancêtre le plus proche qui reste », for a line of the base the
    # differential attaches to a subtask the main structure removes: it goes under the subtask's
    # parent, kept, its parent named.
    main = project.tree
    main.made("Montage", parent_id=node_labelled(main, STUDY)["node_id"])
    structure_id = opened_amendment(api, project)
    own = on(main, structure_id)
    placed_under(api, project, own, "Fabrication", "Montage")
    deleted(main, "Montage", project.stage.manager)
    found = report(api, OutOfDate(project, structure_id, own))["differences"]
    assert found == [
        difference("removed", "task", (lineage(own, "Montage"), "Montage")),
        difference(
            "kept", "estimate_line", (lineage(own, "Fabrication"), "Fabrication"), ["parent"]
        ),
    ]
    with project.stage.database.transaction() as session:
        where = rebased_lines(rebasing(project, structure_id, session))
    assert where.staying[UUID(lineage(own, "Montage"))] == UUID(lineage(own, STUDY))


# --- The refusals ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_loop_the_update_would_close_is_named_by_the_nodes_of_the_differential(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une mise à jour qui laisserait dans le différentiel une boucle de liaisons […] est refusée,
    # le motif et la tâche nommés au compte rendu (ReportRefusal) »: the main structure makes
    # Réalisation follow Étude, the differential makes Étude follow Réalisation — each alone
    # without a loop —; the tasks named by their node in the differential, from the first in the
    # order of the plan.
    project, main, own = late.project, late.project.tree, late.amendment
    manager = project.stage.manager
    making = node_labelled(main, MAKING)
    assert link(main, making, manager, node_labelled(main, MAIN_RENAMED[1])).status_code == 200
    study = node_labelled(own, STUDY)
    assert link(own, study, manager, node_labelled(own, MAKING)).status_code == 200
    found = report(api, late)
    assert linked("added", (lineage(main, MAKING), MAKING), MAIN_RENAMED[1]) in found["differences"]
    assert found["refusals"] == [
        {
            "code": "LINK_CYCLE",
            "params": {
                "cycle": [
                    {"node_id": study["node_id"], "label": MAIN_RENAMED[1]},
                    {"node_id": node_labelled(own, MAKING)["node_id"], "label": MAKING},
                ]
            },
        }
    ]
    # « le lien fautif retiré du différentiel, elle aboutit »
    assert link(own, node_labelled(own, STUDY), manager).status_code == 200
    assert report(api, late)["refusals"] == []


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_link_the_update_would_put_across_the_hierarchy_is_named_the_summary_first(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une liaison interdite »: the main structure moves Réalisation under Étude, the differential
    # makes Réalisation follow Étude: a link between a summary and its subordinate (WF-PLA-0030).
    project, main, own = late.project, late.project.tree, late.amendment
    manager = project.stage.manager
    sent = {
        "node_ids": [node_labelled(main, MAKING)["node_id"]],
        "parent_id": node_labelled(main, MAIN_RENAMED[1])["node_id"],
        "lock_version": counters(api, project)[main.structure_id],
    }
    moved = api.post(f"{main.path}/nodes/move", headers=manager.headers, json=sent)
    assert moved.status_code == 200, moved.text
    making = node_labelled(own, MAKING)
    assert link(own, making, manager, node_labelled(own, STUDY)).status_code == 200
    found = report(api, late)
    assert (
        difference("updated", "task", (lineage(main, MAKING), MAKING), ["parent"])
        in found["differences"]
    )
    assert found["refusals"] == [
        {
            "code": "LINK_FORBIDDEN",
            "params": {
                "link": [
                    {"node_id": node_labelled(own, STUDY)["node_id"], "label": MAIN_RENAMED[1]},
                    {"node_id": making["node_id"], "label": MAKING},
                ]
            },
        }
    ]
    # « le lien fautif retiré du différentiel, elle aboutit »
    assert link(own, node_labelled(own, MAKING), manager).status_code == 200
    assert report(api, late)["refusals"] == []


@pytest.mark.requirement("WF-REV-0100-A")
def test_an_update_beyond_the_horizon_names_the_task_that_finishes_last(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une date au-delà de l'horizon »: the duration of a task of the differential, around the
    # service, which its entry refuses; the task named by its node in the differential.
    own = late.amendment
    making = node_labelled(own, MAKING)
    put_facts(late.project.stage, making["node_id"], duration_value=Decimal(6000))
    assert report(api, late)["refusals"] == [
        {
            "code": "PROJECT_HORIZON_EXCEEDED",
            "params": {"task": {"node_id": making["node_id"], "label": MAKING}},
        }
    ]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_task_whose_roles_the_update_would_leave_without_hours_is_named(
    api: ContractClient, late: OutOfDate
) -> None:
    # « une tâche sans heure travaillée »: the main structure gives Formation a welder on
    # weekdays, the differential a fitter on the weekend — each alone working —; together they
    # share no hour (WF-PLA-0010), the roles and the task named by its node in the differential.
    project, main, own = late.project, late.project.tree, late.amendment
    welder = add_role(project.stage.database, "SOUD", (8, 8, 8, 8, 8, 0, 0))
    fitter = add_role(project.stage.database, "MONT", (0, 0, 0, 0, 0, 8, 8))
    for tree, role, label in ((main, welder, "Soudure"), (own, fitter, "Montage week-end")):
        task = node_labelled(tree, OWN_RENAMED[1] if tree is own else FORMATION)
        line = {"label": label, "quantity": "1", "resource_role_id": str(role), "hours": "4"}
        Lines(tree).made(task, **line)
    found = report(api, late)
    assert (
        difference("added", "estimate_line", (lineage(main, "Soudure"), "Soudure"))
        in found["differences"]
    )
    [refused] = found["refusals"]
    assert refused["code"] == "TASK_WITHOUT_WORKING_HOURS"
    assert {each["resource_role_id"] for each in refused["params"]["resource_roles"]} == {
        str(welder),
        str(fitter),
    }
    assert refused["params"]["tasks"] == [
        {
            "project_id": str(project.project_id),
            "node_id": node_labelled(own, OWN_RENAMED[1])["node_id"],
            "label": OWN_RENAMED[1],
        }
    ]


# --- What has no report ---------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_structure_that_is_no_differential_out_of_date_has_the_409_of_its_update(
    api: ContractClient, project: Costed
) -> None:
    # « une structure qui n'est pas un différentiel en retard de la révision en cours reçoit le
    # 409 de sa mise à jour »: the main structure and a merged differential lack
    # unmerged_amendment_exists, a differential up to date structure_out_of_date, any during a
    # background task no_background_task_running; an unknown structure and a base are not found.
    up_to_date = opened_amendment(api, project)
    merged = opened_amendment(api, project, "Avenant fusionné")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == UUID(merged)).values(is_merged=True)
        )
        base = connection.scalar(
            select(CostStructure.id).where(CostStructure.differential_id == UUID(up_to_date))
        )
    lacking = {"missing_condition": "unmerged_amendment_exists"}
    assert refusal(asked(api, project, project.structure_id)) == (409, REFUSED, lacking)
    assert refusal(asked(api, project, merged)) == (409, REFUSED, lacking)
    current = {"missing_condition": "structure_out_of_date"}
    assert refusal(asked(api, project, up_to_date)) == (409, REFUSED, current)
    assert asked(api, project, project.project_id).status_code == 404
    assert asked(api, project, base).status_code == 404
    project.tree.made("Recette")
    assert asked(api, project, up_to_date).status_code == 200
    started_marking(api, project)
    running = {"missing_condition": "no_background_task_running"}
    assert refusal(asked(api, project, up_to_date)) == (409, REFUSED, running)


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_of_a_marked_revision_or_a_terminal_project_has_no_report(
    api: ContractClient, project: Costed
) -> None:
    # « une structure qui n'est pas un différentiel en retard de la révision en cours »: the last
    # marked revision of a project without a current one lacks revision_draft — the update waits
    # for the revision to be created —; a terminal project project_not_terminal, first.
    late = out_of_date(api, project)
    mark(project.stage, project.tree.revision)
    draft = {"missing_condition": "revision_draft"}
    assert refusal(asked(api, project, late.structure_id)) == (409, REFUSED, draft)
    put_in_state(project.stage.owner, str(project.project_id), "completed")
    terminal = {"missing_condition": "project_not_terminal"}
    assert refusal(asked(api, project, late.structure_id)) == (409, REFUSED, terminal)


# The update of a differential out of date of the current revision, all its conditions held.
HELD = RebaseState(
    terminal=False, current=True, no_task_running=True, differential=True, out_of_date=True
)


@pytest.mark.parametrize(
    ("state", "missing"),
    [
        (replace(HELD, terminal=True, current=False), ["project_not_terminal"]),
        (replace(HELD, current=False, no_task_running=False), ["revision_draft"]),
        (
            replace(HELD, no_task_running=False, differential=False, out_of_date=False),
            ["no_background_task_running", "unmerged_amendment_exists"],
        ),
        (replace(HELD, out_of_date=False), ["structure_out_of_date"]),
        (HELD, []),
    ],
)
@pytest.mark.requirement("WF-REV-0100-A")
def test_the_conditions_of_an_update_are_named_in_the_order_of_its_command(
    state: RebaseState, missing: list[str]
) -> None:
    # « la première condition qui manque nommée dans l'ordre du contrat »: those of the abandonment
    # in its order, then a differential already up to date.
    assert rebase_conditions(state) == missing


# --- What a structure designates ------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_what_a_structure_designates_is_its_gap_to_its_base_whatever_the_main_received(
    late: OutOfDate,
) -> None:
    # « Ce qu'une structure désigne est son écart à sa base, par la lignée »: the differential out
    # of date designates its addition, its modification, its removal, and nothing of what the main
    # structure received; the main structure, against the same base, what it received.
    project, own, main = late.project, late.amendment, late.project.tree
    with project.stage.database.transaction() as session:
        base = differential_base(session, project.project_id, UUID(late.structure_id))
        assert base is not None
        gap = designated(session, project.project_id, (base, UUID(late.structure_id)))
        received = designated(session, project.project_id, (base, project.structure_id))
    assert gap.added == {UUID(lineage(own, OWN_ADDED))}
    assert gap.changed == {UUID(lineage(own, OWN_RENAMED[1])): {"label"}}
    assert gap.removed == {UUID(lineage(main, OWN_REMOVED))}
    assert received.added == {UUID(lineage(main, MAIN_ADDED))}
    assert received.changed == {UUID(lineage(main, MAIN_RENAMED[1])): {"label"}}
    assert received.removed == {UUID(lineage(own, MAIN_REMOVED))}
