# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines a merge writes into the main structure, private to the module (US-2560/L2).

The estimate's part of the application of a merge (WF-REV-0050, WF-DEV-0020; EP-08, "La fusion et
la survenance"), once the planning has written the tasks; the planning writes the nodes of the
lines (``place_merged_lines``), then this module their facets:

- **A line the differential adds** is a copy of the differential's, under the node the planning
  created for it, at its first version: its figures as they are, which are also its figures of
  reference, and its budgeted amount the amount the differential prices it at — what the amendment
  notifies —; it carries neither the remaining to commit before a review nor the mark of a
  re-estimate.
- **A line of both the differential designates** takes the columns it changes. Its label, its
  category, its role, its subproject and its delay of payment are the line's own. Its figures —
  its quantity, its hours, its unit disbursement — become its figures of reference, and its
  budgeted amount the differential's, whenever the differential changes what prices it (a figure,
  its category or its role); they become its current figures too only when its task is not
  started and nobody re-estimated it (``reestimated_at``), as ``mergeCostStructure`` says.
  Otherwise the current figures stay, whatever the differential changes, its role included: a
  line re-estimated to 140 that the differential brings to 120 bears 120 budgeted and 140
  re-estimated. A role changed keeps the kind of the line — an entry never gives a role to a line
  without one, nor takes it from one (``RESOURCE_ROLE_REQUIRED``, ``FIELD_NOT_ACCEPTED``) —, so
  its current hours stay those of a labour line; the replay prices them at the rate of the role
  it now names. A line the differential only moves, or names only by its label, its subproject or
  its delay of payment, keeps its budget and its figures.
- **The lines of a started task the merge keeps and completes** are brought to a remaining of
  nought by the function of ``setLineRemaining`` (``reestimate``): their quantity nought, priced
  again, marked, the reason of a former re-estimate cleared; their budgeted amount kept — a line
  that read its budget from its re-estimated amount, the project having no reference yet, has it
  written first.
- **A provision line** keeps its figures, its risk's alone; it takes as its budgeted amount the
  provision it carries, which the reference the merge marks fixes: "le montant budgété est celui
  que la référence a fixé" (WF-DEV-0020, WF-RIS-0050; #4274). Written here, before the marking,
  after which the database refuses any write of a line of the revision; a revision opened from it
  takes it by the lineage (``copy_lines``). It never enters the reference budget, the sum of the
  budgeted amounts of the lines but the provisions (``lines_for_indicators``,
  ``reference_budgets``), nor does it advance a counter: a budgeted amount is computed.
  The designation of a marked revision by the command (``reference_correctable``) writes nothing,
  and has nothing to write: a revision it can designate was marked while the project had no
  reference, so that its provision lines bear a budgeted amount of null (``budgeted_of`` reads a
  null as the re-estimated amount, the provision, which is never projected), and the revision
  opened after it copies that null by the lineage. Only a merge, which marks a reference whose
  figures it has just changed, has a budgeted amount to fix (``test_risk_provision_lines.py``, the
  provision line marked plainly then designated). The write here is neither stamped
  (``lock_version``, ``updated_at``, ``updated_by``) as ``_stamped`` and ``_zeroed`` stamp theirs: a
  provision line is closed to the entry, its risk alone writing it, so no entry holds its counter
  to lose, and the revision is marked in the same transaction, which freezes the line and its
  history whole; the amount it gives is the one the line read before, null read as the provision.

The amounts are priced again by the replay of the dates that ends the merge; a provision line is
never priced again.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.entries import LineEntry
from waterfall.core.estimate.reading import rows_of
from waterfall.core.estimate.remaining.reviewing import reestimate
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import FacetWrite, place_merged_lines

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from uuid import UUID

    from waterfall.core.planning.interface import BearingTask, MergedLines
    from waterfall.core.revisions.interface import StructureMerging

NOUGHT = Decimal(0)
# The columns of a line that are its own, taken as the differential has them.
OWN = (
    ("label", "label"),
    ("cost_category", "cost_category_id"),
    ("resource_role", "resource_role_id"),
    ("subproject", "subproject_id"),
    ("payment_delay_days", "payment_delay_days"),
)
# The figures of a line, and those of its reference.
FIGURES = ("quantity", "hours", "unit_disbursement")
REFERENCE = ("reference_quantity", "reference_hours", "reference_unit_disbursement")
# What prices a line: a change of one designates its figures.
PRICING = frozenset({"quantity", "hours", "unit_disbursement", "cost_category", "resource_role"})
# What a line created does not take from the differential's: it has none of them.
CLEARED = (
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
    "reestimated_at",
    "remaining_reason",
)


@dataclass(frozen=True, slots=True)
class LineMerged:
    """A line of the differential the merge writes: its node there, and in the main structure.

    ``held`` the node of the line of the same lineage in the main structure, none for a line the
    differential adds; ``fields`` the columns the differential changes, as the report names them;
    ``task`` the lineage of the task it stands under in the differential.
    """

    source: UUID
    held: UUID | None
    fields: frozenset[str]
    task: UUID


def _stamped(row: EstimateLine, merging: StructureMerging) -> None:
    """Count a write of a line: its version advanced, its author and its instant."""
    row.lock_version += 1
    row.updated_at, row.updated_by = merging.act.at, merging.act.author


def _created(source: EstimateLine, node_id: UUID, merging: StructureMerging) -> EstimateLine:
    """Give the facet of a line the differential adds, under its node in the main structure."""
    act = merging.act
    columns = {each.key: getattr(source, each.key) for each in EstimateLine.__table__.columns}
    columns.update(
        node_id=node_id,
        budgeted_amount=source.reestimated_amount,
        lock_version=1,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
        **dict.fromkeys(CLEARED),
        **{
            reference: getattr(source, figure)
            for reference, figure in zip(REFERENCE, FIGURES, strict=True)
        },
    )
    return EstimateLine(**columns)


def _designated(
    row: EstimateLine, source: EstimateLine, line: LineMerged, *, current: bool
) -> None:
    """Give a line of the main structure what the differential designates of it.

    ``current`` whether its task is not started: its current figures follow the differential's if
    nobody re-estimated it, whatever the columns the differential changes.
    """
    for name, column in OWN:
        if name in line.fields:
            setattr(row, column, getattr(source, column))
    if not line.fields & PRICING:
        return
    for reference, figure in zip(REFERENCE, FIGURES, strict=True):
        setattr(row, reference, getattr(source, figure))
    row.budgeted_amount = source.reestimated_amount
    if current and row.reestimated_at is None:
        for figure in FIGURES:
            setattr(row, figure, getattr(source, figure))


def _zeroed(row: EstimateLine, merging: StructureMerging, bearer: BearingTask) -> None:
    """Bring a line of a task the merge completes to a remaining of nought, its budget kept.

    By the function of ``setLineRemaining`` (``reestimate``), on the task that bears it, without a
    reason: the line counted, priced again and marked, as a re-estimate to nought leaves it.

    ``reestimate`` can refuse, but not here (#4249): the entry sends the quantity alone, which every
    line accepts, so that ``FIELD_NOT_ACCEPTED`` cannot be; and the line exists, its category
    rated for the year of its revision when it was written, a rate no operation takes away (the
    hourly rates are corrected at the version read and "never deleted",
    ``cost_settings/interface/hourly_rates.py``), so that ``HOURLY_RATE_MISSING`` cannot be. The
    report need not announce either; a test shows the merge of a started task bearing a line of
    labour and one that is not (``labor`` and ``non_labor``, the kinds a task bears: a line of
    ``provision`` is the own estimate of a risk, borne by no task of the order),
    ``test_a_started_task_the_merge_completes_is_brought_to_nought_labour_or_not``.
    """
    if row.budgeted_amount is None:
        row.budgeted_amount = row.reestimated_amount
    write = FacetWrite(
        merging.session, merging.project_id, merging.revision_id, row.node_id, bearer, merging.act
    )
    reestimate(write, LineEntry(quantity=NOUGHT, sent=frozenset({"quantity"})), None)


def write_lines(
    merging: StructureMerging, where: MergedLines, lines: Collection[LineMerged]
) -> None:
    """Write the lines of a merge: their nodes by the planning, then their facets.

    ``lines`` those the differential adds or designates, in its order.
    """
    session, project_id = merging.session, merging.project_id
    created = place_merged_lines(merging)
    sources = {
        each.node_id: each for each in rows_of(session, project_id, [line.source for line in lines])
    }
    held_nodes = [each.held for each in lines if each.held is not None]
    held_nodes += [
        each.node_id
        for each in where.main
        if each.is_provision or each.task_lineage_id in where.completing
    ]
    held: Mapping[UUID, EstimateLine] = {
        each.node_id: each for each in rows_of(session, project_id, held_nodes)
    }
    sent = {each.held for each in lines}
    for line in lines:
        source = sources[line.source]
        if line.held is None:
            session.add(_created(source, created[line.source], merging))
            continue
        row = held[line.held]
        if line.fields - {"parent"}:
            _designated(row, source, line, current=line.task not in where.started)
            _stamped(row, merging)
    for each in where.main:
        completing = each.task_lineage_id in where.completing
        if each.is_provision:
            _provision_budgeted(held[each.node_id])
        elif completing and each.node_id not in sent:
            _zeroed(held[each.node_id], merging, where.bearers[each.task_lineage_id])
    session.flush()


def _provision_budgeted(row: EstimateLine) -> None:
    """Give a provision line of the reference the merge marks its provision as its budgeted amount.

    Its re-estimated amount, which is its provision, never projected (``set_provision``).
    """
    if row.budgeted_amount != row.reestimated_amount:
        row.budgeted_amount = row.reestimated_amount
