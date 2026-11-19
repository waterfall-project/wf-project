# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The severity, the counter and the identity of a risk, through the service (US-2570/L1).

The severity is the total of the own estimate, computed: every entry in it advances the counter of
the risk with the structure's, and writes its provision line again (#1453, WF-RIS-0010). The
identity is a datum of the project (H-02, #1783): written without creating a revision nor entering
the history, never undone by an abandonment, the counter of the risk advancing at every write and
never going back. A risk read in a marked revision is the one that revision froze (WF-RIS-0030);
the copy of a revision takes the evaluations up, and its abandonment takes them away. Every answer
is checked against the contract (``ContractClient``).
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from history_support import undone
from nodes_support import entries, mark, signed_in
from projects_support import PROJECTS, Person, Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import LABEL, Costed, Risks, costed
from sqlalchemy import func, select

from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import RiskEvaluation
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def risks(api: ContractClient, project: Costed) -> Risks:
    """Give the risks of the project costed."""
    return Risks(api, project)


def main_line(project: Costed, node_id: str) -> dict[str, Any]:
    """Read the provision line of the main structure, as the grid reads it."""
    return project.tree.node(node_id)["estimate_line"]


def main_counter(project: Costed) -> int:
    """Read the counter of the main structure of the current revision."""
    with project.stage.database.transaction() as session:
        held = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == project.structure_id)
        )
    assert held is not None
    return held


def revisions_of(project: Costed) -> int:
    """Count the revisions of the project."""
    with project.stage.database.transaction() as session:
        held = session.scalar(select(func.count()).where(Revision.project_id == project.project_id))
    return held or 0


# --- The severity and the counter -----------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_severity_and_the_provision_follow_every_entry_of_the_own_estimate(
    risks: Risks, project: Costed
) -> None:
    # Declared at 30 %, its own estimate empty: a task, then a line of 200, then 250. Each entry
    # advances the counter of the risk with the structure's; the severity is the total, the
    # provision line of the main structure carries it weighted by the probability.
    risk = risks.declared()
    revision = project.revision_id
    counter = main_counter(project)
    line = risks.costed_at(risk, revision, "200.00")
    read = risks.risk(risk)
    assert (read["severity"], read["provision_amount"], read["lock_version"]) == (
        "200.00",
        "60.00",
        3,
    )
    assert main_line(project, risk["provision_node_id"])["reestimated_amount"] == "60.00"
    assert main_counter(project) == counter + 1
    risks.repriced(risk, revision, line, "250.00")
    read = risks.risk(risk)
    assert (read["severity"], read["provision_amount"], read["lock_version"]) == (
        "250.00",
        "75.00",
        4,
    )
    provision = main_line(project, risk["provision_node_id"])
    assert (provision["unit_disbursement"], provision["base_amount"]) == ("75.00", "75.00")


@pytest.mark.requirement("WF-RIS-0010-A")
def test_an_entry_that_moves_no_amount_advances_the_counter_of_the_risk_alone(
    risks: Risks, project: Costed
) -> None:
    # A task created in the own estimate changes no amount: the counter of the risk advances, the
    # main structure is left as it was.
    risk = risks.declared()
    counter = main_counter(project)
    path = risks.own(risk, project.revision_id)
    risks.made(path, {"kind": "task", "parent_id": None, "task": {"label": "Grue"}})
    read = risks.risk(risk)
    assert (read["severity"], read["lock_version"]) == ("0.00", 2)
    assert main_counter(project) == counter


# --- The identity ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_identity_is_written_without_a_revision_and_no_abandonment_undoes_it(
    risks: Risks, project: Costed
) -> None:
    # Declared, then the revision marked: the project has no current revision, and the change of
    # the identity creates none. A revision opened and abandoned after does not bring it back, and
    # the counter of the risk never goes back.
    risk = risks.declared()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    before = revisions_of(project)
    answer = risks.update(risk, mitigation_notes="Réserver une seconde grue.")
    assert answer.status_code == 200, answer.text
    changed = answer.json()
    assert (changed["mitigation_notes"], changed["lock_version"]) == (
        "Réserver une seconde grue.",
        2,
    )
    assert changed["audit"]["updated_by"]["user_id"] == str(project.stage.manager.user_id)
    assert revisions_of(project) == before
    opened = risks.revision()
    renamed = risks.update(risks.risk(risk), label="Grue indisponible").json()
    assert renamed["lock_version"] == 3
    risks.abandon(opened)
    after = risks.risk(risk)
    assert (after["label"], after["mitigation_notes"]) == (
        "Grue indisponible",
        "Réserver une seconde grue.",
    )
    assert after["lock_version"] == 4


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_identity_does_not_enter_the_history(
    risks: Risks, project: Costed, realm: TestRealm
) -> None:
    # A task created, then the identity changed, by a contributor whose writes the history keeps:
    # the undoing undoes the task, and leaves the identity and the counter of the risk as they are.
    writer = signed_in(project.stage, realm)
    risk = risks.declared()
    created = project.tree.create("Essais", writer)
    assert created.status_code == 201, created.text
    task = created.json()["nodes"][0]
    changed = risks.update(risk, writer, description="Grue louée.").json()
    undone(project.tree, writer)
    assert task["node_id"] not in {each["node_id"] for each in project.tree.items()}
    after = risks.risk(risk)
    assert (after["description"], after["lock_version"]) == ("Grue louée.", changed["lock_version"])


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_change_of_the_identity_is_refused_stale_unknown_or_on_a_terminal_project(
    risks: Risks, project: Costed
) -> None:
    risk = risks.declared()
    stale = risks.update({**risk, "lock_version": 7}, label="Autre")
    assert stale.status_code == 412, stale.text
    assert stale.json()["params"] == {"expected_lock_version": 1}
    unknown = risks.update({**risk, "risk_id": str(project.revision_id)})
    assert unknown.status_code == 404, unknown.text
    put_in_state(project.stage.owner, project.stage.project["project_id"], "abandoned")
    terminal = risks.update(risk, label="Autre")
    assert terminal.status_code == 409, terminal.text
    assert terminal.json()["params"] == {"missing_condition": "project_not_terminal"}
    assert risks.risk(risk)["available_commands"] == []
    assert risks.risk(risk)["label"] == LABEL


# --- The revisions --------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_marked_revision_freezes_the_risk_and_the_copy_takes_it_up(
    risks: Risks, project: Costed
) -> None:
    # Severity 200 when the revision is marked; the copy opened takes the risk up, its own estimate
    # and its provision line under identifiers of their own, and its line changed to 300 there
    # leaves the marked revision as it was.
    risk = risks.declared()
    marked = project.revision_id
    risks.costed_at(risk, marked, "200.00")
    mark(project.stage, {"revision_id": str(marked)})
    current = UUID(risks.revision()["revision_id"])
    copied = risks.risk(risk)
    assert copied["structure_id"] != risk["structure_id"]
    assert copied["provision_node_id"] != risk["provision_node_id"]
    assert (copied["severity"], copied["provision_amount"]) == ("200.00", "60.00")
    path = risks.own(risk, current)
    line = next(
        each
        for each in risks.api.get(path, headers=risks.headers).json()["items"]
        if each["kind"] == "estimate_line"
    )
    risks.repriced(risk, current, line, "300.00")
    assert risks.risk(risk)["severity"] == "300.00"
    frozen = risks.risk(risk, marked)
    assert (frozen["severity"], frozen["provision_amount"], frozen["structure_id"]) == (
        "200.00",
        "60.00",
        risk["structure_id"],
    )
    assert frozen["available_commands"][-1] == {
        "command": "delete",
        "is_available": False,
        "missing_conditions": ["risk_not_cited"],
    }


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_abandonment_takes_the_evaluations_of_its_revision_away_and_advances_the_risks(
    risks: Risks, project: Costed
) -> None:
    # A risk of the marked revision is read there again once the copy is abandoned, its counter
    # advanced; one the abandoned revision declared is read nowhere.
    kept = risks.declared()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    opened = risks.revision()
    gone = risks.declared()
    risks.abandon(opened)
    after = risks.risk(kept)
    assert (after["lock_version"], after["structure_id"]) == (2, kept["structure_id"])
    assert risks.read(gone).status_code == 404
    with project.stage.database.transaction() as session:
        evaluations = session.scalars(
            select(RiskEvaluation.revision_id).where(
                RiskEvaluation.project_id == project.project_id
            )
        ).all()
    assert evaluations == [project.revision_id]
    assert Decimal(after["probability"]) == Decimal("0.3")


# --- The entries that advance the counter, and the provision that is never projected --------------


def deleted_by(
    risks: Risks, risk: dict[str, Any], revision_id: object, line: dict[str, Any], who: Person
) -> None:
    """Delete a node of the own estimate of a risk, as ``who`` does, at the counter read."""
    path = f"{risks.own(risk, revision_id)}/{line['node_id']}?lock_version={line['lock_version']}"
    answer = risks.api.delete(path, headers=who.headers)
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_deletion_and_the_undoing_of_an_entry_of_the_own_estimate_advance_the_counter(
    risks: Risks, project: Costed, realm: TestRealm
) -> None:
    # « …toute saisie dans le devis propre fait avancer `Risk.lock_version` » : la suppression de
    # la ligne, puis son annulation, avancent le compteur du risque et suivent la provision.
    writer = signed_in(project.stage, realm)
    risk = risks.declared()
    line = risks.costed_at(risk, project.revision_id, "200.00")
    before = risks.risk(risk)
    assert (before["severity"], before["provision_amount"]) == ("200.00", "60.00")
    deleted_by(risks, risk, project.revision_id, line, writer)
    deleted = risks.risk(risk)
    assert (deleted["severity"], deleted["provision_amount"]) == ("0.00", "0.00")
    assert deleted["lock_version"] > before["lock_version"]
    assert main_line(project, risk["provision_node_id"])["reestimated_amount"] == "0.00"
    undone(project.tree, writer)
    restored = risks.risk(risk)
    assert (restored["severity"], restored["provision_amount"]) == ("200.00", "60.00")
    assert restored["lock_version"] > deleted["lock_version"]
    assert main_line(project, risk["provision_node_id"])["reestimated_amount"] == "60.00"


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_undoing_of_a_creation_in_the_own_estimate_advances_the_counter(
    risks: Risks, project: Costed, realm: TestRealm
) -> None:
    writer = signed_in(project.stage, realm)
    risk = risks.declared()
    path = risks.own(risk, project.revision_id)
    answer = risks.api.post(
        path,
        headers=writer.headers,
        json={"kind": "task", "parent_id": None, "task": {"label": "Grue"}},
    )
    assert answer.status_code == 201, answer.text
    created = risks.risk(risk)
    undone(project.tree, writer)
    assert risks.risk(risk)["lock_version"] > created["lock_version"]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_provision_line_is_never_projected_when_its_task_is_moved_in_the_main_structure(
    api: ContractClient, risks: Risks, project: Costed
) -> None:
    # « …une ligne de provision n'est jamais projetée » : sous une inflation de 3 %, la tâche
    # porteuse décalée de deux ans dans la structure principale redate la ligne, qui garde le
    # montant de `provision_amount` — la gravité pondérée —, seule son année de consommation suit.
    stage = project.stage
    path = f"{PROJECTS}/{project.project_id}"
    held = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    answer = api.patch(
        path,
        headers=stage.manager.headers,
        json={"inflation_rate": "0.03", "lock_version": held},
    )
    assert answer.status_code == 200, answer.text
    risk = risks.declared()
    risks.costed_at(risk, project.revision_id, "200.00")
    declared = risks.risk(risk)
    carrier = project.tree.node(str(declared["provision_task"]["node_id"]))
    year = utc_now().year + 2
    monday = next(
        day for day in (date(year, 11, each) for each in range(1, 8)) if day.weekday() == 0
    )
    moved = project.tree.change(
        carrier,
        scheduling_mode="manual",
        start={"date": monday.isoformat()},
        finish={"date": (monday + timedelta(days=1)).isoformat()},
    )
    assert moved.status_code == 200, moved.text
    line = main_line(project, risk["provision_node_id"])
    assert line["consumption_year"] == year
    assert (line["base_amount"], line["reestimated_amount"]) == ("60.00", "60.00")
    assert risks.risk(risk)["provision_amount"] == line["reestimated_amount"]


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_opening_of_a_revision_advances_the_counter_of_a_risk_whose_estimate_holds_a_node(
    risks: Risks, project: Costed
) -> None:
    # The copy redates the own estimates that hold a node, which advances their risk; one that is
    # empty is not redated, and its risk keeps its counter.
    held = risks.declared()
    empty = risks.declared()
    risks.costed_at(held, project.revision_id, "200.00")
    counters = (risks.risk(held)["lock_version"], risks.risk(empty)["lock_version"])
    mark(project.stage, {"revision_id": str(project.revision_id)})
    risks.revision()
    assert risks.risk(held)["lock_version"] > counters[0]
    assert risks.risk(empty)["lock_version"] == counters[1]


# --- The label, and the names it gives (#3980) ---------------------------------------------------


def own_label(risks: Risks, revision_id: object, risk: dict[str, Any]) -> str:
    """Read the label the list of the structures of a revision gives the own estimate of a risk."""
    path = f"{risks.base}/revisions/{revision_id}/structures"
    listed = risks.api.get(path, headers=risks.headers).json()
    return next(each["label"] for each in listed if each.get("risk_id") == risk["risk_id"])


def provision_label(risks: Risks, revision_id: object, risk: dict[str, Any]) -> str:
    """Read the label of the provision line of a risk in the main structure of a revision."""
    path = f"{risks.base}/revisions/{revision_id}/structures"
    main = next(
        each["structure_id"]
        for each in risks.api.get(path, headers=risks.headers).json()
        if each["kind"] == "main"
    )
    items = risks.api.get(f"{path}/{main}/nodes", headers=risks.headers).json()["items"]
    return next(
        each["estimate_line"]["label"]
        for each in items
        if each["node_id"] == risk["provision_node_id"] and each["estimate_line"]
    )


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_renamed_renames_its_own_estimate_and_its_provision_line_outside_the_history(
    risks: Risks, project: Costed, realm: TestRealm
) -> None:
    # #3980, option (a): the current revision follows the label, as the declaration named them
    # (« Provision — <libellé> »); the severity and the provision stay, and no entry of the history
    # is written, the identity being the project's (H-02).
    writer = signed_in(project.stage, realm)
    risk = risks.declared()
    risks.costed_at(risk, project.revision_id, "200.00")
    risk = risks.risk(risk)
    entries_before = len(entries(project.stage))
    counted = main_counter(project)
    answer = risks.update(risk, writer, label="Grue louée indisponible")
    assert answer.status_code == 200, answer.text
    assert answer.json()["lock_version"] == risk["lock_version"] + 1
    assert own_label(risks, project.revision_id, risk) == "Grue louée indisponible"
    assert (
        provision_label(risks, project.revision_id, risk) == "Provision — Grue louée indisponible"
    )
    assert main_counter(project) == counted + 1
    after = risks.risk(risk)
    assert (after["severity"], after["provision_amount"]) == (
        risk["severity"],
        risk["provision_amount"],
    )
    assert len(entries(project.stage)) == entries_before
    # A change that leaves the label alone renames nothing, and moves no counter of the main one.
    again = risks.update(after, writer, description="Grue louée.")
    assert again.status_code == 200, again.text
    assert main_counter(project) == counted + 1


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_renamed_leaves_the_marked_revisions_with_the_names_they_were_marked_with(
    risks: Risks, project: Costed
) -> None:
    # The revision marked is frozen (WF-DAT-0020): only the current one follows the label.
    risk = risks.declared()
    marked = project.revision_id
    mark(project.stage, {"revision_id": str(marked)})
    current = risks.revision()["revision_id"]
    renamed = risks.update(risk, label="Grue indisponible")
    assert renamed.status_code == 200, renamed.text
    assert own_label(risks, current, risk) == "Grue indisponible"
    assert provision_label(risks, current, risks.risk(risk)) == "Provision — Grue indisponible"
    assert own_label(risks, marked, risk) == LABEL
    assert provision_label(risks, marked, risk) == f"Provision — {LABEL}"


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_renamed_without_a_current_revision_writes_the_identity_alone(
    risks: Risks, project: Costed
) -> None:
    risk = risks.declared()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    before = revisions_of(project)
    answer = risks.update(risk, label="Grue indisponible")
    assert answer.status_code == 200, answer.text
    assert revisions_of(project) == before
    assert own_label(risks, project.revision_id, risk) == LABEL
