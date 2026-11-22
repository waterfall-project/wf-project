# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fabrics every lot of the back of EP-30 starts from (EP-30, "Les tests du back").

Added to those of EP-08 (``risks_support``): in the project costed at 1 000 (``costed``), a risk
whose own estimate is a differential of the main structure — whole, with its base, up to date — that
adds a line, modifies one and abandons a task (``risk_differential``); the same, out of date, the
main structure having received a task, a re-estimation and the deletion of the task whose line it
modifies (``out_of_date_risk``); and the same, pruned by the marking of its revision
(``pruned_risk``).

Until the stories that serve them, the own estimate is written around the service, by the owner of
the tables, as the rows the service will write: its structure and its base copies of the main
structure, its nodes under the lineages of the main structure's, its evaluation identified at 30 %
with its severity of 200 recorded, and its provision line of 60 in the main structure, under
``Réalisation``. The main structure is written through the service, and the marking by the
transaction of the worker. A lot that serves one may write it through the service here, leaving its
result unchanged.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from amendments_support import deleted, node_labelled
from estimate_support import Lines
from nodes_support import mark
from project_rows import AT, base_row, risk_row, structure_row
from risks_support import (
    MAKING,
    PROVISION,
    SEVERITY,
    STUDY,
    evaluation_row,
    material_line,
)
from sqlalchemy import delete, insert, select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.revisions.tables import CostStructure, OwnEstimateAbandonment
from waterfall.core.risks.tables import Risk, RiskEvaluation

if TYPE_CHECKING:
    from risks_support import Costed
    from sqlalchemy.engine import Connection

# What the own estimate designates: a line added under ``Étude``, the line of ``Étude`` modified,
# ``Réalisation`` abandoned with its line — 500 + 100 - 400, a severity of 200 (WF-RIS-0010).
ADDED = ("Renfort", Decimal("500.00"))
MODIFIED = ("Plans", Decimal("600.00"), Decimal("700.00"))
ABANDONED = MAKING
# What the main structure receives after, for the own estimate out of date: a task, a line
# re-estimated, and the deletion of the task whose line the own estimate modifies.
MAIN_ADDED = "Recette"
MAIN_REESTIMATED = ("Fabrication", "450.00")
MAIN_REMOVED = STUDY
# The label of the risk of the fabrics.
LABEL = "Sol instable"


@dataclass(frozen=True)
class RiskDifferential:
    """A risk of a project costed whose own estimate is a differential of the main structure.

    ``structure_id`` its own estimate, ``base_id`` its base, none once pruned; ``nodes`` the node of
    the own estimate of each task and line it holds, by label; ``provision_node_id`` its provision
    line in the main structure.
    """

    project: Costed
    risk_id: UUID
    structure_id: UUID
    base_id: UUID | None
    nodes: dict[str, UUID]
    provision_node_id: UUID


def _main_counter(connection: Connection, project: Costed) -> int:
    """Read the counter of the main structure of the current revision."""
    counter = connection.scalar(
        select(CostStructure.lock_version).where(CostStructure.id == project.structure_id)
    )
    assert counter is not None
    return counter


def _copied(connection: Connection, project: Costed, target: UUID) -> dict[str, UUID]:
    """Copy the tasks and lines of the main structure into a structure, under their lineages.

    Give the node of each copy by its label; the project costed holds no link.
    """
    nodes = connection.execute(
        select(Node.__table__).where(Node.structure_id == project.structure_id)
    ).mappings()
    held = [dict(each) for each in nodes]
    copies = {each["id"]: uuid4() for each in held}
    # The tasks before their lines, which name them.
    for each in sorted(held, key=lambda node: node["parent_id"] is not None):
        parent = each["parent_id"]
        each.update(
            id=copies[each["id"]],
            structure_id=target,
            parent_id=None if parent is None else copies[parent],
        )
        connection.execute(insert(Node).values(**each))
    labels: dict[str, UUID] = {}
    for facet, of_node in ((Task, Task.node_id), (EstimateLine, EstimateLine.node_id)):
        rows = connection.execute(select(facet.__table__).where(of_node.in_(list(copies))))
        for row in rows.mappings():
            copy = {**row, "node_id": copies[row["node_id"]]}
            if "structure_id" in copy:
                copy["structure_id"] = target
            connection.execute(insert(facet).values(**copy))
            labels[str(row["label"])] = copy["node_id"]
    return labels


def _designate(connection: Connection, project: Costed, nodes: dict[str, UUID]) -> None:
    """Make the own estimate designate what the fabric says: a line added, one modified, a task.

    The line added takes its node into ``nodes``; the task abandoned and its line leave it.
    """
    own = connection.scalar(select(Node.structure_id).where(Node.id == nodes[STUDY]))
    assert own is not None
    added = material_line(
        connection,
        (project.project_id, project.revision_id, own, nodes[STUDY]),
        project.costs.material,
        ADDED[1],
    )
    connection.execute(
        update(EstimateLine).where(EstimateLine.node_id == added).values(label=ADDED[0])
    )
    nodes[ADDED[0]] = added
    amount = MODIFIED[2]
    connection.execute(
        update(EstimateLine)
        .where(EstimateLine.node_id == nodes[MODIFIED[0]])
        .values(unit_disbursement=amount, base_amount=amount, reestimated_amount=amount)
    )
    gone = [nodes.pop(ABANDONED), nodes.pop(MAIN_REESTIMATED[0])]
    connection.execute(delete(EstimateLine).where(EstimateLine.node_id.in_(gone)))
    connection.execute(delete(Task).where(Task.node_id.in_(gone)))
    # The line before its task, which it names.
    for each in reversed(gone):
        connection.execute(delete(Node).where(Node.id == each))


def risk_differential(project: Costed, label: str = LABEL) -> RiskDifferential:
    """Declare a risk whose own estimate designates, up to date, in a project costed.

    Its structure and its base copies of the main structure, the counter of the main structure
    retained; the own estimate adds ``ADDED``, modifies ``MODIFIED`` and abandons ``ABANDONED``;
    its evaluation identified at 30 %, its severity of 200 recorded, its provision of 60 under
    ``Réalisation``.
    """
    project_id, revision_id = project.project_id, project.revision_id
    risk = risk_row(project_id, label=label)
    risk_id = risk["id"]
    assert isinstance(risk_id, UUID)
    with project.stage.owner.begin() as connection:
        connection.execute(insert(Risk).values(**risk))
        counter = _main_counter(connection, project)
        own = structure_row(
            project_id,
            revision_id,
            kind="risk",
            risk_id=risk_id,
            label=label,
            main_lock_version=counter,
        )
        structure_id = own["id"]
        assert isinstance(structure_id, UUID)
        base = base_row(project_id, revision_id, structure_id)
        base_id = base["id"]
        assert isinstance(base_id, UUID)
        connection.execute(insert(CostStructure).values(**own))
        connection.execute(insert(CostStructure).values(**base))
        _copied(connection, project, base_id)
        nodes = _copied(connection, project, structure_id)
        _designate(connection, project, nodes)
        provision = material_line(
            connection,
            (project_id, revision_id, project.structure_id, project.tasks[MAKING]),
            project.costs.provision,
            PROVISION,
        )
        evaluation = evaluation_row(
            project_id,
            risk_id,
            (revision_id, structure_id),
            project.costs.provision,
            state="identified",
            provision_node_id=provision,
            severity=SEVERITY,
        )
        connection.execute(insert(RiskEvaluation).values(**evaluation))
    return RiskDifferential(project, risk_id, structure_id, base_id, nodes, provision)


def out_of_date_risk(project: Costed, label: str = LABEL) -> RiskDifferential:
    """Give the risk of ``risk_differential``, its own estimate out of date.

    The main structure receives, through the service, ``MAIN_ADDED``, ``MAIN_REESTIMATED`` and the
    deletion of ``MAIN_REMOVED``, whose line the own estimate modifies.
    """
    risk = risk_differential(project, label)
    tree = project.tree
    tree.made(MAIN_ADDED)
    Lines(tree).changed(
        node_labelled(tree, MAIN_REESTIMATED[0]), unit_disbursement=MAIN_REESTIMATED[1]
    )
    deleted(tree, MAIN_REMOVED, project.stage.manager)
    return risk


def pruned_risk(project: Costed, label: str = LABEL) -> RiskDifferential:
    """Give the risk of ``risk_differential``, pruned, its revision marked by the worker.

    Its structure keeps what it designates and the ancestors of it — ``Étude`` unchanged, ``Plans``
    modified, ``Renfort`` added —, abandons ``Réalisation`` (``own_estimate_abandonment``), has no
    base any more and names its revision, which the marking then marks ``v1.0``.
    """
    risk = risk_differential(project, label)
    with project.stage.owner.begin() as connection:
        abandoned = connection.scalar(
            select(Node.lineage_id).where(Node.id == project.tasks[ABANDONED])
        )
        connection.execute(
            insert(OwnEstimateAbandonment).values(
                project_id=project.project_id,
                id=uuid4(),
                revision_id=project.revision_id,
                structure_id=risk.structure_id,
                node_lineage_id=abandoned,
                created_at=AT,
            )
        )
        _pruned_base(connection, risk)
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == risk.structure_id)
            .values(pruned_revision_id=project.revision_id)
        )
    mark(project.stage, {"revision_id": str(project.revision_id)})
    return RiskDifferential(
        project, risk.risk_id, risk.structure_id, None, risk.nodes, risk.provision_node_id
    )


def _pruned_base(connection: Connection, risk: RiskDifferential) -> None:
    """Delete the base of an own estimate, its nodes first, as the pruning does."""
    assert risk.base_id is not None
    nodes = select(Node.id).where(Node.structure_id == risk.base_id)
    connection.execute(delete(EstimateLine).where(EstimateLine.node_id.in_(nodes)))
    connection.execute(delete(Task).where(Task.node_id.in_(nodes)))
    connection.execute(
        delete(Node).where(Node.structure_id == risk.base_id, Node.parent_id.is_not(None))
    )
    connection.execute(delete(Node).where(Node.structure_id == risk.base_id))
    connection.execute(delete(CostStructure).where(CostStructure.id == risk.base_id))


def held_lines(project: Costed, structure_id: UUID) -> dict[str, Decimal]:
    """Read the lines a structure holds, around the service: their re-estimated amount by label."""
    with project.stage.owner.connect() as connection:
        rows = connection.execute(
            select(EstimateLine.label, EstimateLine.reestimated_amount)
            .join(Node, Node.id == EstimateLine.node_id)
            .where(Node.structure_id == structure_id)
        ).all()
    return {str(label): amount for label, amount in rows}


def held_tasks(project: Costed, structure_id: UUID) -> set[str]:
    """Read the tasks a structure holds, around the service, by label."""
    with project.stage.owner.connect() as connection:
        return set(
            connection.scalars(
                select(Task.label)
                .join(Node, Node.id == Task.node_id)
                .where(Node.structure_id == structure_id)
            )
        )
