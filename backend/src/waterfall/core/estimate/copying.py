# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of the lines of a revision opened from a marked one, private to the module.

The facet of the lines copies them under the nodes the planning copied (``copy_lines``, the
``copy`` hook of ``LINE_FACET``), by one ``INSERT … SELECT`` joined to the identifiers of the
copies (``copies``): five thousand lines sent one by one were most of the ten seconds of the
opening of a revision (US-2240, #3102). The budgeted amount of each comes from the line of its
lineage in the reference revision, read beside: the lineages are the planning's.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Integer,
    Numeric,
    Uuid,
    bindparam,
    column,
    func,
    insert,
    literal,
    null,
    select,
)

from waterfall.core.estimate.remaining.reviewing import was_reviewed
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import lineages_of, lines_of_revision
from waterfall.core.projects.interface import project_facts
from waterfall.platform.database import Base, UtcDateTime, among, copied_columns, copies

if TYPE_CHECKING:
    from typing import Any
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionCopy

NOUGHT = Decimal("0.00")
# The figures a line copied from a review keeps as its remaining to commit before it (EP-09).
PREVIOUS = ("quantity", "hours", "unit_disbursement", "reestimated_amount")
LINE = Base.metadata.tables[EstimateLine.__tablename__]


def _budgets(session: Session, project_id: UUID, reference: UUID) -> dict[UUID, Decimal]:
    """Give the budgeted amount of each line of the reference revision, by its lineage.

    The budgeted amount as read: its re-estimated one when it has none (``budgeted_of``).
    """
    held = lines_of_revision(session, project_id, reference)
    by_node = {node: lineage for lineage, node in held.items()}
    rows = session.execute(
        select(
            EstimateLine.node_id,
            func.coalesce(EstimateLine.budgeted_amount, EstimateLine.reestimated_amount),
        ).where(EstimateLine.project_id == project_id, among(EstimateLine.node_id, by_node))
    )
    return {by_node[node]: amount for node, amount in rows}


def _budgeted(
    session: Session, project_id: UUID, sources: list[UUID]
) -> tuple[dict[UUID, Decimal], bool]:
    """Give the budgeted amount each line copied takes, by its source; and whether it takes one.

    That of the line of the same lineage in the reference revision, nought without one; none on a
    project without a reference, whose lines read their re-estimated amount (EP-07).
    """
    reference = project_facts(session, project_id).reference_revision_id
    if reference is None:
        return {}, False
    budgets = _budgets(session, project_id, reference)
    lineages = lineages_of(session, project_id, sources)
    return {each: budgets.get(lineages[each], NOUGHT) for each in sources}, True


def copy_lines(copy: RevisionCopy) -> None:
    """Copy the lines of the nodes copied into the revision opened (WF-DAT-0010).

    Under the nodes the planning copied (``copy.identifiers``), at their first version, with the
    stamp of the opening; the budgeted amount by the lineage in the reference revision; and, from a
    source marked once its project was In progress, its figures and its re-estimated amount as the
    remaining to commit before the review (``previous_*``), none otherwise (EP-09). The copy of a
    structure into another of the same revision (``copy.within_revision``, a differential opened)
    keeps each line as it is: its budgeted amount and its remaining to commit before, not the
    reference's again.
    """
    session, ids = copy.session, copy.identifiers
    within = copy.within_revision
    sources = list(
        session.scalars(
            select(EstimateLine.node_id).where(
                EstimateLine.project_id == copy.project_id, among(EstimateLine.node_id, ids)
            )
        )
    )
    if not sources:
        return
    budgets, referenced = ({}, False) if within else _budgeted(session, copy.project_id, sources)
    node = copies({each: ids[each] for each in sources}, "copied_line")
    at, author = literal(copy.at, UtcDateTime()), literal(copy.author, Uuid())
    replaced: dict[str, ColumnElement[Any]] = {
        "node_id": node.c.copy,
        "lock_version": literal(1, Integer()),
        "created_at": at,
        "created_by": author,
        "updated_at": at,
        "updated_by": author,
    }
    if not within:
        replaced["budgeted_amount"] = null()
        reviewed = was_reviewed(session, copy.project_id, copy.source)
        for figure in PREVIOUS:
            replaced[f"previous_{figure}"] = LINE.c[figure] if reviewed else null()
    rows = select().select_from(LINE).join(node, node.c.source == LINE.c.node_id)
    if referenced:
        budget = (
            func.unnest(
                bindparam(None, list(budgets), type_=ARRAY(Uuid())),
                bindparam(None, list(budgets.values()), type_=ARRAY(Numeric())),
            )
            .table_valued(column("node_id", Uuid()), column("amount", Numeric()))
            .render_derived(name="budget")
        )
        replaced["budgeted_amount"] = budget.c.amount
        rows = rows.join(budget, budget.c.node_id == LINE.c.node_id)
    names, columns = copied_columns(LINE, replaced)
    session.execute(
        insert(LINE).from_select(
            names, rows.add_columns(*columns).where(LINE.c.project_id == copy.project_id)
        )
    )
