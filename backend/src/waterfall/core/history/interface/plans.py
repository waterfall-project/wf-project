# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The plans of a paste: kept by ``previewPaste``, read and dropped by ``applyPaste``.

A plan keeps the block judged, the target and the counter of the structure, for an hour (EP-06,
"L'historique annulable et le collage"); the planning judges and applies it, the history keeps it
without reading any table of the planning.

Declared by US-1380/L1; filled by US-1450/L1.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import delete, select

from waterfall.core.history.tables import PastePlan
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.history.snapshots import JsonValue

# How long a plan is kept between its preview and its application.
PLAN_LIFETIME = timedelta(hours=1)

# The columns a paste targets, as the contract says them (``NodeColumn``).
type NodeColumn = Literal[
    "label",
    "description",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "physical_progress",
    "total_float",
    "is_critical",
    "started_on",
    "completed_on",
    "predecessors",
    "work_breakdown",
    "cost_category",
    "resource_role",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject",
    "payment_delay_days",
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
]


@dataclass(frozen=True, slots=True)
class PlanToKeep:
    """The plan of a paste as its preview judged it: where it goes, what it writes, on what counter.

    ``rows`` are the lines judged, in JSON, which only the planning reads;
    ``structure_lock_version`` the counter of the structure read at the preview.
    """

    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    user_account_id: UUID
    target_node_id: UUID
    target_column: NodeColumn
    rows: JsonValue
    structure_lock_version: int


@dataclass(frozen=True, slots=True)
class KeptPlan:
    """A plan kept, by its identifier, until ``expires_at``."""

    plan_id: UUID
    plan: PlanToKeep
    created_at: datetime
    expires_at: datetime


def keep_plan(session: Session, plan: PlanToKeep, at: datetime) -> KeptPlan:
    """Keep the plan of a paste of an account, for an hour from ``at``, and give its identifier."""
    kept = KeptPlan(new_id(), plan, at, at + PLAN_LIFETIME)
    session.add(
        PastePlan(
            id=kept.plan_id,
            project_id=plan.project_id,
            revision_id=plan.revision_id,
            structure_id=plan.structure_id,
            user_account_id=plan.user_account_id,
            target_node_id=plan.target_node_id,
            target_column=plan.target_column,
            rows=plan.rows,
            structure_lock_version=plan.structure_lock_version,
            created_at=kept.created_at,
            expires_at=kept.expires_at,
        )
    )
    session.flush()
    return kept


def read_plan(
    session: Session, plan_id: UUID, structure_id: UUID, user_account_id: UUID, at: datetime
) -> KeptPlan | None:
    """Read and lock the plan its account kept on a structure, or ``None`` past its hour.

    ``None`` too for a plan unknown, dropped, of another structure or of another account. The plan
    is locked until the end of the transaction: two applications of one plan come one after the
    other, and the second finds it dropped.
    """
    row = session.scalars(
        select(PastePlan)
        .where(
            PastePlan.id == plan_id,
            PastePlan.structure_id == structure_id,
            PastePlan.user_account_id == user_account_id,
        )
        .with_for_update()
    ).first()
    if row is None or row.expires_at <= at:
        return None
    plan = PlanToKeep(
        project_id=row.project_id,
        revision_id=row.revision_id,
        structure_id=row.structure_id,
        user_account_id=row.user_account_id,
        target_node_id=row.target_node_id,
        target_column=cast("NodeColumn", row.target_column),
        rows=cast("JsonValue", row.rows),
        structure_lock_version=row.structure_lock_version,
    )
    return KeptPlan(row.id, plan, row.created_at, row.expires_at)


def drop_plan(session: Session, plan_id: UUID) -> None:
    """Drop the plan of a paste once applied."""
    session.execute(delete(PastePlan).where(PastePlan.id == plan_id))
