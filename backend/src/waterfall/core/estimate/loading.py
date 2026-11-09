# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the witness: a revision's estimate reconciled with the one the witness describes.

What the loader of the witness asks of the estimate for a revision it has just opened and whose
tasks it has written (EP-07, "Le chargeur du témoin"; ``load_lines``): the lines the copy gave the
revision are reconciled by lineage with those described — deleted, changed, created, their
identifiers and their instant imposed — by the planning, which owns the nodes
(``load_line_nodes``) and asks the hooks of this module for the facets. The amounts are those the
service computes, in the frame of a creation: each line judged as the API judges it, then priced at
the rates of its revision, on the dates the engine computes once the structure is written; the
computed is the expected.

A line created has the budgeted amount of the line of its lineage in the reference revision, nought
without one, as a line copied has (``copy_lines``); null while the project has no reference.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.writing import HoursJudged
from waterfall.core.planning.interface import LineNodeLoad, lines_of_revision, load_line_nodes
from waterfall.core.projects.interface import project_facts

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.entries import LineEntry
    from waterfall.core.planning.interface import Place
    from waterfall.platform.audit import Act

NOUGHT = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class LineLoad:
    """A line as the witness describes it: its identifiers, its task's lineage, its rank, its facet.

    ``entry`` is what the line is entered with (``EstimateLineWrite``), every field of the facet
    given, null ones included (``LineEntry.sent``); ``position`` its rank among the lines of its
    task, from 1.
    """

    node_id: UUID
    lineage_id: UUID
    task_lineage_id: UUID
    position: int
    entry: LineEntry


def _budgeted(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the lines of a revision the budgeted amount of their lineage in the reference."""
    reference = project_facts(session, project_id).reference_revision_id
    if reference is None or reference == revision_id:
        return
    held = lines_of_revision(session, project_id, revision_id)
    kept = lines_of_revision(session, project_id, reference)
    budgets = {
        line.node_id: budgeted_of(line)
        for line in rows_of(session, project_id, list(kept.values()))
    }
    lineages = {node: lineage for lineage, node in held.items()}
    for line in rows_of(session, project_id, list(held.values())):
        node = kept.get(lineages[line.node_id])
        budgeted = NOUGHT if node is None else budgets.get(node, NOUGHT)
        if line.budgeted_amount != budgeted:
            line.budgeted_amount = budgeted
    session.flush()


def load_lines(session: Session, place: Place, lines: tuple[LineLoad, ...], act: Act) -> None:
    """Reconcile the structure of a revision just opened with the lines the witness describes.

    A line created is judged as a creation is, but for the hours of its task, judged by the
    engine on the structure the whole description leaves (``HoursJudged``): the roles of a task
    given one by one would be refused against a structure half written. A line kept is changed in
    place. The budgeted amounts are then those of the lineage in the reference revision.
    """
    nodes = tuple(
        LineNodeLoad(
            each.node_id,
            each.lineage_id,
            each.task_lineage_id,
            each.position,
            HoursJudged(each.entry),
            each.entry,
        )
        for each in lines
    )
    load_line_nodes(session, place, nodes, act)
    _budgeted(session, place.project_id, place.revision_id)
