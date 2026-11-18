# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk declared, read and renamed (WF-RIS-0010, WF-RIS-0020).

``createRisk``, ``getRisk`` and ``updateRisk`` (US-2570/L1), under ``risks.read`` and
``risks.write``: a risk is read by whoever consults its project, declared and renamed by its
contributors. The declaration is an entry of the current revision, which it creates when the
project has none; the change of the identity is a datum of the project, which writes no revision
(H-02, #1783). The response names the computed fields of the risk and what each depends on, by its
state (``computed_fields``, WF-IHM-0030).

Registered by the application from US-2550/L1; served by US-2570/L1.
"""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import Risk, RiskUpdate, RiskWrite
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.nodes import Writing
from waterfall.api.projects import viewer_of
from waterfall.api.wire import text_of
from waterfall.core.planning.interface import Writer
from waterfall.core.risks.interface import (
    OMITTED,
    RiskEntry,
    RiskIdentityChange,
    RiskView,
    create_risk,
    read_risk,
    update_risk,
)
from waterfall.core.users.interface import read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["risks"])

CONSULT = "risks.read"
CHANGE = "risks.write"
# What the computed fields of a risk depend on, by field (``RiskComputedField``): the provision of
# an identified risk on its severity and its probability, that of another on the reference.
SEVERITY = {"field": "severity", "dependencies": ["own_estimate"]}
PROVISION_IDENTIFIED = {"field": "provision_amount", "dependencies": ["severity_and_probability"]}
PROVISION_REFERENCE = {"field": "provision_amount", "dependencies": ["reference_provision"]}
OCCURRENCE_COST = {"field": "occurrence_cost", "dependencies": ["occurrence_estimate"]}


def _money(value: Decimal) -> str:
    """Give an amount as the contract writes it: to the cent."""
    return f"{value:.2f}"


def _computed(view: RiskView) -> list[dict[str, str | list[str]]]:
    """Name the computed fields of a risk, by its state, in the order of the contract."""
    if view.state == "identified":
        return [SEVERITY, PROVISION_IDENTIFIED]
    if view.state == "occurred":
        return [SEVERITY, PROVISION_REFERENCE, OCCURRENCE_COST]
    return [SEVERITY, PROVISION_REFERENCE]


def described(session: Session, view: RiskView) -> Risk:
    """Describe a risk as the contract does, its authors named as they are today."""
    authors = read_authors(
        session, {each for each in (view.created_by, view.updated_by) if each is not None}
    )
    task = view.provision_task
    cell = view.matrix_cell
    return Risk.model_validate(
        {
            "risk_id": view.risk_id,
            "label": view.label,
            "description": view.description,
            "mitigation_notes": view.mitigation_notes,
            "probability": text_of(view.probability),
            "severity": _money(view.severity),
            "provision_amount": _money(view.provision_amount),
            "occurrence_cost": (
                None if view.occurrence_cost is None else _money(view.occurrence_cost)
            ),
            "occurred_reestimated_amount": (
                None
                if view.occurred_reestimated_amount is None
                else _money(view.occurred_reestimated_amount)
            ),
            "state": view.state,
            "structure_id": view.structure_id,
            "provision_node_id": view.provision_node_id,
            "provision_cost_category_id": view.provision_cost_category_id,
            "provision_cost_category_label": view.provision_cost_category_label,
            "provision_cost_category_is_active": view.provision_cost_category_is_active,
            "provision_subproject_id": view.provision_subproject_id,
            "provision_subproject_label": view.provision_subproject_label,
            "provision_task": (
                None if task is None else {"node_id": task.node_id, "label": task.label}
            ),
            "matrix_cell": {
                "probability_level": cell.probability_level,
                "severity_level": cell.severity_level,
                "zone": cell.zone,
            },
            "last_review_on": view.last_review_on,
            "computed_fields": _computed(view),
            "available_commands": [
                {
                    "command": command.command,
                    "is_available": command.is_available,
                    "missing_conditions": list(command.missing_conditions),
                }
                for command in view.commands
            ],
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(
                    None if view.created_by is None else authors.get(view.created_by)
                ),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(
                    None if view.updated_by is None else authors.get(view.updated_by)
                ),
            },
            "lock_version": view.lock_version,
        }
    )


def id_of(value: object) -> UUID | None:
    """Give the identifier a body carries, none when it carries none."""
    root = getattr(value, "root", None)
    return root if isinstance(root, UUID) else None


@router.post(
    "/projects/{project_id}/risks",
    operation_id="createRisk",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    status_code=201,
    response_model=Risk,
    response_model_exclude_unset=True,
)
def post_risk(
    project_id: UUID, body: RiskWrite, actor: Acting, writer: Writing, session: Transaction
) -> Risk:
    """Declare a risk in the current revision of a project, created if it has none."""
    entry = RiskEntry(
        label=body.label,
        probability=Decimal(body.probability.root.root),
        description=body.description,
        mitigation_notes=body.mitigation_notes,
        provision_cost_category_id=id_of(body.provision_cost_category_id),
        provision_subproject_id=id_of(body.provision_subproject_id),
        provision_task_id=id_of(body.provision_task_id),
    )
    view = create_risk(session, project_id, entry, writer, viewer_of(actor))
    return described(session, view)


@router.get(
    "/projects/{project_id}/risks/{risk_id}",
    operation_id="getRisk",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=Risk,
    response_model_exclude_unset=True,
)
def get_risk(
    project_id: UUID,
    risk_id: UUID,
    actor: Acting,
    session: Transaction,
    revision_id: Annotated[UUID | None, Query()] = None,
) -> Risk:
    """Read a risk in a revision: the one named, else the current, else the last marked."""
    view = read_risk(session, project_id, risk_id, revision_id, viewer_of(actor))
    return described(session, view)


@router.patch(
    "/projects/{project_id}/risks/{risk_id}",
    operation_id="updateRisk",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=Risk,
    response_model_exclude_unset=True,
)
def patch_risk(
    project_id: UUID, risk_id: UUID, body: RiskUpdate, actor: Acting, session: Transaction
) -> Risk:
    """Write the identity of a risk at the counter read, a datum of the project (H-02).

    Outside the history (#1783): the writer has no stack. A description or notes not sent stay.
    """
    sent = body.model_fields_set
    change = RiskIdentityChange(
        risk_id,
        body.label,
        body.lock_version.root,
        description=body.description if "description" in sent else OMITTED,
        mitigation_notes=body.mitigation_notes if "mitigation_notes" in sent else OMITTED,
    )
    writer = Writer(Act(actor.user_id, utc_now()), None)
    view = update_risk(session, project_id, change, writer, viewer_of(actor))
    return described(session, view)
