# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The grids of the planning and of the estimate on the own estimate of a risk (US-2570/L2).

The own estimate of a risk is read and written by the operations of the main structure
(``listNodes``, ``createNode``, ``updateTaskFacet``, ``updateEstimateLine``, ``setPredecessors``,
``moveNodes``, ``deleteNode``, ``previewPaste``, ``applyPaste``), under the commands
``edit_planning`` and ``edit_estimate`` of its structure, in every state of the project that is not
terminal, In progress included, and with neither progress nor remaining to commit (WF-RIS-0030).
Each write advances its counter, and the risk's with it, and touches the main structure by the
provision line alone (US-2580); a revision marked after the risk carries its own estimate, read as
it was (WF-REV-0100). Every answer is checked against the contract (``ContractClient``).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import commands_of, listed, on
from estimate_support import YEAR, Costing, Lines, costing
from history_support import delete, link
from nodes_support import Tree, mark
from paste_support import apply, counter, planned
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import ESTIMATE, Costed, Risks, costed, material
from sqlalchemy import select, update
from test_amendments_base_counted import correct_rate, set_inflation

from waterfall.core.projects.tables import Project
from waterfall.core.risks.tables import Risk

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
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def own_tree(project: Costed, risk: dict[str, Any]) -> Tree:
    """Give the tree of the grids pointed at the own estimate of a risk."""
    return on(project.tree, risk["structure_id"])


def node_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read a node of a structure by its label, a task's or a line's."""
    found = [
        each for each in tree.items() if (each["task"] or each["estimate_line"])["label"] == label
    ]
    assert len(found) == 1, label
    return found[0]


def outside_provision(tree: Tree) -> list[dict[str, Any]]:
    """Read the nodes of a structure but the provision lines, which follow the risks written."""
    return [
        each
        for each in tree.items()
        if not (each["estimate_line"] or {"label": ""})["label"].startswith("Provision")
    ]


def snapshot(tree: Tree) -> tuple[Any, int]:
    """Read a structure whole, and its counter: what a write elsewhere must leave as it was."""
    return tree.read().json(), counter(tree)


def risk_counter(project: Costed, risk: dict[str, Any]) -> int:
    """Read the counter of a risk, which its own estimate's follows (#1453)."""
    with project.stage.database.transaction() as session:
        held = session.scalar(select(Risk.lock_version).where(Risk.id == UUID(risk["risk_id"])))
    assert held is not None
    return held


def total(tree: Tree) -> Decimal:
    """Read what an own estimate adds to the project: its totals less the 1 000 of the main one.

    The own estimate is a copy of the main structure since US-3070/L3, its base too (EP-30).
    """
    return Decimal(tree.read().json()["totals"]["reestimated_amount"]) - ESTIMATE


# --- WF-RIS-0030-A -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0030-A")
def test_every_operation_of_the_grids_serves_the_own_estimate_of_a_risk(
    api: ContractClient, project: Costed
) -> None:
    # « La grille de devis d'un risque offre les mêmes opérations que celle du projet »: the nine
    # operations of the tree answer on the own estimate, which they alone change, its counter
    # advancing with each write and the risk's with it.
    stage = project.stage
    risk = Risks(api, project).declared("0.5")
    tree = own_tree(project, risk)
    lines = Lines(tree)
    main_before = snapshot(project.tree)
    main_nodes = outside_provision(project.tree)
    assert {each["difference"] for each in tree.items()} == {"unchanged"}
    counted = counter(tree)
    held = risk_counter(project, risk)
    # createNode: a task, a line under it.
    task = tree.made("Grue louée")
    line = lines.made(task, **material(project.costs, "Location", "300.00"))["nodes"][0]
    assert counter(tree) == counted + 2
    assert risk_counter(project, risk) == held + 2
    assert line["estimate_line"]["reestimated_amount"] == "300.00"
    # updateTaskFacet, updateEstimateLine.
    renamed = tree.changed(task, label="Grue louée sur site")["nodes"][0]
    assert renamed["task"]["label"] == "Grue louée sur site"
    priced = lines.changed(line, quantity="2")["nodes"][0]
    assert priced["estimate_line"]["reestimated_amount"] == "600.00"
    # setPredecessors: a second task follows the first.
    second = tree.made("Remise en état")
    answer = link(tree, second, stage.manager, node_of(tree, "Grue louée sur site"))
    assert answer.status_code == 200, answer.text
    # moveNodes: the line goes under the second task.
    sent = {
        "node_ids": [priced["node_id"]],
        "parent_id": node_of(tree, "Remise en état")["node_id"],
        "lock_version": counter(tree),
    }
    moved = api.post(f"{tree.path}/nodes/move", headers=stage.manager.headers, json=sent)
    assert moved.status_code == 200, moved.text
    assert node_of(tree, "Location")["parent_id"] == node_of(tree, "Remise en état")["node_id"]
    # previewPaste, applyPaste: a label pasted.
    plan = planned(tree, node_of(tree, "Remise en état"), "label", [["Remise en état du site"]])
    pasted = apply(tree, plan)
    assert pasted.status_code == 200, pasted.text
    assert node_of(tree, "Remise en état du site")
    # deleteNode: the line goes; the severity of the risk is the total, computed, never entered.
    assert total(tree) == Decimal("600.00")
    assert Decimal(Risks(api, project).risk(risk)["severity"]) == Decimal("600.00")
    gone = delete(tree, node_of(tree, "Location"), stage.manager)
    assert gone.status_code == 200, gone.text
    assert total(tree) == Decimal(0)
    assert Decimal(Risks(api, project).risk(risk)["severity"]) == Decimal(0)
    assert risk_counter(project, risk) > held + 2
    # The main structure keeps its tasks: its provision line alone follows the risk (US-2580).
    kept = [each["task"]["label"] for each in project.tree.items() if each["task"]]
    assert kept == [each["task"]["label"] for each in main_before[0]["items"] if each["task"]]
    assert outside_provision(project.tree) == main_nodes
    # Its counter advances once per move of the provision (150, 300, then nought), none else.
    assert counter(project.tree) == main_before[1] + 3


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_own_estimate_lists_its_commands_without_a_remaining_to_commit(
    api: ContractClient, project: Costed
) -> None:
    risk = Risks(api, project).declared()
    structures = {each["structure_id"]: each for each in listed(api, project)}
    own = commands_of(structures[risk["structure_id"]])
    assert own == {"edit_planning": (True, []), "edit_estimate": (True, [])}


@pytest.mark.requirement("WF-RIS-0030-A")
@pytest.mark.parametrize("state", ["created", "pricing", "in_progress"])
def test_the_own_estimate_is_entered_in_every_state_of_a_project_that_is_not_terminal(
    api: ContractClient, project: Costed, state: str
) -> None:
    # « à tout état non terminal du projet, En cours compris »: the estimate of the main structure
    # is closed In progress (WF-DEV-0050), the own estimate of a risk is not, and carries no
    # remaining to commit.
    risk = Risks(api, project).declared()
    put_in_state(project.stage.owner, str(project.project_id), state)
    structures = {each["structure_id"]: each for each in listed(api, project)}
    if state == "in_progress":
        main = commands_of(structures[project.tree.structure_id])
        assert main["edit_estimate"] == (False, ["project_before_in_progress"])
    assert commands_of(structures[risk["structure_id"]])["edit_estimate"] == (True, [])
    tree = own_tree(project, risk)
    task = tree.made("Grue")
    made = Lines(tree).made(task, **material(project.costs, "Location", "40.00"))
    assert made["nodes"][0]["estimate_line"]["reestimated_amount"] == "40.00"
    changed = Lines(tree).changed(made["nodes"][0], quantity="3")["nodes"][0]
    assert changed["estimate_line"]["reestimated_amount"] == "120.00"
    assert total(tree) == Decimal("120.00")
    assert "edit_remaining" not in commands_of(structures[risk["structure_id"]])


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_own_estimate_is_refused_to_a_terminal_project(
    api: ContractClient, project: Costed
) -> None:
    # The states that are not terminal enter the own estimate; the others refuse it, naming it.
    risk = Risks(api, project).declared()
    mark(project.stage, project.tree.revision)
    put_in_state(project.stage.owner, str(project.project_id), "completed")
    refused = own_tree(project, risk).create("Grue")
    assert refused.status_code == 409, refused.text
    assert refused.json()["params"] == {"missing_condition": "project_not_terminal"}


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_write_in_the_own_estimate_of_a_risk_changes_neither_another_nor_the_main_structure(
    api: ContractClient, project: Costed
) -> None:
    risks = Risks(api, project)
    first = risks.declared("0.5", "Premier")
    second = risks.declared("0.1", "Second")
    main_before = snapshot(project.tree)
    other = own_tree(project, second)
    other_before = snapshot(other)
    held = risk_counter(project, second)
    risks.costed_at(first, project.revision_id, "80.00")
    assert snapshot(other) == other_before
    assert risk_counter(project, second) == held
    # The main structure keeps its tasks and its lines: its provision lines alone follow (US-2580).
    after = [each["task"]["label"] for each in project.tree.items() if each["task"]]
    assert after == [each["task"]["label"] for each in main_before[0]["items"] if each["task"]]
    assert total(own_tree(project, first)) == Decimal("80.00")


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_own_estimate_of_a_risk_is_refused_to_a_revision_marked(
    api: ContractClient, project: Costed
) -> None:
    risk = Risks(api, project).declared()
    tree = own_tree(project, risk)
    mark(project.stage, project.tree.revision)
    refused = tree.create("Grue")
    assert refused.status_code == 409, refused.text
    assert refused.json()["params"] == {"missing_condition": "revision_draft"}


# --- WF-REV-0100-A -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_own_estimate_of_a_risk_is_in_every_revision_marked_after_it(
    api: ContractClient, project: Costed
) -> None:
    # « Un risque déclaré ajoute une structure propre, présente dans chaque révision marquée
    # postérieure tant qu'il n'est pas survenu »: the first revision marked carries it with the
    # estimate it was given, the next one opened by copy takes it up, and it is read as it was.
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    risks.costed_at(risk, project.revision_id, "200.00")
    mark(project.stage, project.tree.revision)
    first = listed(api, project)
    assert [(each["kind"], each["risk_id"]) for each in first if each["kind"] == "risk"] == [
        ("risk", risk["risk_id"])
    ]
    second = risks.revision()
    second_id = second["revision_id"]
    carried = risks.risk(risk, second_id)
    assert carried["structure_id"] != risk["structure_id"]
    path = f"{PROJECTS}/{project.project_id}/revisions/{second_id}/structures"
    held = api.get(path, headers=project.stage.manager.headers).json()
    assert [each["risk_id"] for each in held if each["kind"] == "risk"] == [risk["risk_id"]]
    carried_tree = on(project.tree, carried["structure_id"])
    carried_tree.path = f"{path}/{carried['structure_id']}"
    assert total(carried_tree) == Decimal("200.00")
    # A write in the revision in progress leaves the one marked as it was.
    risks.repriced(risk, second_id, node_of(carried_tree, "Location"), "250.00")
    assert total(carried_tree) == Decimal("250.00")
    marked = own_tree(project, risk)
    assert total(marked) == Decimal("200.00")
    mark(project.stage, second, "v2.0")
    marked_second = api.get(path, headers=project.stage.manager.headers).json()
    assert [each["risk_id"] for each in marked_second if each["kind"] == "risk"] == [
        risk["risk_id"]
    ]
    third = risks.revision()
    assert [
        each["risk_id"]
        for each in api.get(
            f"{PROJECTS}/{project.project_id}/revisions/{third['revision_id']}/structures",
            headers=project.stage.manager.headers,
        ).json()
        if each["kind"] == "risk"
    ] == [risk["risk_id"]]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_provision_line_keeps_its_amount_when_the_reference_year_changes_at_an_opening(
    api: ContractClient, project: Costed, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #3995: a revision opened a year later prices its lines again for its year of reference
    # (#3535). The provision line, in a task of the main structure that falls two years after the
    # first reference, would be projected by one year of inflation less, were it a line like the
    # others: it keeps the severity weighted by the probability the risk sets. The own estimate is
    # dated as the main structure is (EP-30): its line of 200 is projected two years, to 212.18;
    # the revision opened takes up the severity recorded, until the next entry or update (EP-30,
    # "La gravité et la provision"). The severity a revision opened carries is out of date by
    # design: it is that of the last update or entry (WF-RIS-0070), not recomputed at the opening.
    stage = project.stage
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == project.project_id)
            .values(inflation_rate=Decimal("0.03"))
        )
    start = date(YEAR + 2, 1, 3)
    moved = project.tree.api.patch(
        project.tree.path,
        headers=stage.manager.headers,
        json={"planning_start_on": start.isoformat(), "lock_version": counter(project.tree)},
    )
    assert moved.status_code == 200, moved.text
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    risks.costed_at(risk, project.revision_id, "200.00")
    assert (risks.risk(risk)["severity"], risks.risk(risk)["provision_amount"]) == (
        "212.18",
        "106.09",
    )
    plans = node_of(project.tree, "Plans")["estimate_line"]["reestimated_amount"]
    mark(stage, project.tree.revision)
    monkeypatch.setattr(
        "waterfall.api.revisions.utc_now", lambda: datetime(YEAR + 1, 1, 12, tzinfo=UTC)
    )
    second = risks.revision()
    assert second["reference_year"] == YEAR + 1
    carried = on(project.tree, main_of(api, project, second["revision_id"]))
    base = revision_path(project, second["revision_id"])
    carried.path = f"{base}/structures/{carried.structure_id}"
    # The line of material is projected again, the provision line is not.
    assert node_of(carried, "Plans")["estimate_line"]["reestimated_amount"] != plans
    provisions = [
        each["estimate_line"]
        for each in carried.items()
        if each["estimate_line"] and each["estimate_line"]["label"].startswith("Provision")
    ]
    assert [each["reestimated_amount"] for each in provisions] == ["106.09"]
    assert [each["consumption_year"] for each in provisions] == [YEAR + 2]
    read = risks.risk(risk)
    assert (read["severity"], read["provision_amount"]) == ("212.18", "106.09")


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_rate_and_an_inflation_written_after_the_entry_record_the_severity_again(
    api: ContractClient, project: Costed, costs: Costing
) -> None:
    # The rate of a role and the inflation price again the own estimate and its base, which the
    # entries of a risk do not write: the severity is recorded again by that write too, from the
    # amounts of the structures as they stand, and the provision with it (EP-30, "La gravité et la
    # provision"; #1453).
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    own = own_tree(project, risk)
    wiring = own.made("Câblage")
    labour = {"quantity": "1", "resource_role_id": str(costs.role), "hours": "10"}
    Lines(own).made(wiring, label="Câblage MO", **labour)
    later = own.made(
        "Exploitation",
        task={
            "scheduling_mode": "manual",
            "start": {"date": f"{YEAR + 2}-11-06"},
            "finish": {"date": f"{YEAR + 2}-11-07"},
        },
    )
    Lines(own).made(later, label="Exploitation MO", **labour)
    before = risks.risk(risk)
    added = ("Câblage MO", "Exploitation MO")

    def gap() -> Decimal:
        return sum(
            (Decimal(node_of(own, each)["estimate_line"]["reestimated_amount"]) for each in added),
            Decimal("0.00"),
        )

    assert Decimal(before["severity"]) == gap() > 0
    set_inflation(api, project.stage, "0.03")
    correct_rate(project.stage, costs, "70.00")
    read = risks.risk(risk)
    assert Decimal(read["severity"]) == gap() != Decimal(before["severity"])
    assert node_of(own, "Câblage MO")["estimate_line"]["reestimated_amount"] == "700.00"
    # The provision is half the severity at 50 %, to the cent.
    assert abs(Decimal(read["provision_amount"]) * 2 - Decimal(read["severity"])) <= Decimal("0.01")


def revision_path(project: Costed, revision_id: str) -> str:
    """Give the path of a revision of the project."""
    return f"{PROJECTS}/{project.project_id}/revisions/{revision_id}"


def main_of(api: ContractClient, project: Costed, revision_id: str) -> str:
    """Give the main structure of a revision of the project."""
    path = f"{revision_path(project, revision_id)}/structures"
    held = api.get(path, headers=project.stage.manager.headers).json()
    return next(each["structure_id"] for each in held if each["kind"] == "main")
