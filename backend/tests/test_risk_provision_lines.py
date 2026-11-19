# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision line of a risk in the state of its task, the estimate and the grid (US-2580/L2).

The rules EP-07 and EP-09 wrote for a line of the provision kind, proved on the line of a risk
declared through the service: it holds no task open — a summary whose subordinates are completed is
completed and not signalled, a milestone that bears it alone is completed from the Kanban
(WF-PLA-0040, WF-PLA-0050) —; it needs no hourly rate (WF-DEV-0010), is never projected
(WF-DEV-0030), and moves with the rate of inflation only by what its own estimate, priced again,
gives its severity (WF-PRJ-0040); the grid neither moves nor deletes it, its risk alone writing it
(#4007). Every answer is checked against the contract (``ContractClient``).
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import YEAR, Costing, Lines, costing
from nodes_support import Tree, refusal
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, task_named
from planning_support import insert_task
from risks_support import (
    RISK_LABEL,
    Costed,
    Risks,
    costed,
    differential,
    material,
    material_line,
)
from sqlalchemy import delete, select

from waterfall.core.cost_settings.tables import HourlyRate
from waterfall.core.estimate.tables import RevisionRate
from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MILESTONE = {"duration": {"value": "0", "unit": "d"}}
TUESDAY = DAY + timedelta(days=1)
CENT = Decimal("0.01")
STATE = "STATE_FORBIDS_OPERATION"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision, in pricing."""
    return costed(api, stage, costs)


@pytest.fixture
def risks(api: ContractClient, project: Costed) -> Risks:
    """Give the risks of the project costed."""
    return Risks(api, project)


def running(api: ContractClient, stage: Scene, costs: Costing) -> Risks:
    """Give the risks of a project In progress: the hazards over their trial, a milestone, a task.

    The reference written, marked and designated, then the current revision opened from it
    (``in_progress``); the hazards bear no line of their own, the milestone none, the assembly its
    fixings at 50.
    """

    def build(tree: Tree, lines: Lines) -> None:
        hazards = tree.made("Aléas")
        tree.made("Essai", parent_id=hazards["node_id"])
        tree.made("Jalon", task=MILESTONE)
        assembly = tree.made("Montage")
        lines.made(assembly, **material(costs, "Fixations", "50"))

    review: Review = in_progress(api, stage, build)
    tree = review.tree
    tasks = {each["task"]["label"]: UUID(each["node_id"]) for each in tree.items("?kinds=task")}
    held = Costed(
        stage,
        costs,
        tree,
        review.lines,
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
        tasks,
    )
    return Risks(api, held)


def gesture(tree: Tree, label: str, progress: str, on: date) -> Any:
    """Send the state of the card of a task, at the counter read, on the day said."""
    node = task_named(tree, label)
    sent = {"progress": progress, "lock_version": node["lock_version"], "occurred_on": str(on)}
    path = f"{tree.path}/nodes/{node['node_id']}/progress"
    return tree.api.put(path, headers=tree.stage.manager.headers, json=sent)


def moved(tree: Tree, label: str, progress: str, on: date) -> dict[str, Any]:
    """Send a gesture that must be accepted; give what is answered."""
    answer = gesture(tree, label, progress, on)
    assert answer.status_code == 200, answer.text
    return answer.json()


def state(node: dict[str, Any]) -> tuple[str, str | None, str | None, bool]:
    """Give the state of a task, its two dates and whether it awaits only its own lines."""
    task = node["task"]
    return task["progress"], task["started_on"], task["completed_on"], task["awaiting_own_lines"]


def board(risks: Risks) -> dict[str, dict[str, dict[str, Any]]]:
    """Read the Kanban as the manager does: the cards of each column, by the label of their task."""
    path = f"{risks.base}/remaining-indicators/startable-tasks"
    answer = risks.api.get(path, headers=risks.headers)
    assert answer.status_code == 200, answer.text
    return {
        column: {card["task"]["label"]: card for card in cards}
        for column, cards in answer.json().items()
    }


# --- The state of a task and the Kanban ---------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_whose_only_own_line_is_the_provision_of_a_risk_is_completed_unsignalled(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « Une récapitulative dont toutes les subordonnées sont terminées et dont la seule ligne propre
    # est une provision de 40 est terminée et n'est pas signalée. » A risk of 200 at 20 % bears its
    # provision of 40 on the hazards: their trial completed, the hazards are completed with it, and
    # neither the reading nor the Kanban signals them.
    risks = running(api, stage, costs)
    tree = risks.project.tree
    risk = risks.declared_costed(
        probability="0.2", provision_task_id=str(risks.project.tasks["Aléas"])
    )
    assert (risk["provision_amount"], risk["provision_task"]["label"]) == ("40.00", "Aléas")
    moved(tree, "Essai", "started", DAY)
    [hazards] = moved(tree, "Essai", "completed", TUESDAY)["ancestors"]
    completed = ("completed", DAY.isoformat(), TUESDAY.isoformat(), False)
    assert state(hazards) == completed
    assert state(task_named(tree, "Aléas")) == completed
    assert line_named(tree, f"Provision — {RISK_LABEL}")["estimate_line"]["reestimated_amount"] == (
        "40.00"
    )
    columns = board(risks)
    assert "Aléas" not in {label for cards in columns.values() for label in cards}
    assert "Essai" in columns["completed"]


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_milestone_that_bears_only_the_provision_of_a_risk_is_completed_from_the_kanban(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « Un jalon qui ne porte qu'une ligne de provision est terminé depuis le Kanban. » : its card
    # offers the completion, which ``setTaskProgress`` accepts, the milestone completed that day.
    risks = running(api, stage, costs)
    tree = risks.project.tree
    risks.declared_costed(provision_task_id=str(risks.project.tasks["Jalon"]))
    card = board(risks)["not_started"]["Jalon"]
    complete = next(each for each in card["available_commands"] if each["command"] == "complete")
    assert (complete["progress"], complete["is_available"], complete["missing_conditions"]) == (
        "completed",
        True,
        [],
    )
    [milestone] = moved(tree, "Jalon", "completed", DAY)["nodes"]
    assert state(milestone) == ("completed", DAY.isoformat(), DAY.isoformat(), False)
    assert "Jalon" in board(risks)["completed"]


# --- The estimate: no rate, no projection, the inflation through the own estimate ----------------


def indicators(risks: Risks) -> dict[str, Any]:
    """Read the indicators of the estimate of the current revision."""
    return risks.indicators()


def missing_rates(risks: Risks) -> list[dict[str, Any]]:
    """Read the rates the estimate lacks, as the manager does."""
    answer = risks.api.get(f"{risks.base}/estimate-indicators/missing-rates", headers=risks.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


@pytest.mark.requirement("WF-DEV-0010-A")
def test_an_estimate_of_lines_outside_labour_and_a_provision_is_computed_without_any_rate(
    risks: Risks, project: Costed
) -> None:
    # « Un devis qui ne porte que des lignes hors main-d'œuvre et une ligne de provision se calcule
    # sans aucun taux horaire. » : the material of 1 000 and the provision of 60 of a risk whose own
    # estimate is of material too, no hourly rate left anywhere — the reference's nor the
    # revision's.
    risks.declared_costed()
    with project.stage.owner.begin() as connection:
        connection.execute(delete(RevisionRate))
        connection.execute(delete(HourlyRate))
        assert connection.scalar(select(HourlyRate.id)) is None
    assert missing_rates(risks) == []
    found = indicators(risks)
    assert found["total"] == {"is_computable": True, "value": "1060.00", "reason": None}
    assert all(each["amount"]["is_computable"] for each in found["by_cost_type"])


def inflated(risks: Risks, rate: str) -> None:
    """Change the rate of inflation of the project at the counter read; it must be changed."""
    held = risks.api.get(risks.base, headers=risks.headers).json()["lock_version"]
    sent = {"inflation_rate": rate, "lock_version": held}
    answer = risks.api.patch(risks.base, headers=risks.headers, json=sent)
    assert answer.status_code == 200, answer.text


def later(years: int) -> dict[str, Any]:
    """Give the facet of a manual task of two days, some years after the year of reference."""
    start = date(YEAR + years, 3, 1)
    start += timedelta(days=-start.weekday() % 7)
    return {
        "scheduling_mode": "manual",
        "start": {"date": start.isoformat()},
        "finish": {"date": (start + timedelta(days=1)).isoformat()},
    }


def provision_line(risks: Risks, risk: dict[str, Any]) -> dict[str, Any]:
    """Read the provision line of a risk in the main structure."""
    return risks.project.tree.node(risk["provision_node_id"])["estimate_line"]


def projected(amount: str, years: int) -> str:
    """Give an amount consumed some years after the reference, at 3 % a year, to the cent."""
    return str((Decimal(amount) * Decimal("1.03") ** years).quantize(CENT, ROUND_HALF_UP))


@pytest.mark.requirement("WF-DEV-0030-A")
def test_a_provision_line_borne_two_years_after_the_reference_is_not_projected(
    risks: Risks, project: Costed
) -> None:
    # « Une ligne de provision portée par une tâche consommée deux ans après l'année de référence
    # vaut sa gravité pondérée par sa probabilité, sans autre projection. » At 3 %, the material of
    # the same task is worth 1.03 x 1.03 its base; the provision of 200 at 30 % stays at 60.
    inflated(risks, "0.03")
    task = project.tree.made("Exploitation", task=later(2))
    beside = project.lines.made(task, **material(project.costs, "Pièces", "100.00"))["nodes"][0]
    assert beside["estimate_line"]["reestimated_amount"] == projected("100.00", 2)
    risk = risks.declared_costed(provision_task_id=task["node_id"])
    line = provision_line(risks, risk)
    assert (line["consumption_year"], line["base_amount"], line["reestimated_amount"]) == (
        YEAR + 2,
        "60.00",
        "60.00",
    )
    assert risks.risk(risk)["provision_amount"] == "60.00"


def own_later(risks: Risks, risk: dict[str, Any], amount: str) -> None:
    """Write in the own estimate of a risk a task two years later, bearing material at an amount."""
    path = risks.own(risk, risks.project.revision_id)
    made = risks.made(path, {"kind": "task", "parent_id": None, "task": {"label": "Grue"}})
    sent = {"lock_version": made["lock_version"], **later(2)}
    changed = risks.api.patch(
        f"{path}/{made['node_id']}/task", headers=risks.headers, json=sent
    )
    assert changed.status_code == 200, changed.text
    line = material(risks.project.costs, "Location", amount)
    risks.made(path, {"kind": "estimate_line", "parent_id": made["node_id"], "estimate_line": line})


@pytest.mark.requirement("WF-PRJ-0040-A")
def test_a_provision_changes_with_the_inflation_only_by_its_own_estimate_priced_again(
    risks: Risks, project: Costed
) -> None:
    # « … une ligne de provision ne change que par son devis propre. » Two risks at 30 %, each of
    # 200 of material: the first consumed two years after the reference, its severity priced again
    # at 3 % to 212.18 and its provision to 63.65; the second consumed in the year of reference,
    # its provision of 60 unchanged though its line is borne by a task two years later.
    task = project.tree.made("Exploitation", task=later(2))
    moving = risks.declared_costed(amount=None, label="Grue indisponible")
    own_later(risks, moving, "200.00")
    staying = risks.declared_costed(label="Sol instable", provision_task_id=task["node_id"])
    assert [risks.risk(each)["provision_amount"] for each in (moving, staying)] == [
        "60.00",
        "60.00",
    ]
    inflated(risks, "0.03")
    severity = projected("200.00", 2)
    assert severity == "212.18"
    provision = str((Decimal(severity) * Decimal("0.3")).quantize(CENT, ROUND_HALF_UP))
    first, second = risks.risk(moving), risks.risk(staying)
    assert (first["severity"], first["provision_amount"]) == (severity, provision)
    assert (second["severity"], second["provision_amount"]) == ("200.00", "60.00")
    assert provision_line(risks, moving)["reestimated_amount"] == provision
    assert provision_line(risks, staying)["reestimated_amount"] == "60.00"


# --- The grid does not write it -------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_provision_line_of_a_risk_is_not_deleted_from_the_grid_and_its_risk_is_named(
    risks: Risks, project: Costed
) -> None:
    # The line is written by its risk alone (« propre à l'US », #4007): its deletion from the grid
    # is refused by ``line_not_provision``, the risk named as ``at_least_one_task`` names it, and
    # nothing is deleted — neither the line nor the provision of the estimate.
    risk = risks.declared_costed()
    line = project.tree.node(risk["provision_node_id"])
    refused = risks.delete(line)
    assert refusal(refused) == (
        409,
        STATE,
        {
            "missing_condition": "line_not_provision",
            "risks": [{"risk_id": risk["risk_id"], "label": RISK_LABEL}],
        },
    )
    kept = project.tree.node(risk["provision_node_id"])
    assert (kept["lock_version"], kept["estimate_line"]["reestimated_amount"]) == (
        line["lock_version"],
        "60.00",
    )
    assert risks.indicators()["total"]["value"] == "1060.00"
    assert risks.risk(risk)["lock_version"] == risk["lock_version"]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_line_of_a_category_of_provision_in_a_differential_is_deleted_as_any_other(
    risks: Risks, project: Costed
) -> None:
    # Only the main structure bears the provision of a risk: a differential holds lines of that
    # category and no provision (#4008), and the grid deletes them as any other line.
    structure_id = differential(project)
    with project.stage.owner.begin() as connection:
        task = insert_task(
            connection, project.project_id, project.revision_id, structure_id, label="Avenant"
        )
        line = material_line(
            connection,
            (project.project_id, project.revision_id, structure_id, task),
            project.costs.provision,
            Decimal("50.00"),
        )
        held = connection.scalar(select(Node.lock_version).where(Node.id == line))
    path = (
        f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
        f"/structures/{structure_id}/nodes/{line}"
    )
    answer = risks.api.delete(path, headers=risks.headers, params={"lock_version": held})
    assert answer.status_code == 200, answer.text
