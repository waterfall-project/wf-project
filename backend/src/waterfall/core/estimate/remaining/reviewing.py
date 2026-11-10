# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line reviewed, private to the module (US-1580/L2; EP-09, "Modules").

The re-estimate of a line writes its figures by the function that writes the estimate
(``change_line``, the facet of EP-07): the re-estimated amount recomputed, the budgeted amount and
the lineage left as they are, the previous figures too; it marks the line (``reestimated_at``) and
keeps the reason sent, overwritten by each re-estimate (``remaining_reason``). A figure of
``reestimated_amount_basis`` refused is named under that object (``/reestimated_amount_basis/…``).
A line keeps a task open while its re-estimated amount is not nought, a provision line never: its
amount is the one its risk computes (WF-RIS-0010), none before EP-08.

The copy of a revision gives each line copied, after the copy of the lines, the figures and the
re-estimated amount its source holds as its remaining to commit before the review (``previous_*``)
when the source was marked once its project was In progress — the instant of the passage compared
to that of the marking —, none otherwise: an offer marked in pricing is no review (EP-09, "Ce que
le cadrage décide"). The mark and the reason are those of the line copied, as every column of it.

The remaining to commit of a revision sums the re-estimated amounts of the lines, provisions left
out, of the tasks not completed of its main structure, at the state of its tasks (EP-09, "Les
indicateurs du reste à engager").
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import update

from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.estimate.placing import placed_lines
from waterfall.core.estimate.reading import rows_of
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.estimate.writing import change_line, read_line
from waterfall.core.projects.interface import list_state_transitions
from waterfall.core.revisions.interface import revision_marked_at
from waterfall.platform.errors import FieldError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.entries import LineEntry
    from waterfall.core.planning.interface import FacetWrite
    from waterfall.core.revisions.interface import RevisionCopy

BASIS = "/reestimated_amount_basis"
FIGURES = frozenset({"/quantity", "/hours", "/unit_disbursement"})
PROVISION = "provision"
IN_PROGRESS = "in_progress"
NOUGHT = Decimal("0.00")


def _pointed(refused: UnprocessableError) -> UnprocessableError:
    """Name the figures a re-estimate refuses under the object that sends them."""
    fields = tuple(
        FieldError(f"{BASIS}{each.pointer}", each.code, each.params)
        if each.pointer in FIGURES
        else each
        for each in refused.fields
    )
    return UnprocessableError(refused.code, refused.params, fields)


def reestimate(write: FacetWrite, figures: LineEntry, reason: str | None) -> None:
    """Write the figures sent of a line, priced again, marked and with its reason; or refuse (422).

    Refused as the entry of the estimate refuses a figure: one the line does not accept
    (``FIELD_NOT_ACCEPTED``), one below nought (``VALUE_OUT_OF_RANGE``), a category without a rate
    (``HOURLY_RATE_MISSING``).
    """
    try:
        change_line(write, figures)
    except UnprocessableError as refused:
        raise _pointed(refused) from None
    line = read_line(write.session, write.project_id, write.node_id)
    line.reestimated_at = write.act.at
    line.remaining_reason = reason
    write.session.flush()


def provisions_of(session: Session, rows: Collection[EstimateLine]) -> frozenset[UUID]:
    """Give, of the lines read, the provision lines: their category is of the provision kind."""
    categories = category_labels(session, {row.cost_category_id for row in rows})
    return frozenset(
        row.node_id
        for row in rows
        if (category := categories.get(row.cost_category_id)) is not None
        and category.cost_type_kind == PROVISION
    )


def keeps_open(session: Session, project_id: UUID, line_ids: Sequence[UUID]) -> bool:
    """Tell whether one of the lines named keeps a remaining to commit, a provision never."""
    rows = rows_of(session, project_id, line_ids)
    provisions = provisions_of(session, rows)
    return any(row.reestimated_amount != 0 for row in rows if row.node_id not in provisions)


def _reviewed(session: Session, project_id: UUID, revision_id: UUID) -> bool:
    """Tell whether a revision was marked once its project was In progress (a review)."""
    marked = revision_marked_at(session, revision_id)
    if marked is None:
        return False
    passages = [
        each.occurred_at
        for each in list_state_transitions(session, project_id)
        if each.to_state == IN_PROGRESS
    ]
    return bool(passages) and min(passages) <= marked


def copy_previous(copy: RevisionCopy) -> None:
    """Give the lines copied the remaining to commit of their source, if it was a review."""
    session = copy.session
    sources = rows_of(session, copy.project_id, list(copy.identifiers))
    if not sources:
        return
    reviewed = _reviewed(session, copy.project_id, copy.source)
    session.execute(
        update(EstimateLine),
        [
            {
                "project_id": copy.project_id,
                "node_id": copy.identifiers[row.node_id],
                "previous_quantity": row.quantity if reviewed else None,
                "previous_hours": row.hours if reviewed else None,
                "previous_unit_disbursement": row.unit_disbursement if reviewed else None,
                "previous_reestimated_amount": row.reestimated_amount if reviewed else None,
            }
            for row in sources
        ],
    )


def revision_remaining(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[Decimal, dict[UUID, Decimal]]:
    """Give the remaining to commit of a revision, and each line's, at the state of its tasks."""
    placed = placed_lines(session, project_id, revision_id)
    provisions = provisions_of(session, [each.line for each in placed])
    by_line = {
        each.line.node_id: each.line.reestimated_amount
        for each in placed
        if not each.is_completed and each.line.node_id not in provisions
    }
    return sum(by_line.values(), NOUGHT), by_line
