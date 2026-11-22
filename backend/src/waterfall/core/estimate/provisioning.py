# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision line of a risk, written at the request of the risks alone (EP-08, "Modules").

A line of the main structure, of the category of provision the risk designates and of the
subproject it designates, if one, whose figures are its provision: one unit at that amount, which
is its base amount and its re-estimated amount, never projected, without a payment delay
(WF-RIS-0010, WF-DEV-0020, WF-DEV-0030; #733). Its year of consumption is the year of the heaviest
share of its task, as for any line; its budgeted amount is nought on a project that has a reference
— the risk declared since bears none in it —, null otherwise, read as the re-estimated one
(WF-DEV-0020). Its label names its risk.

The risks ask for it at the declaration (``ProvisionEntry``, by ``create_borne_line`` of the
planning, whose facet hook ``create_line`` addresses here), and write its amount again each time
the severity or the probability changes (``set_provision``), under the lock of the main structure,
whose counter advances. They write its label again when their risk is renamed
(``rename_provision``, #3980), and name the lines of a revision opened (``rename_provisions``).
When the risk designates another category or subproject for it (``updateRiskProvision``), they write
them on the line (``set_provision_bearing``): the subproject of a line of a started task that has
received actual costs included, which a line entered by the grid may not take (WF-PRJ-0050).

Each write of a provision line advances the counter of the main structure as a provision line's
(``provision_written``): the own estimates up to date stay so (EP-30).

Filled by US-2570/L1; completed by US-2580/L1.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import case, select, update

from waterfall.core.estimate.costing import basis_of, priced
from waterfall.core.estimate.pricing import CENT
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.revisions.interface import (
    provision_written,
    structure_counted,
    structure_facts,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import FacetCreation, Place
    from waterfall.platform.audit import Act

# The label of a provision line, before the label of its risk.
PROVISION_LABEL = "Provision — {label}"
ONE = Decimal(1)
NOUGHT = CENT * 0


@dataclass(frozen=True, slots=True)
class ProvisionEntry:
    """The provision line of a risk, as the risks ask for it: its risk's label, what bears it.

    ``amount`` the provision, the severity weighted by the probability, to the cent.
    """

    risk_label: str
    cost_category_id: UUID
    subproject_id: UUID | None
    amount: Decimal


def create_provision(creation: FacetCreation, entry: ProvisionEntry) -> None:
    """Write the facet of a provision line created under its task (``create_borne_line``)."""
    session, project_id, act = creation.session, creation.project_id, creation.act
    basis = basis_of(session, project_id, creation.revision_id)
    year = priced(entry.amount, creation.bearer, basis, None).consumption_year
    session.add(
        EstimateLine(
            project_id=project_id,
            node_id=creation.node_id,
            kind="estimate_line",
            label=PROVISION_LABEL.format(label=entry.risk_label),
            cost_category_id=entry.cost_category_id,
            resource_role_id=None,
            quantity=ONE,
            hours=None,
            unit_disbursement=entry.amount,
            payment_delay_days=0,
            subproject_id=entry.subproject_id,
            base_amount=entry.amount,
            budgeted_amount=NOUGHT if basis.has_reference else None,
            reestimated_amount=entry.amount,
            consumption_year=year,
            lock_version=1,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    session.flush()


def rename_provision(
    session: Session, place: Place, node_id: UUID, risk_label: str, act: Act
) -> None:
    """Write the label of a provision line again from its risk's, under the lock of its structure.

    ``place`` is the main structure that bears the line. A line already so named is left as it is;
    one that is renamed advances the counter of the structure, and not its own, as its amount
    does (``set_provision``): the risks rename it, never the grid (#3980).
    """
    structure_facts(session, place.project_id, place.structure_id, lock=True)
    line = session.scalars(
        select(EstimateLine)
        .where(EstimateLine.project_id == place.project_id, EstimateLine.node_id == node_id)
        .execution_options(populate_existing=True)
    ).one()
    label = PROVISION_LABEL.format(label=risk_label)
    if line.label == label:
        return
    line.label = label
    line.updated_at, line.updated_by = act.at, act.author
    session.flush()
    with provision_written(session):
        structure_counted(session, place.project_id, place.structure_id)


def rename_provisions(session: Session, project_id: UUID, risk_labels: dict[UUID, str]) -> None:
    """Name the provision lines of a revision opened by their risks' labels, in one statement.

    ``risk_labels`` maps the node of each line to the label of its risk: the copy of a revision
    names them from the risk, not from the lines it copies (#3980). The lines are new, at their
    first version: no counter advances.
    """
    if not risk_labels:
        return
    names = {node: PROVISION_LABEL.format(label=label) for node, label in risk_labels.items()}
    session.execute(
        update(EstimateLine)
        .where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(names))
        .values(label=case(names, value=EstimateLine.node_id))
        .execution_options(synchronize_session=False)
    )


def provision_amount(session: Session, project_id: UUID, node_id: UUID) -> Decimal:
    """Read the amount of a provision line: its re-estimated amount, which is its provision."""
    return session.scalars(
        select(EstimateLine.reestimated_amount).where(
            EstimateLine.project_id == project_id, EstimateLine.node_id == node_id
        )
    ).one()


def set_provision(session: Session, place: Place, node_id: UUID, amount: Decimal) -> bool:
    """Write the amount of a provision line again, under the lock of its structure; tell if moved.

    ``place`` is the main structure that bears the line. A line already at the amount is left as
    it is; one that moves advances the counter of the structure, whose total it changes, and not
    its own: a figure computed, not entered (``LockVersion``), whose audit is left to the entries.
    """
    structure_facts(session, place.project_id, place.structure_id, lock=True)
    line = session.scalars(
        select(EstimateLine)
        .where(EstimateLine.project_id == place.project_id, EstimateLine.node_id == node_id)
        .execution_options(populate_existing=True)
    ).one()
    if (line.unit_disbursement, line.base_amount, line.reestimated_amount) == (amount,) * 3:
        return False
    line.quantity = ONE
    line.unit_disbursement = amount
    line.base_amount = amount
    line.reestimated_amount = amount
    session.flush()
    with provision_written(session):
        structure_counted(session, place.project_id, place.structure_id)
    return True


def set_provision_bearing(
    session: Session, place: Place, node_id: UUID, bearing: tuple[UUID, UUID | None]
) -> bool:
    """Write the category and the subproject of a provision line, its amount as it is; tell if so.

    ``bearing`` the category of provision the risk designates and its subproject, none to take the
    provision out of its subproject. The line is the risk's alone: no rule of the grid judges the
    change, neither the actual costs of its subproject nor the state of its task (WF-PRJ-0050).
    Under the lock of the main structure, whose counter advances, the line's own staying: a figure
    the risk writes (``LockVersion``).
    """
    structure_facts(session, place.project_id, place.structure_id, lock=True)
    line = session.scalars(
        select(EstimateLine)
        .where(EstimateLine.project_id == place.project_id, EstimateLine.node_id == node_id)
        .execution_options(populate_existing=True)
    ).one()
    category, subproject = bearing
    if (line.cost_category_id, line.subproject_id) == (category, subproject):
        return False
    line.cost_category_id, line.subproject_id = category, subproject
    session.flush()
    with provision_written(session):
        structure_counted(session, place.project_id, place.structure_id)
    return True
