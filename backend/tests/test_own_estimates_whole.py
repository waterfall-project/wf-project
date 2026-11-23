# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own estimate of a risk whole: born with its base, read against it, its severity a gap.

US-3070/L3, on the project costed at 1 000 (``risks_support.costed``) given a line of labour of 100
hours under ``Étude``. ``createRisk`` copies the main structure twice, the own estimate and its
base; ``listNodes`` reads the own estimate against its base (``NodeDifference``); the writes of the
tree apply to it as to a differential, without a provision line, an attachment, a tracking or a
start of its own; each write records the severity, the gap of the totals of the own estimate and
of its base, and advances the counter of the risk (EP-30, "La gravité et la provision"). Every
answer is checked against the contract (``ContractClient``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import listed, on
from estimate_support import Costing, Lines, costing
from history_support import delete
from nodes_support import set_progress
from paste_support import counter
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, Risks, costed
from sqlalchemy import select
from test_amendments_tracking import task_of, timeline, track

from waterfall.core.risks.tables import Risk, RiskEvaluation

if TYPE_CHECKING:
    from nodes_support import Tree
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The line of labour of the main structure, 100 hours at 65.00, which the own estimate carries to
# 130; the task it adds, and the amount of the line of the task it abandons.
WIRING, HOURS, RATE = "Câblage", "100", Decimal("65.00")
ADDED = "Renfort"
ABANDONED_AMOUNT = Decimal("400.00")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the labour at 65.00 an hour."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000, and a line of labour of 100 hours under ``Étude``."""
    made = costed(api, stage, costs)
    labour = {
        "label": WIRING,
        "quantity": "1",
        "resource_role_id": str(costs.role),
        "hours": HOURS,
    }
    made.lines.made(str(made.tasks[STUDY]), **labour)
    return made


def labelled(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Give the nodes read, by the label of their task or of their line."""
    return {(each["task"] or each["estimate_line"])["label"]: each for each in items}


def outside_provisions(tree: Tree) -> list[str]:
    """Read the labels of a structure in their order, its provision lines left out."""
    return [
        (each["task"] or each["estimate_line"])["label"]
        for each in tree.items()
        if not (each["estimate_line"] or {"label": ""})["label"].startswith("Provision")
    ]


def structure(api: ContractClient, project: Costed, structure_id: str) -> dict[str, Any]:
    """Read a structure of the current revision as the list gives it."""
    return next(each for each in listed(api, project) if each["structure_id"] == structure_id)


def recorded(project: Costed, risk: dict[str, Any]) -> tuple[Decimal | None, int]:
    """Read, around the service, the severity a risk recorded and the counter of the risk."""
    with project.stage.database.transaction() as session:
        severity = session.scalar(
            select(RiskEvaluation.severity).where(
                RiskEvaluation.risk_id == UUID(risk["risk_id"]),
                RiskEvaluation.revision_id == project.revision_id,
            )
        )
        held = session.scalar(select(Risk.lock_version).where(Risk.id == UUID(risk["risk_id"])))
    assert held is not None
    return severity, held


def designated(project: Costed, own: Tree) -> None:
    """Make an own estimate add a task, carry the line of labour to 130 hours, abandon a task."""
    who = project.stage.manager
    own.made(ADDED)
    wiring = labelled(own.items())[WIRING]
    Lines(own).changed(wiring, hours="130")
    answer = delete(own, labelled(own.items())[MAKING], who)
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_risk_declared_reads_the_main_structure_whole_and_designates_nothing(
    api: ContractClient, project: Costed
) -> None:
    # « La grille d'un devis propre qui vient d'être créé présente les tâches et les lignes de la
    # structure principale, aucune n'étant présentée ajoutée, modifiée ou retirée. »
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    own = on(project.tree, risk["structure_id"])
    read = own.read().json()
    assert outside_provisions(own) == outside_provisions(project.tree)
    assert {each["difference"] for each in read["items"]} == {"unchanged"}
    assert read["totals"]["reestimated_amount"] == "7500.00"
    held = structure(api, project, risk["structure_id"])
    main = structure(api, project, project.tree.structure_id)
    assert (held["is_up_to_date"], held["is_pruned"]) == (True, False)
    assert held["planning_start_on"] == main["planning_start_on"]
    assert (main["is_up_to_date"], main["is_pruned"]) == (None, None)
    read_risk = risks.risk(risk)
    assert (read_risk["severity"], read_risk["provision_amount"]) == ("0.00", "0.00")


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_task_added_a_line_carried_to_130_hours_and_a_task_abandoned_read_so(
    api: ContractClient, project: Costed
) -> None:
    # « Dans le devis propre d'un risque, une tâche ajoutée après une tâche du projet, une ligne
    # existante portée de 100 à 130 heures et une tâche existante abandonnée sont présentées
    # ajoutée, modifiée et retirée ; la structure principale est inchangée. »
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    own = on(project.tree, risk["structure_id"])
    main_before = (outside_provisions(project.tree), counter(project.tree))
    designated(project, own)
    read = labelled(own.items())
    assert read[ADDED]["difference"] == "added"
    assert read[WIRING]["difference"] == "modified"
    assert "reestimated_amount" in read[WIRING]["changes"]
    assert read[WIRING]["estimate_line"]["hours"] == "130"
    assert read[MAKING]["difference"] == "removed"
    assert read[MAKING]["editable_fields"] == []
    assert read["Plans"]["difference"] == "unchanged"
    marks = {each["difference"] for each in own.items("?difference=added,modified,removed")}
    assert marks == {"added", "modified", "removed"}
    # The main structure keeps its nodes and its figures; its counter moved by the provision line
    # alone, which the risk writes at each write of its own estimate (US-2580).
    assert outside_provisions(project.tree) == main_before[0]
    assert labelled(project.tree.items())[WIRING]["estimate_line"]["hours"] == HOURS
    assert counter(project.tree) > main_before[1]
    # The severity is the gap: 30 hours more, the line of 400 abandoned.
    gap = RATE * 30 - ABANDONED_AMOUNT
    assert Decimal(risks.risk(risk)["severity"]) == gap


@pytest.mark.story("US-3070")
def test_each_entry_records_the_severity_and_advances_the_risk(
    api: ContractClient, project: Costed
) -> None:
    # Toute saisie dans le devis propre avance ``Risk.lock_version`` et recalcule la gravité et la
    # provision dans la même écriture (#1453, US-3080): recorded, never computed at the reading.
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    own = on(project.tree, risk["structure_id"])
    assert recorded(project, risk) == (Decimal("0.00"), 1)
    own.made(ADDED)
    severity, held = recorded(project, risk)
    assert (severity, held) == (Decimal("0.00"), 2)
    Lines(own).changed(labelled(own.items())[WIRING], hours="130")
    severity, after = recorded(project, risk)
    assert (severity, after) == (RATE * 30, held + 1)
    read = risks.risk(risk)
    assert (read["severity"], read["provision_amount"]) == ("1950.00", "975.00")
    answer = delete(own, labelled(own.items())[MAKING], project.stage.manager)
    assert answer.status_code == 200, answer.text
    assert recorded(project, risk) == (RATE * 30 - ABANDONED_AMOUNT, after + 1)
    # A write of the main structure leaves the severity recorded, and the own estimate out of date.
    project.tree.made("Recette")
    assert recorded(project, risk)[0] == RATE * 30 - ABANDONED_AMOUNT
    assert structure(api, project, risk["structure_id"])["is_up_to_date"] is False


@pytest.mark.story("US-3070")
def test_an_abandon_that_outweighs_the_additions_records_a_negative_severity_provisioning_nothing(
    api: ContractClient, project: Costed
) -> None:
    # The gap is signed: an own estimate that abandons more than it adds is an opportunity, whose
    # provision does not go below nought (EP-30, "La gravité et la provision").
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    own = on(project.tree, risk["structure_id"])
    answer = delete(own, labelled(own.items())[MAKING], project.stage.manager)
    assert answer.status_code == 200, answer.text
    assert recorded(project, risk)[0] == -ABANDONED_AMOUNT
    assert risks.risk(risk)["provision_amount"] == "0.00"


@pytest.mark.story("US-3070")
def test_the_own_estimate_bears_no_provision_line_nor_remaining_nor_start_of_its_own(
    api: ContractClient, project: Costed
) -> None:
    # « le devis propre ne porte ni ligne de provision — la sienne, comme celles des autres risques,
    # n'y figure pas —, ni […] reste à engager ; […] il n'a pas de date de début de planning à lui,
    # celle de la structure principale étant la sienne »
    risks = Risks(api, project)
    first = risks.declared("0.5", "Premier")
    second = risks.declared("0.2", "Second")
    provisions = {
        each["estimate_line"]["label"]
        for each in project.tree.items()
        if each["estimate_line"] and each["estimate_line"]["label"].startswith("Provision")
    }
    assert len(provisions) == 2
    for risk in (first, second):
        own = on(project.tree, risk["structure_id"])
        labels = set(outside_provisions(own))
        assert not labels & provisions
        assert "edit_remaining" not in {
            each["command"]
            for each in structure(api, project, risk["structure_id"])["available_commands"]
        }
    own = on(project.tree, first["structure_id"])
    held = structure(api, project, first["structure_id"])
    moved = api.patch(
        own.path,
        headers=project.stage.manager.headers,
        json={"planning_start_on": "2026-12-07", "lock_version": held["lock_version"]},
    )
    assert moved.status_code == 422, moved.text
    assert [(each["pointer"], each["code"]) for each in moved.json()["fields"]] == [
        ("/planning_start_on", "FIELD_READ_ONLY")
    ]


@pytest.mark.story("US-3070")
def test_an_inscription_on_a_task_of_the_own_estimate_is_refused_as_on_a_differential(
    api: ContractClient, project: Costed
) -> None:
    # « ni rattachement au lotissement, ni avancement […] ; […] ``setNodeTracking`` y [est refusé]
    # comme sur un différentiel (WF-PLA-0170, #2497) »: the inscriptions are the main structure's.
    risk = Risks(api, project).declared("0.5")
    own = on(project.tree, risk["structure_id"])
    study = task_of(own, STUDY)
    assert "task.tracking" not in study["editable_fields"]
    before = (counter(own), own.read().json())
    answer = track(own, study, {"kind": "timeline", "timeline_id": timeline(api, project)})
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": "main_structure"}
    assert (counter(own), own.read().json()) == before


@pytest.mark.story("US-3070")
def test_two_risks_are_prepared_each_alone(api: ContractClient, project: Costed) -> None:
    # « deux risques se préparent chacun seul : le devis propre de l'un ne présente rien de ce que
    # l'autre désigne »
    risks = Risks(api, project)
    first = risks.declared("0.5", "Premier")
    second = risks.declared("0.2", "Second")
    designated(project, on(project.tree, first["structure_id"]))
    other = on(project.tree, second["structure_id"])
    assert {each["difference"] for each in other.items()} == {"unchanged"}
    assert ADDED not in labelled(other.items())
    assert labelled(other.items())[WIRING]["estimate_line"]["hours"] == HOURS
    assert risks.risk(second)["severity"] == "0.00"


@pytest.mark.story("US-3070")
def test_a_line_of_a_completed_task_is_modified_and_a_completed_task_abandoned_in_the_own_estimate(
    api: ContractClient, project: Costed
) -> None:
    # « une ligne d'une tâche terminée se modifie dans un devis propre, et une tâche terminée s'y
    # abandonne, quand la structure principale refuse la saisie sous elle »
    risks = Risks(api, project)
    for label in (STUDY, MAKING):
        set_progress(project.stage, str(project.tasks[label]), "completed", date(2026, 3, 2))
    risk = risks.declared("0.5")
    main_line = labelled(project.tree.items())[WIRING]
    refused = Lines(project.tree).change(main_line, hours="130")
    assert refused.status_code == 409, refused.text
    assert refused.json()["params"] == {"missing_condition": "task_not_completed"}
    own = on(project.tree, risk["structure_id"])
    assert labelled(own.items())[STUDY]["task"]["progress"] == "completed"
    Lines(own).changed(labelled(own.items())[WIRING], hours="130")
    answer = delete(own, labelled(own.items())[MAKING], project.stage.manager)
    assert answer.status_code == 200, answer.text
    read = labelled(own.items())
    assert (read[WIRING]["difference"], read[MAKING]["difference"]) == ("modified", "removed")
