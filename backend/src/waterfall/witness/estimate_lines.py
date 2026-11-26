# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the revisions of the witness: the estimate of each revision, after its tasks.

Registered by ``register_revision_filler`` (``chronology``), after the tasks: once the slice of the
revisions opens a revision of PRJ-001 — 100, 101, 102 — and its tasks are written, before the next
event marks it, it reconciles by lineage the lines the copy gave the revision with those
``witness_lines.json`` describes for it — created, changed, deleted — through the interface of the
estimate, at the identifiers and the instant imposed (EP-07, "Le chargeur du témoin"). The amounts
are those the service computes: the lines are judged as a creation is, priced at the rates of their
revision on the dates the engine computes, and the computed is the expected.

The identifier of a node is its own in a revision: the file gives each lineage the one it has in
the revision in progress, where the examples of the contract read them; a marked revision holds the
same lineages under identifiers derived from those, so that two loadings give the same ones. The
file is read by a model of its own, strict, which does not import ``wftools``. It describes the
lines of the tasks and nothing of the provisions, which the declaration of a risk creates (EP-08).
"""

from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from waterfall.core.estimate.interface import LineEntry, LineLoad, load_lines
from waterfall.core.planning.interface import Place
from waterfall.core.revisions.interface import aimed_structure
from waterfall.witness.filling import LineRow, Strict, node_identifier

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness
    from waterfall.witness.filling import Filling

LINES_FILE = "witness_lines.json"
_NODE_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/estimate_line")
# What an entry of a line gives, null fields included (``EstimateLineWrite``).
_ENTERED = frozenset(
    {
        "label",
        "cost_category_id",
        "resource_role_id",
        "quantity",
        "hours",
        "unit_disbursement",
        "payment_delay_days",
        "subproject_id",
    }
)


class _Revision(Strict):
    """What the file says of a revision: its number, and how many lines it gives it."""

    revision: int
    line_count: int


class _Lines(Strict):
    """The lines of the witness by revision, as ``witness_lines.json`` keeps them."""

    revisions: list[_Revision]
    lines: list[LineRow]


def _load(line: LineRow, node_id: UUID) -> LineLoad:
    """Give a line as the estimate loads it."""
    entry = LineEntry(
        label=line.label,
        cost_category_id=line.cost_category_id,
        quantity=line.quantity,
        resource_role_id=line.resource_role_id,
        hours=line.hours,
        unit_disbursement=line.unit_disbursement,
        payment_delay_days=line.payment_delay_days,
        subproject_id=line.subproject_id,
        sent=_ENTERED,
    )
    return LineLoad(
        node_id,
        line.lineage_id,
        line.task_lineage_id,
        line.position,
        entry,
    )


def fill(session: Session, witness: Witness, filling: Filling) -> None:
    """Write the lines the witness describes for a structure, by lineage.

    The lines of the structure the copy gave are reconciled with the described ones. A revision
    the file does not describe is left as it is; one it describes with a count other than its lines
    is a defect of the file, which stops the command.
    """
    number = filling.number
    described = witness.read(LINES_FILE, _Lines)
    revision = next((each for each in described.revisions if each.revision == number), None)
    if revision is None:
        return
    current = max(each.revision for each in described.revisions)
    own = [line for line in described.lines if line.revision == number]
    if len(own) != revision.line_count:
        message = f"revision {number} gives {len(own)} lines, not {revision.line_count}"
        raise ValueError(message)
    project_id = filling.revision.project_id.root
    revision_id = filling.revision.revision_id.root
    changes = filling.changes
    structure_id = filling.structure_id or aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        message = f"revision {number} holds no main structure"
        raise ValueError(message)

    def identified(line: LineRow) -> UUID:
        if changes is not None:
            return changes.node(line.lineage_id)
        return node_identifier(_NODE_NAMESPACE, line.revision, line.node_id, current)

    place = Place(project_id, revision_id, structure_id)
    write_lines(session, place, (filling.lines(own), identified), filling.act)


def write_lines(
    session: Session,
    place: Place,
    lines: tuple[Iterable[LineRow], Callable[[LineRow], UUID]],
    act: Act,
    *,
    additive: bool = False,
) -> None:
    """Reconcile a structure with the lines described; the second of ``lines`` gives their node.

    ``additive`` adds them to what it holds: the own estimate of a risk (``load_lines``).
    """
    described, identified = lines
    loaded = tuple(_load(line, identified(line)) for line in described)
    load_lines(session, place, loaded, act, additive=additive)
