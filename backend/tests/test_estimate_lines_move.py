# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line of an estimate deleted and moved, and what the reference asks of the lines (US-1490/L4).

``deleteNode`` of a line and of the task that bears it, ``moveNodes`` of lines, on the main
structure of the current revision of a project its manager made (``nodes_support``), its labour
category rated for the year of the revision and a category of material beside it
(``estimate_support``); then what the lines answer the other modules — the abandonment of a
revision (``register_closing``), the deletion of a subproject (``register_estimate_facts``), the
change of the nature of a category (``register_employment``). Every answer is checked against the
contract.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file; written by
US-1490/L4 ("Les tests du back").
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import YEAR, Costing, Lines, add_role, costing, give_a_line
from nodes_support import Tree, faults, mark, opened, refusal, set_progress
from planning_support import insert_link, insert_task
from project_rows import lifted_kind_check, structure_row
from projects_support import PROJECTS, Scene, person
from projects_support import scene as make_scene
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, insert, select, update

from waterfall.core.cost_settings.interface import CostCategoryDraft, create_cost_category
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CENT = Decimal("0.01")
STATE_FORBIDS = "STATE_FORBIDS_OPERATION"
COMPLETED = (409, STATE_FORBIDS, {"missing_condition": "task_not_completed"})
CATEGORIES = "/api/v1/reference/cost-categories"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def labour(role: UUID, **line: Any) -> dict[str, Any]:
    """Give a labour line of a role: one person for ten hours, unless said."""
    return {"quantity": "1", "resource_role_id": str(role), "hours": "10", **line}


def material(costs: Costing, **line: Any) -> dict[str, Any]:
    """Give a line of material: one at 350.00, unless said."""
    held = {"quantity": "1", "cost_category_id": str(costs.material), "unit_disbursement": "350.00"}
    return {**held, **line}


def delete(tree: Tree, node: dict[str, Any]) -> Any:
    """Delete a node at the counter read, as the manager does; give the answer."""
    path = f"{tree.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}"
    return tree.api.delete(path, headers=tree.stage.manager.headers)


def counter(tree: Tree) -> int:
    """Read the counter of the structure, which every write of its tree advances."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


def move_body(tree: Tree, nodes: list[dict[str, Any]], parent: str, **body: Any) -> dict[str, Any]:
    """Give the body of a move of nodes under a task, at the counter of the structure read."""
    return {
        "node_ids": [node["node_id"] for node in nodes],
        "parent_id": parent,
        "lock_version": counter(tree),
        **body,
    }


def move(tree: Tree, nodes: list[dict[str, Any]], parent: str, **body: Any) -> Any:
    """Move nodes under a task, as the manager does; give the answer."""
    sent = move_body(tree, nodes, parent, **body)
    return tree.api.post(f"{tree.path}/nodes/move", headers=tree.stage.manager.headers, json=sent)


def moved(tree: Tree, nodes: list[dict[str, Any]], parent: str, **body: Any) -> dict[str, Any]:
    """Move nodes that must move; give what is answered."""
    answer = move(tree, nodes, parent, **body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def stored(stage: Scene) -> int:
    """Count the lines the base keeps."""
    with stage.database.transaction() as session:
        return session.scalar(select(func.count()).select_from(EstimateLine)) or 0


def first_monday(year: int) -> date:
    """Give the first Monday of March of a year: a working day of every calendar of the scene."""
    day = date(year, 3, 1)
    return day + timedelta(days=-day.weekday() % 7)


# --- The deletion ------------------------------------------------------------------------------


def test_a_line_deleted_goes_for_good_and_its_task_and_the_totals_are_given_back(
    tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # ``deleteNode`` of a line: deleted physically, nothing written, its task among the ancestors
    # with its amounts and the totals of the structure without it (US-1490, ``deleteNode``).
    task = tree.made("Câblage")
    lines.made(task, **labour(costs.role))
    node = lines.made(task, **material(costs))["nodes"][0]
    answer = delete(tree, node)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["nodes"] == []
    [bearer] = body["ancestors"]
    assert (bearer["node_id"], bearer["task"]["base_amount"]) == (task["node_id"], "650.00")
    assert (body["totals"]["estimate_line_count"], body["totals"]["base_amount"]) == (1, "650.00")
    assert stored(stage) == 1
    assert node["node_id"] not in {item["node_id"] for item in tree.items()}


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_deletion_of_a_task_takes_its_lines_and_links_and_nothing_else(
    tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « La suppression d'une tâche de la révision en cours entraîne ses lignes et ses liaisons, et
    # rien d'autre. » A summary goes with its subtask, their lines and their links, by the
    # cascade of the keys; the other task keeps its line and the totals decrease by as much.
    summary = tree.made("Lot armoires")
    sub = tree.made("Câblage", parent_id=summary["node_id"])
    lines.made(summary, **material(costs))
    lines.made(sub, **labour(costs.role))
    other = tree.made("Essais")
    kept = lines.made(other, **material(costs, label="Banc d'essai"))["nodes"][0]
    project, revision = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    with stage.owner.begin() as connection:
        connection.execute(
            insert_link(
                project,
                revision,
                UUID(tree.structure_id),
                UUID(sub["node_id"]),
                UUID(other["node_id"]),
            )
        )
    assert stored(stage) == 3
    answer = delete(tree, tree.node(summary["node_id"]))
    assert answer.status_code == 200, answer.text
    assert answer.json()["totals"]["estimate_line_count"] == 1
    assert answer.json()["totals"]["base_amount"] == "350.00"
    with stage.database.transaction() as session:
        held = session.scalars(select(EstimateLine.node_id)).all()
        links = session.scalar(select(func.count()).select_from(TaskLink))
        nodes = session.scalars(select(Node.id).where(Node.project_id == project)).all()
    assert held == [UUID(kept["node_id"])]
    assert links == 0
    assert set(nodes) == {UUID(other["node_id"]), UUID(kept["node_id"])}


@pytest.mark.requirement("WF-DEV-0050-A")
def test_a_line_of_a_completed_task_is_neither_deleted_nor_moved_on_the_main_structure(
    tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « Dans la structure principale, la création d'une ligne sous une tâche terminée, ou le
    # déplacement d'une ligne vers elle, est refusé. » Nor deleted, nor moved from it, the task
    # reopened first from the Kanban (#1767): ``task_not_completed``, after the conditions of the
    # revision; the phase of the project refuses nothing (C-358). Nothing is written.
    done = tree.made("Câblage")
    open_task = tree.made("Essais")
    line = lines.made(done, **material(costs))["nodes"][0]
    other = lines.made(open_task, **material(costs, label="Banc"))["nodes"][0]
    set_progress(stage, done["node_id"], "completed", tree.created_at.date())
    before = counter(tree)
    assert refusal(delete(tree, line)) == COMPLETED
    assert refusal(move(tree, [line], open_task["node_id"])) == COMPLETED
    assert refusal(move(tree, [other], done["node_id"])) == COMPLETED
    assert counter(tree) == before
    assert tree.node(other["node_id"])["parent_id"] == open_task["node_id"]
    assert stored(stage) == 2
    # A line of a task that is not completed moves as elsewhere: here, at the head of its lines.
    third = lines.made(open_task, **material(costs, label="Câbles"))["nodes"][0]
    moved(tree, [third], open_task["node_id"], after_node_id=None)
    labels = [
        item["estimate_line"]["label"]
        for item in tree.items()
        if item["parent_id"] == open_task["node_id"]
    ]
    assert labels == ["Câbles", "Banc"]
    mark(stage, tree.revision)
    marked = (409, STATE_FORBIDS, {"missing_condition": "revision_draft"})
    assert refusal(delete(tree, line)) == marked
    assert refusal(move(tree, [line], open_task["node_id"])) == marked


@pytest.mark.requirement("WF-DEV-0050-A")
def test_a_line_reordered_under_its_own_completed_task_is_refused_on_the_main_structure(
    tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # A completed task freezes its lines on the main structure, their rank included: a move to the
    # task that already bears them is refused as a move to another (``task_not_completed``), and
    # nothing moves.
    done = tree.made("Câblage")
    first = lines.made(done, **material(costs, label="Câbles"))["nodes"][0]
    second = lines.made(done, **material(costs, label="Banc"))["nodes"][0]
    set_progress(stage, done["node_id"], "completed", tree.created_at.date())

    def labels() -> list[str]:
        return [
            item["estimate_line"]["label"]
            for item in tree.items()
            if item["parent_id"] == done["node_id"]
        ]

    before = counter(tree)
    assert labels() == ["Câbles", "Banc"]
    answer = move(tree, [first], done["node_id"], after_node_id=second["node_id"])
    assert refusal(answer) == COMPLETED
    assert counter(tree) == before
    assert labels() == ["Câbles", "Banc"]


# --- The move ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0030-A")
def test_a_line_moved_to_a_task_two_years_later_is_priced_on_it_and_given_back(
    api: ContractClient, tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « Une même ligne consommée deux ans après l'année de référence, avec un taux d'inflation de
    # 3 %, vaut 1,03 x 1,03 fois son montant de base. » The line moved to a task two years later
    # is priced again on it (``reinflate``), given back with its amounts and year, the former and
    # the new task among the ancestors.
    path = f"{PROJECTS}/{stage.project['project_id']}"
    held = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    changed = api.patch(
        path, headers=stage.manager.headers, json={"inflation_rate": "0.03", "lock_version": held}
    )
    assert changed.status_code == 200, changed.text
    now = tree.made("Études")
    start = first_monday(YEAR + 2)
    later = tree.made(
        "Exploitation",
        task={
            "scheduling_mode": "manual",
            "start": {"date": start.isoformat()},
            "finish": {"date": (start + timedelta(days=1)).isoformat()},
        },
    )
    line = lines.made(now, **labour(costs.role))["nodes"][0]
    assert line["estimate_line"]["consumption_year"] == YEAR
    assert line["estimate_line"]["reestimated_amount"] == "650.00"
    body = moved(tree, [line], later["node_id"])
    [written] = body["nodes"]
    expected = (Decimal("650.00") * Decimal("1.03") * Decimal("1.03")).quantize(CENT, ROUND_HALF_UP)
    assert written["parent_id"] == later["node_id"]
    assert (
        written["estimate_line"]["base_amount"],
        written["estimate_line"]["reestimated_amount"],
        written["estimate_line"]["consumption_year"],
    ) == ("650.00", str(expected), YEAR + 2)
    ancestors = {each["node_id"]: each["task"] for each in body["ancestors"]}
    assert ancestors[later["node_id"]]["reestimated_amount"] == str(expected)
    assert ancestors[now["node_id"]]["base_amount"] == "0.00"
    read = tree.node(line["node_id"])["estimate_line"]
    assert read["reestimated_amount"] == str(expected)


def test_lines_move_under_a_milestone_after_a_line_and_not_after_a_line_of_another_task(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # ``moveNodes`` of a selection of lines: under a milestone, which carries no subtask but
    # lines, after the line named, in the order sent; a line of another task named as the
    # sibling is refused (``NODE_NOT_SIBLING``), nothing moving (US-1490, ``moveNodes``).
    source = tree.made("Câblage")
    first = lines.made(source, **material(costs, label="Câbles"))["nodes"][0]
    second = lines.made(source, **material(costs, label="Borniers"))["nodes"][0]
    milestone = tree.made("Recette", task={"duration": {"value": "0", "unit": "d"}})
    held = lines.made(milestone, **material(costs, label="PV"))["nodes"][0]
    body = moved(tree, [second, first], milestone["node_id"], after_node_id=held["node_id"])
    assert [each["node_id"] for each in body["nodes"]] == [second["node_id"], first["node_id"]]
    under = [
        item["estimate_line"]["label"]
        for item in tree.items()
        if item["parent_id"] == milestone["node_id"]
    ]
    assert under == ["PV", "Borniers", "Câbles"]
    assert tree.node(milestone["node_id"])["task"]["duration"]["value"] == "0"
    other = tree.made("Essais")
    assert faults(move(tree, [held], other["node_id"], after_node_id=first["node_id"])) == [
        ("/after_node_id", "NODE_NOT_SIBLING", {})
    ]
    assert tree.node(held["node_id"])["parent_id"] == milestone["node_id"]


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_labour_line_moved_to_a_task_whose_role_never_meets_it_is_refused_naming_the_roles(
    tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « L'ajout, à une tâche dont un rôle travaille du lundi au vendredi, d'une ligne d'un rôle qui
    # ne travaille que le week-end est refusé en nommant les deux rôles, et la tâche reste
    # inchangée. » By a move: the line judged once placed under the task that receives it.
    weekdays = tree.made("Câblage")
    lines.made(weekdays, **labour(costs.role))
    weekend = add_role(stage.database, "WE", (0, 0, 0, 0, 0, 8, 8))
    elsewhere = tree.made("Astreinte")
    line = lines.made(elsewhere, **labour(weekend))["nodes"][0]
    before = tree.node(weekdays["node_id"])
    answer = move(tree, [line], weekdays["node_id"])
    assert refusal(answer) == (
        422,
        "TASK_WITHOUT_WORKING_HOURS",
        {
            "resource_roles": [
                {"resource_role_id": str(costs.role), "code": "ING", "label": "Ingénieur"},
                {"resource_role_id": str(weekend), "code": "WE", "label": "Rôle WE"},
            ],
            "tasks": [
                {
                    "project_id": stage.project["project_id"],
                    "node_id": weekdays["node_id"],
                    "label": "Câblage",
                }
            ],
        },
    )
    after = tree.node(weekdays["node_id"])
    kept = ("start", "finish", "calendar_id", "calendar_hours")
    assert [after["task"][name] for name in kept] == [before["task"][name] for name in kept]
    assert tree.node(line["node_id"])["parent_id"] == elsewhere["node_id"]


# --- What the lines answer the other modules ---------------------------------------------------


@pytest.mark.requirement("WF-DAT-0010-A")
def test_the_abandonment_of_the_current_revision_leaves_none_of_its_lines_nor_its_rates(
    api: ContractClient, tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « L'abandon d'une révision en cours ne laisse aucune ligne portant son identifiant. » The
    # lines follow their nodes, the rates it keeps go by ``register_closing``; the marked
    # revision keeps its own. The opening copies the rates of the reference (US-1500/L1).
    task = tree.made("Câblage")
    lines.made(task, **labour(costs.role))
    mark(stage, tree.revision)
    marked = UUID(tree.revision["revision_id"])
    current = opened(api, stage)
    revision = UUID(current["revision_id"])
    project = UUID(stage.project["project_id"])

    def held() -> dict[UUID, tuple[int, int]]:
        with stage.database.transaction() as session:
            counted = session.execute(
                select(Node.revision_id, func.count())
                .join(EstimateLine, EstimateLine.node_id == Node.id)
                .group_by(Node.revision_id)
            ).all()
            found = {row.revision_id: row[1] for row in counted}
            rates = session.scalar(
                select(func.count())
                .select_from(RevisionRate)
                .where(RevisionRate.revision_id == revision)
            )
        return {
            marked: (found.get(marked, 0), 0),
            revision: (found.get(revision, 0), rates or 0),
        }

    assert held() == {marked: (1, 0), revision: (1, 1)}
    path = f"{PROJECTS}/{project}/revisions/{revision}"
    answer = api.delete(
        f"{path}?lock_version={current['lock_version']}", headers=stage.manager.headers
    )
    assert answer.status_code == 204, answer.text
    assert held() == {marked: (1, 0), revision: (0, 0)}


def subproject(api: ContractClient, stage: Scene, code: str) -> str:
    """Create a subproject of the project of the stage, as its manager does; give it."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": f"Poste {code}"},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["subproject_id"]


def delete_subproject(api: ContractClient, stage: Scene, subproject_id: str) -> Any:
    """Delete a subproject at its first counter, as the manager does; give the answer."""
    return api.delete(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects/{subproject_id}",
        headers=stage.manager.headers,
        params={"lock_version": 0},
    )


def deletion_lacks(api: ContractClient, stage: Scene, subproject_id: str) -> list[str]:
    """Read what the command ``delete`` of a subproject lacks, as the list gives it."""
    listed = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects", headers=stage.manager.headers
    )
    assert listed.status_code == 200, listed.text
    [item] = [each for each in listed.json() if each["subproject_id"] == subproject_id]
    return next(
        command["missing_conditions"]
        for command in item["available_commands"]
        if command["command"] == "delete"
    )


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_subproject_the_lines_of_the_current_revision_bear_is_kept_naming_them(
    api: ContractClient, tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « Celle d'un sous-projet que portent des lignes de devis de la révision en cours est refusée
    # et nomme ces lignes ; elle aboutit une fois ces lignes passées hors sous-projet ou à un autre
    # sous-projet. » Each line by its structure, its node, its row number and its label, in the
    # order of the plan.
    named = subproject(api, stage, "SP-CMD")
    other = subproject(api, stage, "SP-REC")
    task = tree.made("Câblage")
    lines.made(task, **material(costs, label="Câbles"))
    first = lines.made(task, **material(costs, label="Borniers", subproject_id=named))
    second = lines.made(task, **material(costs, label="Raccordement", subproject_id=named))
    assert deletion_lacks(api, stage, named) == ["subproject_without_estimate_lines"]
    assert deletion_lacks(api, stage, other) == []
    refused = delete_subproject(api, stage, named)
    assert refusal(refused) == (
        409,
        STATE_FORBIDS,
        {
            "missing_condition": "subproject_without_estimate_lines",
            "estimate_lines": [
                {
                    "structure_id": tree.structure_id,
                    "structure_label": "Structure principale",
                    "node_id": written["nodes"][0]["node_id"],
                    "row_number": row,
                    "label": label,
                }
                for written, row, label in ((first, 3, "Borniers"), (second, 4, "Raccordement"))
            ],
        },
    )
    lines.changed(tree.node(first["nodes"][0]["node_id"]), subproject_id=None)
    lines.changed(tree.node(second["nodes"][0]["node_id"]), subproject_id=other)
    assert delete_subproject(api, stage, named).status_code == 204
    assert refusal(delete_subproject(api, stage, other))[2]["estimate_lines"][0]["label"] == (
        "Raccordement"
    )


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_lines_a_refusal_names_come_main_structure_first_then_by_structure_label(
    tree: Tree, lines: Lines, costs: Costing, stage: Scene, owner: Engine
) -> None:
    api = tree.api
    # The main structure first, whatever the label of the others: a differential whose label sorts
    # before "Structure principale" is named after it. No differential is written before EP-08 and
    # the kind of a structure is checked: the check is lifted for this test alone, and restored.
    named = subproject(api, stage, "SP-CMD")
    task = tree.made("Câblage")
    written = lines.made(task, **material(costs, label="Borniers", subproject_id=named))
    project_id, revision_id = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    row = structure_row(project_id, revision_id, kind="differential", label="Alpha")
    structure_id = row["id"]
    assert isinstance(structure_id, UUID)
    with lifted_kind_check(owner):
        try:
            with owner.begin() as connection:
                connection.execute(insert(CostStructure).values(**row))
                bearer = insert_task(connection, project_id, revision_id, structure_id)
                node_id = give_a_line(connection, bearer)
                connection.execute(
                    update(EstimateLine)
                    .where(EstimateLine.node_id == node_id)
                    .values(label="Alpha 1", subproject_id=UUID(named))
                )
            refused = delete_subproject(api, stage, named)
            found = refusal(refused)[2]["estimate_lines"]
            assert [(line["structure_label"], line["label"]) for line in found] == [
                ("Structure principale", "Borniers"),
                ("Alpha", "Alpha 1"),
            ]
            assert found[0]["node_id"] == written["nodes"][0]["node_id"]
        finally:
            with owner.begin() as connection:
                nodes = select(Node.id).where(Node.structure_id == structure_id)
                connection.execute(sql_delete(EstimateLine).where(EstimateLine.node_id.in_(nodes)))
                connection.execute(
                    sql_delete(Node).where(
                        Node.structure_id == structure_id, Node.kind == "estimate_line"
                    )
                )
                connection.execute(sql_delete(Task).where(Task.node_id.in_(nodes)))
                connection.execute(sql_delete(Node).where(Node.structure_id == structure_id))
                connection.execute(
                    sql_delete(CostStructure).where(CostStructure.id == structure_id)
                )


@pytest.mark.requirement("WF-DAT-0080-A")
@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_subproject_a_marked_revision_cites_by_a_line_is_refused_and_stays_offered(
    api: ContractClient, tree: Tree, lines: Lines, costs: Costing, stage: Scene
) -> None:
    # « Celle d'un sous-projet référencé par une révision marquée est refusée, et le sous-projet
    # reste proposé à la saisie. » ; « La suppression physique d'un sous-projet référencé par une
    # révision marquée est rejetée. » Referenced by a line of the marked revision; the copy of the
    # line in the revision opened then bears it too, named second.
    named = subproject(api, stage, "SP-CMD")
    task = tree.made("Câblage")
    lines.made(task, **material(costs, subproject_id=named))
    mark(stage, tree.revision)
    cited = (409, STATE_FORBIDS, {"missing_condition": "subproject_not_cited"})
    assert deletion_lacks(api, stage, named) == ["subproject_not_cited"]
    assert refusal(delete_subproject(api, stage, named)) == cited
    current = Tree(api, stage, opened(api, stage))
    assert deletion_lacks(api, stage, named) == [
        "subproject_not_cited",
        "subproject_without_estimate_lines",
    ]
    assert refusal(delete_subproject(api, stage, named)) == cited
    copied = next(item for item in current.items() if item["kind"] == "task")
    offered = Lines(current).made(copied, **material(costs, label="Câbles", subproject_id=named))
    assert offered["nodes"][0]["estimate_line"]["subproject_id"] == named


@pytest.mark.requirement("WF-REF-0040-A")
def test_a_category_a_line_employs_is_refused_a_nature_of_another_kind(
    tree: Tree, lines: Lines, costs: Costing, realm: TestRealm
) -> None:
    # « Le rattachement d'une catégorie employée à une nature d'un autre type est refusé […] ; le
    # rattachement d'une catégorie inemployée, sans taux ni rôle, à une nature d'un autre type est
    # accepté. » Employed by a line of a revision, current or marked.
    api, stage = tree.api, tree.stage
    changer = person(stage.database, realm, "cost_settings.read", "cost_settings.write")
    with stage.database.transaction() as session:
        labour_kind = session.scalar(select(CostType.id).where(CostType.code == "MO"))
        nature = session.scalar(select(CostType.id).where(CostType.code == "MAT"))
        assert nature is not None
        draft = CostCategoryDraft("MAT-002", "Câbles", "606002", nature)
        spare = create_cost_category(session, draft, Act(None, utc_now())).cost_category_id

    def attach(category: UUID, code: str, label: str, accounting: str) -> Any:
        with stage.database.transaction() as session:
            counter = session.scalar(
                select(CostCategory.lock_version).where(CostCategory.id == category)
            )
        body = {
            "code": code,
            "label": label,
            "accounting_code": accounting,
            "cost_type_id": str(labour_kind),
            "lock_version": counter,
        }
        return api.patch(f"{CATEGORIES}/{category}", headers=changer.headers, json=body)

    unused = (409, STATE_FORBIDS, {"missing_condition": "cost_category_unused"})
    task = tree.made("Câblage")
    node = lines.made(task, **material(costs, cost_category_id=str(spare)))["nodes"][0]
    assert refusal(attach(spare, "MAT-002", "Câbles", "606002")) == unused
    assert delete(tree, node).status_code == 200
    accepted = attach(spare, "MAT-002", "Câbles", "606002")
    assert (accepted.status_code, accepted.json()["cost_type_kind"]) == (200, "labor")
    lines.made(task, **material(costs))
    mark(stage, tree.revision)
    assert refusal(attach(costs.material, "MAT-001", "Matériel électrique", "606001")) == unused
