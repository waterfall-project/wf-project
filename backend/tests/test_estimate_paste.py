# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste of a block of cells on the lines of an estimate (US-1560/L1).

``previewPaste`` and ``applyPaste`` of the planning judge the columns of a line — the category, the
role, the quantity, the hours, the unit disbursement, the subproject and the payment delay — in the
order of ``NodeColumn``, by the very functions of the entry of a cell (``updateEstimateLine``,
``createNode``) that the hooks of the facet ``estimate_line`` give. A block pasted under a task
creates its lines past the last node, the paste being one entry of the history. Every answer is
checked against the contract, on the main structure of the current revision of a project its
manager made (``nodes_support``), its labour category rated for the year (``estimate_support``).
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import Costing, Lines, add_role, costing
from history_support import counter, plans, redone, undone
from nodes_support import Tree, entries, opened, set_progress, signed_in
from projects_support import PROJECTS
from projects_support import scene as make_scene
from sqlalchemy import select, update

from waterfall.core.cost_settings.tables import CostCategory

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

EXAMPLES = Path(__file__).resolve().parents[2] / "fixtures" / "api"
MATERIAL = "Matériel électrique"
LABOUR = "Ingénierie"
ROLE = "Ingénieur"
COMPLETED = {"missing_condition": "task_not_completed"}


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


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def labour(costs: Costing, **line: Any) -> dict[str, Any]:
    """Give a labour line of the role of the scene: one engineer for ten hours, unless said."""
    return {"quantity": "1", "resource_role_id": str(costs.role), "hours": "10", **line}


def material(costs: Costing, **line: Any) -> dict[str, Any]:
    """Give a line of material: one at 350.00, unless said."""
    held = {"quantity": "1", "cost_category_id": str(costs.material), "unit_disbursement": "350.00"}
    return {**held, **line}


def preview(
    tree: Tree, target: dict[str, Any], column: str, rows: list[list[str]], who: Person
) -> Any:
    """Preview a block pasted on a cell of a node; give the answer."""
    sent = {"target_node_id": target["node_id"], "target_column": column, "rows": rows}
    return tree.api.post(f"{tree.path}/nodes/paste-preview", headers=who.headers, json=sent)


def planned(
    tree: Tree, target: dict[str, Any], column: str, rows: list[list[str]], who: Person
) -> dict[str, Any]:
    """Preview a block that must be previewed; give the plan."""
    answer = preview(tree, target, column, rows, who)
    assert answer.status_code == 200, answer.text
    return answer.json()


def applied(tree: Tree, plan: dict[str, Any], who: Person) -> dict[str, Any]:
    """Confirm a plan that must be confirmed, at the counter of the structure; give the answer."""
    sent = {"paste_id": plan["paste_id"], "confirmed": True, "lock_version": counter(tree)}
    answer = tree.api.post(f"{tree.path}/nodes/paste", headers=who.headers, json=sent)
    assert answer.status_code == 200, answer.text
    return answer.json()


def reasons(plan: dict[str, Any]) -> list[tuple[int, str | None, str]]:
    """Give the refusals of a plan: the row, the column if there is one, the code."""
    return [(each["row"], each.get("column"), each["code"]) for each in plan["rejected"]]


def estimate_lines(tree: Tree) -> list[dict[str, Any]]:
    """Read the facets of the lines of the structure, in the order of the plan."""
    return [each["estimate_line"] for each in tree.items() if each["kind"] == "estimate_line"]


def line_labels(tree: Tree) -> list[str]:
    """Read the labels of the lines of the structure, in the order of the plan."""
    return [each["label"] for each in estimate_lines(tree)]


def category_label(stage: Scene, category_id: UUID) -> str:
    """Read the label of a category of the reference."""
    with stage.database.transaction() as session:
        return session.scalars(
            select(CostCategory.label).where(CostCategory.id == category_id)
        ).one()


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_block_pasted_on_a_line_writes_each_cell_by_the_functions_of_its_entry(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # Vérif : « Un bloc de trois lignes et quatre colonnes collé depuis un tableur produit un compte
    # rendu avant écriture, puis les trois lignes attendues après confirmation. » — ici sur les
    # colonnes de la ligne : le libellé, la catégorie, le rôle, la quantité, les heures, le débours
    # unitaire (la virgule décimale d'un tableur), le sous-projet, le délai de paiement.
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs, label="Câble"))["nodes"][0]
    engineer = lines.made(task, who, **labour(costs))["nodes"][0]
    before = counter(tree)
    block = [
        ["Câble 5 m", MATERIAL, "", "2", "", "120,50", "", "30"],
        ["Conception", "", ROLE, "3", "12", "", "", "15"],
    ]
    plan = planned(tree, cable, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (2, 0, [])
    # The preview writes nothing: neither the lines, nor the counter.
    assert (line_labels(tree), counter(tree)) == (["Câble", "Étude — Ingénieur"], before)
    body = applied(tree, plan, who)
    assert body["rejected"] == []
    assert [each["node_id"] for each in body["nodes"]] == [cable["node_id"], engineer["node_id"]]
    first, second = (each["estimate_line"] for each in body["nodes"])
    assert (first["label"], first["quantity"], first["payment_delay_days"]) == (
        "Câble 5 m",
        "2",
        30,
    )
    assert (first["unit_disbursement"], first["base_amount"]) == ("120.50", "241.00")
    # A labour line is priced again at the rate of its category: 3 x 12 h x 65.00.
    assert (second["quantity"], second["hours"], second["payment_delay_days"]) == ("3", "12", 15)
    assert second["base_amount"] == "2340.00"
    assert counter(tree) == before + 1


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_block_pasted_from_a_column_of_a_line_fills_the_columns_that_follow_it(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    engineer = lines.made(task, who, **labour(costs))["nodes"][0]
    plan = planned(tree, engineer, "hours", [["12", "", ""]], who)
    assert (plan["accepted"], plan["rejected"]) == (1, [])
    body = applied(tree, plan, who)
    assert body["nodes"][0]["estimate_line"]["hours"] == "12"
    assert body["nodes"][0]["estimate_line"]["base_amount"] == "780.00"


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_columns_a_line_bears_are_its_label_then_those_of_the_estimate(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # Vérif : « Un collage plus large que la grille est refusé en le disant. »
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs))["nodes"][0]
    for column in ("description", "scheduling_mode", "work_breakdown"):
        answer = preview(tree, cable, column, [["x"]], who)
        assert answer.status_code == 422, column
        assert [(each["pointer"], each["code"]) for each in answer.json()["fields"]] == [
            ("/target_column", "FIELD_NOT_ACCEPTED")
        ]
    wide = preview(tree, cable, "cost_category", [["x"] * 16], who)
    assert (wide.status_code, wide.json()["code"], wide.json()["params"]) == (
        422,
        "PASTE_TOO_WIDE",
        {"max_columns": 15},
    )
    assert preview(tree, cable, "label", [["x"] * 16], who).status_code == 200


# (kind of the line, column pasted, text, code of the refusal): each refused by the function of
# ``updateEstimateLine``, the row refused whole and the line left as it was.
REFUSED = [
    ("labour", "cost_category", MATERIAL, "COMPUTED_VALUE"),
    ("labour", "unit_disbursement", "10", "FIELD_NOT_ACCEPTED"),
    ("labour", "base_amount", "1", "COMPUTED_VALUE"),
    ("labour", "consumption_year", "2026", "COMPUTED_VALUE"),
    ("labour", "previous_quantity", "1", "FIELD_NOT_ACCEPTED"),
    ("labour", "resource_role", "Fantôme", "UNKNOWN_RESOURCE_ROLE"),
    ("material", "hours", "5", "FIELD_NOT_ACCEPTED"),
    ("material", "resource_role", ROLE, "FIELD_NOT_ACCEPTED"),
    ("material", "cost_category", "Essais", "UNKNOWN_COST_CATEGORY"),
    ("material", "subproject", "Nulle part", "UNKNOWN_SUBPROJECT"),
    ("material", "quantity", "abc", "NUMBER_INVALID"),
    ("material", "quantity", "-1", "VALUE_OUT_OF_RANGE"),
    ("material", "payment_delay_days", "1,5", "NUMBER_INVALID"),
    ("material", "payment_delay_days", "-3", "VALUE_OUT_OF_RANGE"),
    ("material", "label", "x" * 301, "VALUE_TOO_LONG"),
]


@pytest.mark.requirement("WF-IHM-0050-A")
@pytest.mark.parametrize("case", REFUSED)
def test_a_cell_the_entry_of_a_line_refuses_is_refused_by_its_row_and_its_column(
    tree: Tree, lines: Lines, costs: Costing, who: Person, case: tuple[str, str, str, str]
) -> None:
    # Vérif : « Un bloc dont une cellule porte une catégorie inconnue signale cette ligne ;
    # confirmé, il écrit les autres lignes et non celle-ci ; abandonné, il ne modifie aucune
    # ligne. »
    kind, column, text, code = case
    task = tree.made("Étude", who=who)
    held = labour(costs) if kind == "labour" else material(costs)
    target = lines.made(task, who, **held)["nodes"][0]
    before = estimate_lines(tree)
    plan = planned(tree, target, column, [[text]], who)
    assert (plan["accepted"], reasons(plan)) == (0, [(0, column, code)])
    assert estimate_lines(tree) == before
    body = applied(tree, plan, who)
    assert (body["nodes"], reasons(body)) == ([], reasons(plan))
    assert estimate_lines(tree) == before


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_refused_row_is_not_written_and_the_others_are(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # Vérif : « Un bloc dont une cellule porte une catégorie inconnue signale cette ligne ;
    # confirmé, il écrit les autres lignes et non celle-ci ; abandonné, il ne modifie aucune
    # ligne. »
    task = tree.made("Étude", who=who)
    first = lines.made(task, who, **material(costs, label="Un"))["nodes"][0]
    lines.made(task, who, **material(costs, label="Deux"))
    lines.made(task, who, **material(costs, label="Trois"))
    block = [["Un bis", MATERIAL], ["Deux bis", "Essais"], ["Trois bis", MATERIAL]]
    plan = planned(tree, first, "label", block, who)
    assert (plan["accepted"], reasons(plan)) == (2, [(1, "cost_category", "UNKNOWN_COST_CATEGORY")])
    assert len(plans(tree.stage)) == 1
    assert line_labels(tree) == ["Un", "Deux", "Trois"]
    body = applied(tree, plan, who)
    assert reasons(body) == reasons(plan)
    assert line_labels(tree) == ["Un bis", "Deux", "Trois bis"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_category_of_provision_is_reserved_to_the_risks(
    tree: Tree, lines: Lines, costs: Costing, who: Person, stage: Scene
) -> None:
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs))["nodes"][0]
    label = category_label(stage, costs.provision)
    plan = planned(tree, cable, "cost_category", [[label]], who)
    assert (plan["accepted"], reasons(plan)) == (
        0,
        [(0, "cost_category", "PROVISION_CATEGORY_RESERVED")],
    )


@pytest.mark.requirement("WF-IHM-0050-A")
def test_every_refusal_of_a_row_is_named_at_once_in_the_order_of_the_columns(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs))["nodes"][0]
    block = [["x", "Essais", ROLE, "abc", "5", "-2", "Nulle part", "2"]]
    plan = planned(tree, cable, "label", block, who)
    assert plan["accepted"] == 0
    assert reasons(plan) == [
        (0, "cost_category", "UNKNOWN_COST_CATEGORY"),
        (0, "resource_role", "FIELD_NOT_ACCEPTED"),
        (0, "quantity", "NUMBER_INVALID"),
        (0, "hours", "FIELD_NOT_ACCEPTED"),
        (0, "unit_disbursement", "VALUE_OUT_OF_RANGE"),
        (0, "subproject", "UNKNOWN_SUBPROJECT"),
    ]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_subproject_is_named_by_its_label(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    created = tree.api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-CMD", "label": "Poste de commande"},
    )
    assert created.status_code == 201, created.text
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs))["nodes"][0]
    plan = planned(tree, cable, "subproject", [["Poste de commande"]], who)
    assert (plan["accepted"], plan["rejected"]) == (1, [])
    body = applied(tree, plan, who)
    written = body["nodes"][0]["estimate_line"]
    assert written["subproject_id"] == created.json()["subproject_id"]


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_role_that_leaves_the_task_without_a_worked_hour_is_refused_on_its_cell(
    tree: Tree, lines: Lines, costs: Costing, who: Person, stage: Scene
) -> None:
    # Vérif de WF-IHM-0050-A, motif de refus de la saisie : le rôle qui ne laisse à la tâche aucune
    # heure travaillée (ING du lundi au vendredi, NUIT du samedi au dimanche) est refusé.
    add_role(stage.database, "NUIT", (0, 0, 0, 0, 0, 8, 8))
    task = tree.made("Étude", who=who)
    lines.made(task, who, **labour(costs))
    cable = lines.made(task, who, **material(costs))["nodes"][0]
    blocked = lines.made(task, who, **labour(costs))["nodes"][0]
    # The client of the tests reads no `PasteRejection.params`, whose `tasks` compose two objects
    # (`AmbiguousCompositionError`): the answer is validated by the contract, and read as it comes.
    sent = {"target_node_id": blocked["node_id"], "target_column": "resource_role"}
    answer = tree.api.client.post(
        f"{tree.path}/nodes/paste-preview",
        headers=who.headers,
        json={**sent, "rows": [["Rôle NUIT"]]},
    )
    assert answer.status_code == 200, answer.text
    plan = answer.json()
    assert (plan["accepted"], reasons(plan)) == (
        0,
        [(0, "resource_role", "TASK_WITHOUT_WORKING_HOURS")],
    )
    params = plan["rejected"][0]["params"]
    assert [each["label"] for each in params["resource_roles"]] == ["Ingénieur", "Rôle NUIT"]
    assert [each["label"] for each in params["tasks"]] == ["Étude"]
    assert cable["node_id"] != blocked["node_id"]


@pytest.mark.requirement("WF-DEV-0050-A")
def test_a_cell_of_a_line_of_a_completed_task_is_refused_on_the_main_structure(
    tree: Tree, lines: Lines, costs: Costing, who: Person, stage: Scene
) -> None:
    # Vérif : « Dans la structure principale, la création d’une ligne sous une tâche terminée, ou le
    # déplacement d’une ligne vers elle, est refusé. » (#1767, F-01) — la part du collage : chaque
    # cellule non vide d'une ligne d'une tâche terminée est refusée, la ligne n'est pas écrite ;
    # une cellule vide n'écrit rien et n'est pas refusée.
    open_ = tree.made("En cours", who=who)
    done = tree.made("Terminée", who=who)
    free = lines.made(open_, who, **material(costs, label="Libre"))["nodes"][0]
    frozen = lines.made(done, who, **material(costs, label="Figée"))["nodes"][0]
    set_progress(stage, done["node_id"], "completed", tree.created_at.date())
    assert free["node_id"] != frozen["node_id"]
    before = estimate_lines(tree)
    # The row between them falls on the completed task, which is no line, and is empty.
    block = [["Libre 2", MATERIAL], [""], ["Autre", "", ROLE, "3"]]
    plan = planned(tree, free, "label", block, who)
    assert plan["accepted"] == 1
    assert reasons(plan) == [
        (2, "label", "STATE_FORBIDS_OPERATION"),
        (2, "resource_role", "STATE_FORBIDS_OPERATION"),
        (2, "quantity", "STATE_FORBIDS_OPERATION"),
    ]
    assert {json.dumps(each["params"]) for each in plan["rejected"]} == {json.dumps(COMPLETED)}
    body = applied(tree, plan, who)
    assert reasons(body) == reasons(plan)
    assert line_labels(tree) == ["Libre 2", "Figée"]
    assert estimate_lines(tree)[1] == before[1]


@pytest.mark.requirement("WF-DEV-0050-A")
def test_a_line_created_under_a_completed_task_is_refused_on_the_main_structure(
    tree: Tree, lines: Lines, costs: Costing, who: Person, stage: Scene
) -> None:
    # Vérif : « Dans la structure principale, la création d’une ligne sous une tâche terminée […]
    # est refusé. » (#1767) — par un collage qui crée : la ligne au-delà du dernier nœud, sœur de la
    # dernière ligne d'une tâche terminée, est refusée sur chacune de ses cellules.
    done = tree.made("Terminée", who=who)
    last = lines.made(done, who, **material(costs, label="Figée"))["nodes"][0]
    set_progress(stage, done["node_id"], "completed", tree.created_at.date())
    plan = planned(tree, last, "label", [["Écrite"], ["Créée", MATERIAL]], who)
    assert (plan["accepted"], plan["created"]) == (0, 0)
    assert reasons(plan) == [
        (0, "label", "STATE_FORBIDS_OPERATION"),
        (1, "label", "STATE_FORBIDS_OPERATION"),
        (1, "cost_category", "STATE_FORBIDS_OPERATION"),
    ]
    assert line_labels(tree) == ["Figée"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_rows_past_the_last_node_create_lines_in_one_entry_of_the_history(
    tree: Tree, lines: Lines, costs: Costing, who: Person, stage: Scene
) -> None:
    # Vérif : « Un bloc de trois lignes et quatre colonnes collé depuis un tableur produit un compte
    # rendu avant écriture, puis les trois lignes attendues après confirmation. » ; critère
    # d'US-1450 (#2559) : une ligne au-delà du dernier nœud crée un nœud du genre du nœud visé,
    # sœur du dernier nœud ; une seule entrée d'historique, annulable d'un coup (WF-IHM-0110).
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs, label="Câble"))["nodes"][0]
    before = (counter(tree), len(entries(stage)))
    block = [
        ["Câble 2", MATERIAL, "", "1", "", "10"],
        ["Goulotte", MATERIAL, "", "2", "", "20"],
        ["Conception", "", ROLE, "3", "12"],
    ]
    plan = planned(tree, cable, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (3, 2, [])
    assert (counter(tree), len(entries(stage))) == before
    assert line_labels(tree) == ["Câble"]
    body = applied(tree, plan, who)
    assert body["rejected"] == []
    assert line_labels(tree) == ["Câble 2", "Goulotte", "Conception"]
    written = [each["estimate_line"] for each in body["nodes"]]
    assert [each["base_amount"] for each in written] == ["10.00", "40.00", "2340.00"]
    assert [each["lock_version"] for each in body["nodes"]] == [2, 1, 1]
    assert {each["parent_id"] for each in body["nodes"]} == {task["node_id"]}
    assert (counter(tree), len(entries(stage))) == (before[0] + 1, before[1] + 1)
    assert entries(stage)[-1].kind == "paste"
    # One undoing deletes the two lines it created and gives the first its cells back.
    first = undone(tree, who)
    assert first["undone"]["kind"] == "paste"
    assert line_labels(tree) == ["Câble"]
    assert len(entries(stage)) == before[1] + 1
    again = redone(tree, who)
    assert again["undone"]["kind"] == "paste"
    assert line_labels(tree) == ["Câble 2", "Goulotte", "Conception"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_row_that_creates_a_line_needs_its_label_and_is_refused_whole_otherwise(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # Critère d'US-1450 (#2559) pour le genre ligne : le libellé est requis (`VALIDATION_FAILED`,
    # `label`), les autres cellules se jugent comme celles d'une ligne écrite, la ligne refusée ne
    # crée rien et les autres sont créées.
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs, label="Câble"))["nodes"][0]
    block = [
        ["Câble 2", MATERIAL],
        ["Goulotte", MATERIAL],
        ["", MATERIAL],
        ["Essais", "Essais"],
        ["Sans catégorie", ""],
        ["Rôle sans heures", "", ROLE, "1", "5", "9"],
    ]
    plan = planned(tree, cable, "label", block, who)
    assert (plan["accepted"], plan["created"]) == (2, 1)
    assert reasons(plan) == [
        (2, "label", "VALIDATION_FAILED"),
        (3, "cost_category", "UNKNOWN_COST_CATEGORY"),
        (4, "cost_category", "VALUE_REQUIRED"),
        (5, "unit_disbursement", "FIELD_NOT_ACCEPTED"),
    ]
    body = applied(tree, plan, who)
    assert reasons(body) == reasons(plan)
    assert line_labels(tree) == ["Câble 2", "Goulotte"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_line_created_at_the_root_has_no_task_to_bear_it(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # The anchor, the last node, is a task at the root of the structure: the sibling of a task at
    # the root would be a line without a task (`UNKNOWN_TASK`), refused whole and created for none.
    study = tree.made("Étude", who=who)
    last = tree.made("Dernière", who=who)
    cable = lines.made(study, who, **material(costs))["nodes"][0]
    plan = planned(tree, cable, "label", [["Une"], [""], ["Deux"], ["Trois"]], who)
    assert (plan["accepted"], plan["created"]) == (1, 0)
    assert reasons(plan) == [(2, None, "UNKNOWN_TASK"), (3, None, "UNKNOWN_TASK")]
    assert last["node_id"] != cable["node_id"]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_line_created_beside_a_task_that_is_the_last_node_goes_under_its_parent(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # The last node is a subtask: a line created beside it bears on its parent, the task above.
    study = tree.made("Étude", who=who)
    note = tree.made("Note", who=who, parent_id=study["node_id"])
    cable = lines.made(study, who, **material(costs, label="Câble"))["nodes"][0]
    # The row between them falls on the subtask, a task, and is empty.
    plan = planned(tree, cable, "label", [["Câble 2"], [""], ["Goulotte", MATERIAL]], who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (2, 1, [])
    body = applied(tree, plan, who)
    created = body["nodes"][-1]
    assert (created["kind"], created["parent_id"]) == ("estimate_line", study["node_id"])
    assert line_labels(tree) == ["Câble 2", "Goulotte"]
    assert note["node_id"] not in {each["node_id"] for each in body["nodes"]}


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_cell_on_a_column_the_node_under_it_does_not_bear_is_refused(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # « Une cellule non vide qui tombe sur une colonne que sa ligne n'accepte pas est refusée » :
    # la ligne de devis ne porte ni description ni catégorie de tâche, la tâche ni catégorie ni
    # rôle ; seul le libellé est commun.
    study = tree.made("Étude", who=who)
    cable = lines.made(study, who, **material(costs, label="Câble"))["nodes"][0]
    other = tree.made("Autre", who=who)
    on_task = planned(tree, cable, "label", [["Câble 2", MATERIAL], ["Autre 2", MATERIAL]], who)
    assert (on_task["accepted"], reasons(on_task)) == (
        1,
        [(1, "cost_category", "FIELD_NOT_ACCEPTED")],
    )
    from_task = planned(tree, study, "label", [["Étude 2", "x"], ["Câble 3", "x"]], who)
    assert (from_task["accepted"], reasons(from_task)) == (
        1,
        [(1, "description", "FIELD_NOT_ACCEPTED")],
    )
    applied(tree, from_task, who)
    assert line_labels(tree) == ["Câble"]
    assert other["node_id"] != study["node_id"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_row_judged_again_at_the_confirmation_is_refused_when_its_category_is_deactivated(
    tree: Tree, lines: Lines, costs: Costing, who: Person, stage: Scene
) -> None:
    # « Une catégorie ou un rôle désactivé depuis l'aperçu » : la ligne est rejugée à la
    # confirmation, refusée (`INACTIVE_REFERENCE_OBJECT`), non écrite, et redite dans `rejected`.
    task = tree.made("Étude", who=who)
    cable = lines.made(task, who, **material(costs, label="Câble"))["nodes"][0]
    plan = planned(tree, cable, "label", [["Câble 2", MATERIAL], ["Créée", MATERIAL]], who)
    assert (plan["accepted"], plan["created"]) == (2, 1)
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostCategory).where(CostCategory.id == costs.material).values(is_active=False)
        )
    body = applied(tree, plan, who)
    # The line that keeps its category deactivated since is written, as `updateEstimateLine` does;
    # the line to create names it, and is refused.
    assert reasons(body) == [(1, "cost_category", "INACTIVE_REFERENCE_OBJECT")]
    assert line_labels(tree) == ["Câble 2"]
    assert [each["node_id"] for each in body["nodes"]] == [cable["node_id"]]


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_plan_of_a_block_that_creates_lines_is_the_example_of_the_contract(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # #2624 : l'exemple `creating_lines` de `previewPaste` — un bloc de cinq lignes collé sur le
    # libellé de la dernière ligne de la structure : la première l'écrit, les deux suivantes,
    # au-delà du dernier nœud, créent des lignes, la quatrième, sans libellé, et la cinquième, d'une
    # catégorie inconnue, sont refusées — est ce que le service répond ; le seul identifiant du
    # plan diffère.
    example = json.loads((EXAMPLES / "paste_plan_creating_lines.json").read_text(encoding="utf-8"))
    task = tree.made("Câblage des armoires", who=who)
    last = lines.made(task, who, **material(costs, label="Borniers"))["nodes"][0]
    block = [
        ["Borniers à vis", MATERIAL],
        ["Goulottes", MATERIAL],
        ["Repères de câbles", MATERIAL],
        ["", MATERIAL],
        ["Essais de mise en service", "Essais"],
    ]
    plan = planned(tree, last, "label", block, who)
    assert {key: value for key, value in plan.items() if key != "paste_id"} == {
        key: value for key, value in example["value"].items() if key != "paste_id"
    }
    UUID(plan["paste_id"])
    assert uuid4() != UUID(plan["paste_id"])
