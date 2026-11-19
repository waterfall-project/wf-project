# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines a graft copies into another structure, private to the module (US-2620/L1).

The facet of the lines answers the graft of the planning (``FacetHooks.judge_graft``,
``FacetHooks.graft``; EP-08, "Modules"), which the occurrence of a risk asks to merge its own
estimate into the main structure (WF-RIS-0060):

- **Judged.** A task grafted keeps its lines, hence the calendar their roles give it; a role whose
  calendar has since lost its hours — the reference changed after the revision was marked — would
  leave it without an hour in its week. Each such task is a reason that refuses the graft, its
  roles and the task named as the structure grafted holds it, the task copied having no node yet
  (``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010, ``ReportRefusal``).
- **Written.** Each line keeps its figures, under the node the planning copied it to, at its first
  version, with the stamp of the graft; its budgeted amount is nought — the line of a risk that
  occurred is work the reference did not hold (WF-RIS-0060, WF-RAE-0050) —, and it carries neither
  the grandeurs of a reference, nor the remaining to commit before a review, nor the mark of a
  re-estimation: it is created in the structure grafted into. Its re-estimated amount is the
  planning's to price again on the dates of its task there, once the engine is replayed, which
  keeps that of the structure grafted while its dates do not change.

The provision line the graft removes goes by the deletion of its node (``delete_lines``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Integer, Numeric, Uuid, insert, literal, null, select

from waterfall.core.estimate.costing import judge_working_hours
from waterfall.core.estimate.tables import EstimateLine
from waterfall.platform.database import Base, UtcDateTime, among, copied_columns, copies
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import BearingTask, FacetGraft

NOUGHT = Decimal("0.00")
LINE = Base.metadata.tables[EstimateLine.__tablename__]
# What a line grafted does not take from its source: created, it has none of them.
CLEARED = (
    "reference_quantity",
    "reference_hours",
    "reference_unit_disbursement",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
    "reestimated_at",
    "remaining_reason",
)


def judge_grafted_lines(
    session: Session, project_id: UUID, lines: Mapping[UUID, BearingTask]
) -> tuple[Mapping[str, Any], ...]:
    """Give a refusal for each task grafted whose labour lines would leave it without an hour.

    The roles of every labour line of the task intersected day by day, as an entry judges them
    (``judge_working_hours``), once by task, in the order of the lines given.
    """
    roles = dict(
        session.execute(
            select(EstimateLine.node_id, EstimateLine.resource_role_id).where(
                EstimateLine.project_id == project_id,
                among(EstimateLine.node_id, lines),
                EstimateLine.resource_role_id.is_not(None),
            )
        ).all()
    )
    judged: set[UUID] = set()
    refusals: list[Mapping[str, Any]] = []
    for line, bearer in lines.items():
        role = roles.get(line)
        if role is None or bearer.task_id in judged:
            continue
        judged.add(bearer.task_id)
        try:
            judge_working_hours(session, (project_id, bearer, line), role)
        except UnprocessableError as refused:
            refusals.append({"code": refused.code, "params": dict(refused.params)})
    return tuple(refusals)


def graft_lines(graft: FacetGraft) -> None:
    """Write the lines a graft copied, at a budgeted amount of nought, in one statement."""
    node = copies(graft.copies, "grafted_line")
    at, author = literal(graft.act.at, UtcDateTime()), literal(graft.act.author, Uuid())
    replaced: dict[str, ColumnElement[Any]] = {
        "node_id": node.c.copy,
        "budgeted_amount": literal(NOUGHT, Numeric()),
        "lock_version": literal(1, Integer()),
        "created_at": at,
        "created_by": author,
        "updated_at": at,
        "updated_by": author,
        **{name: null() for name in CLEARED},
    }
    names, columns = copied_columns(LINE, replaced)
    rows = (
        select(*columns)
        .select_from(LINE)
        .join(node, node.c.source == LINE.c.node_id)
        .where(LINE.c.project_id == graft.project_id)
    )
    graft.session.execute(insert(LINE).from_select(names, rows))
