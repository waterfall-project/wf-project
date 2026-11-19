# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report before the merge of a differential (``getStructureMergeReport``; US-2560/L1).

A read that writes nothing: the differences of the differential with the main structure of its
revision, matched by lineage — tasks, lines and links added, updated, removed —, the started tasks
it removes, which the merge keeps and completes, the reasons that refuse it, judged once on the
structure the merge leaves, the counters of the two structures read and whether the merge creates
the current revision; a structure that is no differential to merge has the 409 of its merge. The
provision lines stay out of a differential and of its comparison (#4008), and one whose task the
merge removes goes to another task (WF-RIS-0010). Every answer is checked against the contract
(``ContractClient``), and the parts of the modules against its models (#3948).
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import listed, on, opened_amendment, revision_path, started_marking
from estimate_support import Costing, Lines, costing
from history_support import delete, link
from nodes_support import Tree, mark, opened, put_facts, set_progress, work_breakdown
from planning_support import insert_link
from projects_support import PROJECTS, Scene, contribute, person
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed, declared, material, material_line
from sqlalchemy import select, update

from waterfall.api.contract.models import ImportCompletedTask, ImportDifference, ReportRefusal
from waterfall.core.planning.interface import merged_lines
from waterfall.core.planning.tables import Node
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.commands import MergeState, merge_conditions
from waterfall.core.revisions.interface import StructureMerging, merge_report
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

DAY = date(2026, 3, 2)
REFUSED = "STATE_FORBIDS_OPERATION"


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


def asked(api: ContractClient, project: Costed, structure_id: object, who: Any = None) -> Any:
    """Ask for the report of the merge of a structure of the current revision; give the answer."""
    path = f"{revision_path(project)}/structures/{structure_id}/merge"
    return api.get(path, headers=(who or project.stage.manager).headers)


def report(api: ContractClient, project: Costed, structure_id: object) -> dict[str, Any]:
    """Read the report of the merge of a differential, which must be given."""
    answer = asked(api, project, structure_id)
    assert answer.status_code == 200, answer.text
    return answer.json()


def node_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read a node of a structure by its label, a task's or a line's."""
    found = [
        each for each in tree.items() if (each["task"] or each["estimate_line"])["label"] == label
    ]
    assert len(found) == 1, label
    return found[0]


def lineage(project: Costed, label: str) -> str:
    """Give the lineage of a node of the main structure, by its label."""
    return node_of(project.tree, label)["lineage_id"]


def difference(
    change: str, target: str, named: tuple[str | None, str], fields: list[str] | None = None
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


def counters(api: ContractClient, project: Costed) -> dict[str, int]:
    """Read the counter of each structure of the current revision, by its identifier."""
    return {each["structure_id"]: each["lock_version"] for each in listed(api, project)}


def refusal(answer: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = answer.json()
    return answer.status_code, body["code"], body.get("params", {})


# --- The differences ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_report_gives_the_differences_of_a_differential_and_writes_nothing(
    api: ContractClient, project: Costed
) -> None:
    # « getStructureMergeReport est une lecture qui n'écrit rien : les écarts du différentiel à la
    # principale (ImportDifference) […], les compteurs lus de la principale et du différentiel, et
    # creates_current_revision »: a task and its line added, a link added, a task renamed, a line
    # whose quantity changes, a line removed — the dates the edits move are computed, not named.
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    lines = Lines(tree)
    manager = project.stage.manager
    tests = tree.made("Essais")
    lines.made(tests, **material(project.costs, "Banc d'essai", "50.00"))
    tree.changed(node_of(tree, MAKING), label="Réalisation et mise au point")
    lines.changed(node_of(tree, "Plans"), quantity="2")
    assert delete(tree, node_of(tree, "Fabrication"), manager).status_code == 200
    linked = link(tree, node_of(tree, "Essais"), manager, node_of(tree, STUDY))
    assert linked.status_code == 200, linked.text
    held = counters(api, project)
    headers = project.stage.manager.headers
    main_before = project.tree.read().json()
    revision_before = api.get(revision_path(project), headers=headers).json()
    found = report(api, project, amendment)
    added_link = {**difference("added", "link", (None, "Essais")), "predecessor_label": STUDY}
    assert found == {
        "main_structure_lock_version": held[project.tree.structure_id],
        "amendment_lock_version": held[amendment],
        "creates_current_revision": False,
        "differences": [
            difference("added", "task", (None, "Essais")),
            added_link,
            difference("added", "estimate_line", (None, "Banc d'essai")),
            difference(
                "updated",
                "task",
                (lineage(project, MAKING), "Réalisation et mise au point"),
                ["label"],
            ),
            difference(
                "updated", "estimate_line", (lineage(project, "Plans"), "Plans"), ["quantity"]
            ),
            difference(
                "removed", "estimate_line", (lineage(project, "Fabrication"), "Fabrication")
            ),
        ],
        "completed_tasks": [],
        "refusals": [],
    }
    # Nothing is written: the structures, their counters and the revision are as they were.
    assert counters(api, project) == held
    assert project.tree.read().json() == main_before
    assert api.get(revision_path(project), headers=headers).json() == revision_before


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_parts_of_the_modules_are_those_of_the_contract(
    api: ContractClient, project: Costed
) -> None:
    # « chaque réponse est validée contre le contrat dans les tests du service »: what the planning
    # and the estimate give of a merge, before the API reads it, is of the models of the contract,
    # each key one they declare (#3948).
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    set_progress(project.stage, str(project.tasks[MAKING]), "started", DAY)
    Lines(tree).made(tree.made("Essais"), **material(project.costs, "Banc d'essai", "50.00"))
    assert delete(tree, node_of(tree, MAKING), project.stage.manager).status_code == 200
    with project.stage.database.transaction() as session:
        found = merge_report(
            session,
            (project.project_id, project.revision_id, UUID(amendment)),
            Viewer(project.stage.manager.user_id, ("revisions.read",)),
            Act(project.stage.manager.user_id, utc_now()),
        ).found
    models = (
        (found.differences, ImportDifference),
        (found.completed_tasks, ImportCompletedTask),
        (found.refusals, ReportRefusal),
    )
    assert all(parts for parts, _ in models[:2])
    for parts, model in models:
        for part in parts:
            model.model_validate(part)
            assert set(part) <= set(model.model_fields), part


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_started_task_the_differential_removes_is_named_completed_and_nothing_changes(
    api: ContractClient, project: Costed
) -> None:
    # « Le compte rendu d'une fusion dont le différentiel retire une tâche démarrée nomme cette
    # tâche comme terminée ; l'abandon à cette étape laisse la révision en cours et la référence
    # inchangées. »: kept and signalled, among the completed tasks without a date, its line kept
    # with it; reading the report and not confirming writes nothing.
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    set_progress(project.stage, str(project.tasks[MAKING]), "started", DAY)
    assert delete(tree, node_of(tree, MAKING), project.stage.manager).status_code == 200
    project_path = f"{PROJECTS}/{project.project_id}"
    headers = project.stage.manager.headers
    before = (api.get(project_path, headers=headers).json(), counters(api, project))
    revision = api.get(revision_path(project), headers=headers).json()
    found = report(api, project, amendment)
    assert found["differences"] == [difference("kept", "task", (lineage(project, MAKING), MAKING))]
    assert found["completed_tasks"] == [
        {"lineage_id": lineage(project, MAKING), "label": MAKING, "completed_on": None}
    ]
    assert found["refusals"] == []
    assert (api.get(project_path, headers=headers).json(), counters(api, project)) == before
    assert api.get(revision_path(project), headers=headers).json() == revision
    assert before[0]["current_revision_id"] == str(project.revision_id)


# --- The refusals ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0170-A")
def test_a_differential_that_takes_an_order_item_out_of_its_work_package_is_refused_by_name(
    api: ContractClient, project: Costed
) -> None:
    # « La fusion d'un différentiel qui déplacerait la tâche d'un poste hors du sous-arbre de la
    # tâche de son lot est refusée en nommant la tâche. »: the report names the two tasks by their
    # node in the main structure and their label (ORDER_ITEM_OUTSIDE_WORK_PACKAGE).
    stage = project.stage
    package, item = work_breakdown(stage)
    study = str(project.tasks[STUDY])
    post = project.tree.made("Câblage", parent_id=study)
    put_facts(stage, study, work_package_id=package)
    put_facts(stage, post["node_id"], order_item_id=item)
    tree = on(project.tree, opened_amendment(api, project))
    sent = {
        "node_ids": [node_of(tree, "Câblage")["node_id"]],
        "parent_id": node_of(tree, MAKING)["node_id"],
        "lock_version": counters(api, project)[tree.structure_id],
    }
    moved = api.post(f"{tree.path}/nodes/move", headers=stage.manager.headers, json=sent)
    assert moved.status_code == 200, moved.text
    found = report(api, project, tree.structure_id)
    assert found["differences"] == [
        difference("updated", "task", (post["lineage_id"], "Câblage"), ["parent"])
    ]
    assert found["refusals"] == [
        {
            "code": "ORDER_ITEM_OUTSIDE_WORK_PACKAGE",
            "params": {
                "work_package_task": {"node_id": study, "label": STUDY},
                "order_item_tasks": [{"node_id": post["node_id"], "label": "Câblage"}],
            },
        }
    ]


def amendment_links(project: Costed, tree: Tree, *pairs: tuple[str, str]) -> None:
    """Write links between tasks of a differential around the service, which its entry refuses."""
    with project.stage.owner.begin() as connection:
        for predecessor, successor in pairs:
            connection.execute(
                insert_link(
                    project.project_id,
                    project.revision_id,
                    UUID(tree.structure_id),
                    UUID(node_of(tree, predecessor)["node_id"]),
                    UUID(node_of(tree, successor)["node_id"]),
                )
            )


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_loop_of_links_the_merge_would_close_is_named_and_the_horizon_left_unjudged(
    api: ContractClient, project: Costed
) -> None:
    # « les motifs qui la refusent — LINK_CYCLE […], chacun avec les paramètres que le contrat
    # dit »: the tasks of the loop by their node and their label, from the first in the order of
    # the plan; a loop leaves the dates without a calculation, and the horizon is not judged
    # however long a task lasts (#788).
    tree = on(project.tree, opened_amendment(api, project))
    amendment_links(project, tree, (STUDY, MAKING), (MAKING, STUDY))
    put_facts(project.stage, node_of(tree, MAKING)["node_id"], duration_value=Decimal(6000))
    assert report(api, project, tree.structure_id)["refusals"] == [
        {
            "code": "LINK_CYCLE",
            "params": {
                "cycle": [
                    {"node_id": str(project.tasks[STUDY]), "label": STUDY},
                    {"node_id": str(project.tasks[MAKING]), "label": MAKING},
                ]
            },
        }
    ]


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_link_between_a_summary_and_its_subordinate_is_named_the_summary_first(
    api: ContractClient, project: Costed
) -> None:
    # « LINK_FORBIDDEN »: the two tasks, the summary first, a task the differential adds by a null
    # node and its label.
    tree = on(project.tree, opened_amendment(api, project))
    tree.made("Sous-étude", parent_id=node_of(tree, STUDY)["node_id"])
    amendment_links(project, tree, (STUDY, "Sous-étude"))
    assert report(api, project, tree.structure_id)["refusals"] == [
        {
            "code": "LINK_FORBIDDEN",
            "params": {
                "link": [
                    {"node_id": str(project.tasks[STUDY]), "label": STUDY},
                    {"node_id": None, "label": "Sous-étude"},
                ]
            },
        }
    ]


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_merge_beyond_fifteen_years_names_the_task_that_finishes_last(
    api: ContractClient, project: Costed
) -> None:
    # « PROJECT_HORIZON_EXCEEDED »: the duration of the project beyond fifteen years, the task of
    # the structure merged that finishes last named by its node and its label; the duration the
    # differential gives it, around the service, which its entry refuses.
    tree = on(project.tree, opened_amendment(api, project))
    put_facts(project.stage, node_of(tree, MAKING)["node_id"], duration_value=Decimal(6000))
    found = report(api, project, tree.structure_id)
    assert found["differences"] == [
        difference("updated", "task", (lineage(project, MAKING), MAKING), ["duration"])
    ]
    assert found["refusals"] == [
        {
            "code": "PROJECT_HORIZON_EXCEEDED",
            "params": {"task": {"node_id": str(project.tasks[MAKING]), "label": MAKING}},
        }
    ]


# --- The provision lines --------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_provision_line_stays_out_of_a_differential_and_moves_when_its_task_is_removed(
    api: ContractClient, project: Costed
) -> None:
    # « une ligne de provision dont la fusion retire la tâche passe sur la tâche parente, et le
    # compte rendu le signale »: a differential does not take the provision line up at its opening,
    # and one it would hold is ignored (#4008): untouched, it has no difference; its task removed,
    # the line goes to the first task of the first level left, by an update of its parent.
    risk = declared(project)
    tree = on(project.tree, opened_amendment(api, project))
    with project.stage.owner.begin() as connection:
        provision = connection.scalar(
            select(Node.lineage_id).where(Node.id == risk.provision_node_id)
        )
        held = connection.scalar(
            select(Node.id).where(
                Node.structure_id == UUID(tree.structure_id), Node.lineage_id == provision
            )
        )
        assert held is None
        material_line(
            connection,
            (
                project.project_id,
                project.revision_id,
                UUID(tree.structure_id),
                UUID(node_of(tree, MAKING)["node_id"]),
            ),
            project.costs.provision,
            Decimal("60.00"),
        )
    assert report(api, project, tree.structure_id)["differences"] == []
    assert delete(tree, node_of(tree, STUDY), project.stage.manager).status_code == 200
    assert report(api, project, tree.structure_id)["differences"] == [
        difference("updated", "estimate_line", (str(provision), "Ligne"), ["parent"]),
        difference("removed", "task", (lineage(project, STUDY), STUDY)),
        difference("removed", "estimate_line", (lineage(project, "Plans"), "Plans")),
    ]


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_provision_of_a_subtask_removed_goes_to_its_parent_beside_its_links_and_attachment(
    api: ContractClient, project: Costed
) -> None:
    # « une ligne de provision dont la fusion retire la tâche passe sur la tâche parente »: the
    # subtask that bears it removed, its link removed with it, and the work package it bore named;
    # a link whose lag the differential changes is updated, by the column that presents it.
    stage = project.stage
    package, _ = work_breakdown(stage)
    study = node_of(project.tree, STUDY)
    wiring = project.tree.made("Câblage", parent_id=study["node_id"])
    put_facts(stage, wiring["node_id"], work_package_id=package)
    linked = link(project.tree, node_of(project.tree, MAKING), stage.manager, study, wiring)
    assert linked.status_code == 200, linked.text
    with stage.owner.begin() as connection:
        bearer = (project.project_id, project.revision_id, project.structure_id)
        provision = material_line(
            connection, (*bearer, UUID(wiring["node_id"])), project.costs.provision, Decimal(60)
        )
        provision_lineage = connection.scalar(select(Node.lineage_id).where(Node.id == provision))
    tree = on(project.tree, opened_amendment(api, project))
    making = node_of(tree, MAKING)
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": node_of(tree, STUDY)["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "2", "unit": "d"},
            }
        ],
        "lock_version": making["lock_version"],
    }
    path = f"{tree.path}/nodes/{making['node_id']}/predecessors"
    assert api.put(path, headers=stage.manager.headers, json=sent).status_code == 200
    assert delete(tree, node_of(tree, "Câblage"), stage.manager).status_code == 200
    assert report(api, project, tree.structure_id)["differences"] == [
        {
            **difference("updated", "link", (lineage(project, MAKING), MAKING), ["predecessors"]),
            "predecessor_label": STUDY,
        },
        difference("updated", "estimate_line", (str(provision_lineage), "Ligne"), ["parent"]),
        {
            **difference("removed", "link", (lineage(project, MAKING), MAKING)),
            "predecessor_label": "Câblage",
        },
        {
            **difference("removed", "task", (wiring["lineage_id"], "Câblage")),
            "work_breakdown_label": "Lot",
        },
    ]
    # The task it goes to, which the estimate reads of the plan of the planning: the parent.
    with stage.database.transaction() as session:
        merging = StructureMerging(
            session,
            project.project_id,
            project.revision_id,
            project.structure_id,
            UUID(tree.structure_id),
            Act(None, utc_now()),
            applying=False,
        )
        moved = merged_lines(merging).moved
    assert moved == {UUID(wiring["lineage_id"]): UUID(study["node_id"])}


# --- What has no report ---------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_structure_that_is_no_differential_to_merge_has_the_409_of_its_merge(
    api: ContractClient, project: Costed
) -> None:
    # « une structure qui n'est pas un différentiel fusionnable reçoit le 409 de sa fusion »: the
    # main structure, a merged differential, a differential while a background task runs; an
    # unknown structure is not found.
    merged = opened_amendment(api, project, "Avenant fusionné")
    amendment = opened_amendment(api, project)
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == UUID(merged)).values(is_merged=True)
        )
    lacking = {"missing_condition": "unmerged_amendment_exists"}
    assert refusal(asked(api, project, project.structure_id)) == (409, REFUSED, lacking)
    assert refusal(asked(api, project, merged)) == (409, REFUSED, lacking)
    assert asked(api, project, project.project_id).status_code == 404
    started_marking(api, project)
    running = {"missing_condition": "no_background_task_running"}
    assert refusal(asked(api, project, amendment)) == (409, REFUSED, running)


@pytest.mark.requirement("WF-REV-0050-A")
def test_without_a_current_revision_the_report_says_the_merge_creates_it(
    api: ContractClient, project: Costed, realm: TestRealm
) -> None:
    # « creates_current_revision »: a differential of the last marked revision of a project without
    # a current revision, its counters frozen by the marking; refused to whoever may not create a
    # revision (may_create_revision), and once a revision is current (revision_draft).
    stage = project.stage
    amendment = opened_amendment(api, project)
    mark(stage, project.tree.revision)
    held = counters(api, project)
    found = report(api, project, amendment)
    assert found["creates_current_revision"] is True
    assert (found["main_structure_lock_version"], found["amendment_lock_version"]) == (
        held[project.tree.structure_id],
        held[amendment],
    )
    reader = person(stage.database, realm, "revisions.read", "project_settings.read")
    contribute(stage.database, stage.project["project_id"], reader, "contributor")
    creating = {"missing_condition": "may_create_revision"}
    assert refusal(asked(api, project, amendment, reader)) == (409, REFUSED, creating)
    opened(api, stage)
    draft = {"missing_condition": "revision_draft"}
    assert refusal(asked(api, project, amendment)) == (409, REFUSED, draft)


# A merge on the current revision, all its conditions held; and on the last marked revision.
HELD = MergeState(
    terminal=False, current=True, source=False, no_task_running=True, mergeable=True, creates=False
)
SOURCE = replace(HELD, current=False, source=True, creates=True)


@pytest.mark.parametrize(
    ("state", "missing"),
    [
        (replace(HELD, terminal=True, mergeable=False), ["project_not_terminal"]),
        (replace(HELD, current=False, no_task_running=False), ["revision_draft"]),
        (
            replace(SOURCE, no_task_running=False, mergeable=False, creates=False),
            ["no_background_task_running", "unmerged_amendment_exists", "may_create_revision"],
        ),
        (HELD, []),
        (SOURCE, []),
    ],
)
@pytest.mark.requirement("WF-REV-0050-A")
def test_the_conditions_of_a_merge_are_named_in_the_order_of_its_command(
    state: MergeState, missing: list[str]
) -> None:
    # « les conditions de la commande merge_structure sont nommées dans l'ordre du contrat »: a
    # terminal project first, then a marked revision that does not create the current one; the
    # background task, the differential, the permission to create a revision for the last marked.
    assert merge_conditions(state) == missing
