# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the amendments and the risks share (EP-08, "Les tests du back").

The rows of the risks written around the service — the evaluation of a risk in a revision, a
review, a share of the reserve, the risk itself being ``project_rows``' (``risk_row``), which the
nodes name —, each valid unless a test changes it; and the three fabrics every lot of the back
starts from, so that none builds its own (US-2550/L1): a project costed at 1 000 through the
service (``costed``), a risk of severity 200 at 30 % declared in it (``declared``), and a
differential of its current revision (``differential``).
Until the stories that serve them, the risk and the differential are written around the service,
by the owner of the tables, as the rows the service will write: the risk with its own estimate, a
task bearing a line of 200, its evaluation identified, and its provision line of 60 in the main
structure, under the first task of the first level, of the category of provision the installation
is delivered with (WF-RIS-0010). A lot that serves one may write it through the service here,
leaving its result unchanged. A helper several test modules read lives here, never in one of them.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from estimate_support import YEAR, Costing, Lines
from nodes_support import Tree, opened
from planning_support import insert_task, node_row
from project_rows import AT, STAMP, risk_row, structure_row
from projects_support import PROJECTS
from sqlalchemy import func, insert, select

from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.risks.tables import Risk, RiskEvaluation

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from sqlalchemy.engine import Connection
    from support import ContractClient

# The figures of the fabrics: the estimate of the project, the severity of the risk, its
# probability, and the provision they give (WF-RIS-0010).
ESTIMATE = Decimal("1000.00")
SEVERITY = Decimal("200.00")
PROBABILITY = Decimal("0.30")
PROVISION = Decimal("60.00")
# The two tasks of the project costed, each with its line of material and its amount.
STUDY, MAKING = "Étude", "Réalisation"
COSTED = ((STUDY, "Plans", "600.00"), (MAKING, "Fabrication", "400.00"))


# --- The rows, around the service ----------------------------------------------------------------


def evaluation_row(
    project_id: UUID,
    risk_id: UUID,
    structure: tuple[UUID, UUID],
    category_id: UUID,
    **overrides: object,
) -> dict[str, object]:
    """Give the columns of the evaluation of a risk, dismissed: neither provision line nor cost.

    ``structure`` is the revision and the own structure of the risk in it.
    """
    revision_id, structure_id = structure
    return {
        "project_id": project_id,
        "risk_id": risk_id,
        "revision_id": revision_id,
        "probability": PROBABILITY,
        "state": "dismissed",
        "structure_id": structure_id,
        "provision_node_id": None,
        "provision_cost_category_id": category_id,
        "provision_subproject_id": None,
        "provision_task_lineage_id": None,
        "occurrence_cost": None,
        **STAMP,
        **overrides,
    }


def review_row(
    project_id: UUID, risk_id: UUID, revision_id: UUID, **overrides: object
) -> dict[str, object]:
    """Give the columns of a review of a risk, which kept it identified at 30 % of 200."""
    return {
        "project_id": project_id,
        "id": uuid4(),
        "risk_id": risk_id,
        "revision_id": revision_id,
        "reviewed_on": AT.date(),
        "probability": PROBABILITY,
        "severity": SEVERITY,
        "state": "identified",
        "created_at": AT,
        **overrides,
    }


def share_row(
    project_id: UUID, risk_id: UUID, revision_id: UUID, **overrides: object
) -> dict[str, object]:
    """Give the columns of the share of a risk in a reference: its provision of 60."""
    return {
        "project_id": project_id,
        "revision_id": revision_id,
        "risk_id": risk_id,
        "provision_amount": PROVISION,
        "created_at": AT,
        **overrides,
    }


def material_line(
    connection: Connection,
    bearer: tuple[UUID, UUID, UUID, UUID],
    category_id: UUID,
    amount: Decimal,
) -> UUID:
    """Write a line of one unit at ``amount`` under a task, last of its lines; give its node.

    ``bearer`` is the project, the revision, the structure and the task of the line.
    """
    project_id, revision_id, structure_id, task_id = bearer
    last = connection.scalar(
        select(func.max(Node.rank)).where(
            Node.project_id == project_id, Node.parent_id == task_id, Node.kind == "estimate_line"
        )
    )
    node = node_row(
        project_id,
        revision_id,
        structure_id,
        kind="estimate_line",
        parent_id=task_id,
        rank=(last or 0) + 1,
    )
    node_id = node["id"]
    assert isinstance(node_id, UUID)
    connection.execute(insert(Node).values(**node))
    connection.execute(
        insert(EstimateLine).values(
            project_id=project_id,
            node_id=node_id,
            kind="estimate_line",
            label="Ligne",
            cost_category_id=category_id,
            resource_role_id=None,
            quantity=Decimal(1),
            hours=None,
            unit_disbursement=amount,
            payment_delay_days=0,
            subproject_id=None,
            base_amount=amount,
            budgeted_amount=None,
            reestimated_amount=amount,
            consumption_year=YEAR,
            **STAMP,
        )
    )
    return node_id


def provision_category(connection: Connection) -> UUID:
    """Give the category of provision the installation is delivered with (WF-RIS-0010)."""
    found = connection.scalars(
        select(CostCategory.id)
        .join(CostType, CostType.id == CostCategory.cost_type_id)
        .where(CostType.kind == "provision")
    ).first()
    assert found is not None
    return found


# --- The fabrics ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Costed:
    """A project costed at 1 000 in its current revision, written through the service.

    ``tasks`` the node of each task of its main structure, by label: ``Étude`` bearing a line of
    600, ``Réalisation`` a line of 400, both of material.
    """

    stage: Scene
    costs: Costing
    tree: Tree
    lines: Lines
    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    tasks: dict[str, UUID]


def material(costs: Costing, label: str, amount: str) -> dict[str, Any]:
    """Give a line of material, one unit at the amount said, as the service receives it."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def costed(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Open the current revision of the project of a stage and cost it at 1 000, as its manager."""
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    lines = Lines(tree)
    tasks: dict[str, UUID] = {}
    for task, label, amount in COSTED:
        made = tree.made(task)
        lines.made(made, **material(costs, label, amount))
        tasks[task] = UUID(made["node_id"])
    total = sum(
        (
            Decimal(each["estimate_line"]["reestimated_amount"])
            for each in tree.items()
            if each["kind"] == "estimate_line"
        ),
        Decimal(0),
    )
    assert total == ESTIMATE
    return Costed(
        stage,
        costs,
        tree,
        lines,
        UUID(stage.project["project_id"]),
        UUID(revision["revision_id"]),
        UUID(tree.structure_id),
        tasks,
    )


@dataclass(frozen=True)
class Declared:
    """A risk declared in the current revision of a project costed, as the service will write it.

    Its own structure and the task of it that bears the line of its severity; its provision line in
    the main structure, under ``Étude``.
    """

    risk_id: UUID
    structure_id: UUID
    task_id: UUID
    provision_node_id: UUID


def declared(costed: Costed, label: str = "Retard du fournisseur") -> Declared:
    """Declare a risk of severity 200 at 30 % in a project costed, around the service.

    Its provision of 60 under ``Étude``, of the category of provision; identified.
    """
    project_id, revision_id = costed.project_id, costed.revision_id
    risk = risk_row(project_id, label=label)
    risk_id = risk["id"]
    assert isinstance(risk_id, UUID)
    own = structure_row(project_id, revision_id, kind="risk", risk_id=risk_id, label=label)
    structure_id = own["id"]
    assert isinstance(structure_id, UUID)
    with costed.stage.owner.begin() as connection:
        connection.execute(insert(Risk).values(**risk))
        connection.execute(insert(CostStructure).values(**own))
        task_id = insert_task(connection, project_id, revision_id, structure_id, label=label)
        material_line(
            connection,
            (project_id, revision_id, structure_id, task_id),
            costed.costs.material,
            SEVERITY,
        )
        provision = material_line(
            connection,
            (project_id, revision_id, costed.structure_id, costed.tasks[STUDY]),
            costed.costs.provision,
            PROVISION,
        )
        connection.execute(
            insert(RiskEvaluation).values(
                **evaluation_row(
                    project_id,
                    risk_id,
                    (revision_id, structure_id),
                    costed.costs.provision,
                    state="identified",
                    provision_node_id=provision,
                )
            )
        )
    return Declared(risk_id, structure_id, task_id, provision)


def differential(costed: Costed, label: str = "Avenant 1") -> UUID:
    """Open an empty differential in the current revision of a project costed, around the service.

    A structure of the kind ``amendment``; a test writes its nodes. Its copy of the main structure
    is US-2550/L3's.
    """
    row = structure_row(costed.project_id, costed.revision_id, kind="amendment", label=label)
    structure_id = row["id"]
    assert isinstance(structure_id, UUID)
    with costed.stage.owner.begin() as connection:
        connection.execute(insert(CostStructure).values(**row))
    return structure_id


# --- The risks, through the service --------------------------------------------------------------

# The label of the risk declared by default.
LABEL = "Retard du fournisseur"


class Risks:
    """The risks of a project costed, declared, read, written through the service."""

    def __init__(self, api: ContractClient, project: Costed) -> None:
        self.api = api
        self.project = project
        self.stage = project.stage
        self.base = f"{PROJECTS}/{project.project_id}"
        self.headers = self.stage.manager.headers

    def declared(self, probability: str = "0.3", label: str = LABEL) -> dict[str, Any]:
        """Declare a risk in the current revision; give it."""
        sent = {"label": label, "probability": probability}
        answer = self.api.post(f"{self.base}/risks", headers=self.headers, json=sent)
        assert answer.status_code == 201, answer.text
        return answer.json()

    def read(self, risk: dict[str, Any], revision_id: object = None) -> Any:
        """Read a risk, in the revision named, the current or the last marked otherwise."""
        query = "" if revision_id is None else f"?revision_id={revision_id}"
        return self.api.get(f"{self.base}/risks/{risk['risk_id']}{query}", headers=self.headers)

    def risk(self, risk: dict[str, Any], revision_id: object = None) -> dict[str, Any]:
        """Read a risk that must be read; give it."""
        answer = self.read(risk, revision_id)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def update(self, risk: dict[str, Any], who: Person | None = None, **body: Any) -> Any:
        """Change the identity of a risk at the counter read, as the manager by default."""
        sent = {"label": risk["label"], "lock_version": risk["lock_version"], **body}
        path = f"{self.base}/risks/{risk['risk_id']}"
        headers = self.headers if who is None else who.headers
        return self.api.patch(path, headers=headers, json=sent)

    def own(self, risk: dict[str, Any], revision_id: object) -> str:
        """Give the path of the nodes of the own estimate a risk holds in a revision."""
        held = self.risk(risk, revision_id)["structure_id"]
        return f"{self.base}/revisions/{revision_id}/structures/{held}/nodes"

    def made(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Create a node in a structure, as the manager does; give the node created."""
        answer = self.api.post(path, headers=self.headers, json=body)
        assert answer.status_code == 201, answer.text
        return answer.json()["nodes"][0]

    def costed_at(self, risk: dict[str, Any], revision_id: object, amount: str) -> dict[str, Any]:
        """Write a task bearing a line of material at an amount in an own estimate; give it."""
        path = self.own(risk, revision_id)
        task = self.made(path, {"kind": "task", "parent_id": None, "task": {"label": "Grue"}})
        line = material(self.project.costs, "Location", amount)
        sent = {"kind": "estimate_line", "parent_id": task["node_id"], "estimate_line": line}
        return self.made(path, sent)

    def repriced(
        self, risk: dict[str, Any], revision_id: object, line: dict[str, Any], amount: str
    ) -> dict[str, Any]:
        """Change the amount of a line of the own estimate; give the line written."""
        path = f"{self.own(risk, revision_id)}/{line['node_id']}/estimate-line"
        sent = {"lock_version": line["lock_version"], "unit_disbursement": amount}
        answer = self.api.patch(path, headers=self.headers, json=sent)
        assert answer.status_code == 200, answer.text
        return answer.json()["nodes"][0]

    def revision(self) -> dict[str, Any]:
        """Open the current revision of the project; give it."""
        answer = self.api.post(f"{self.base}/revisions", headers=self.headers, json={})
        assert answer.status_code == 201, answer.text
        return answer.json()

    def abandon(self, revision: dict[str, Any]) -> None:
        """Abandon a current revision at the counter read."""
        path = f"{self.base}/revisions/{revision['revision_id']}"
        query = f"?lock_version={revision['lock_version']}"
        answer = self.api.delete(f"{path}{query}", headers=self.headers)
        assert answer.status_code == 204, answer.text
