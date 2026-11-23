# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the witness: declared, reviewed, occurred, at the instants of the chronology.

``witness_risks.json`` (``wftools.mockwitnessrisksfile``) describes the three risks of PRJ-001; the
chronology says when each is declared, reviewed and occurs (``risk_declared``, ``risk_reviewed``,
``risk_occurred``; EP-08, "Le chargeur du témoin", US-2650/L1). Each write is made through the
interface of the risks, by the rules of the API, by the project manager of the witness at the
instant of its event:

- **the declaration** (``load_risk``) in the revision in progress, under the identifiers the
  witness imposes — the risk, its own estimate, its provision line, whose lineage is that
  identifier —, its provision under the task the description names by its lineage; its own
  estimate born whole, the copy of the main structure (EP-30), to which what the revision gives
  it is added, its tasks then its lines, at the first level after those of the main structure: a
  declaration keeps the severity of an own estimate that designates nothing, the review that
  follows it in the chronology the one so entered (WF-RIS-0010);
- **a review** (``review_risk``) at the counter of the risk read, which may dismiss it;
- **the occurrence** (``load_occurrence``), its own estimate merged into the main structure, then
  the states of the tasks the examples give the nodes grafted laid as the description of the
  revision in progress gives them.

The own estimate of a risk in the revision opened, and before its occurrence, is copied again from
the main structure, then entered (``enter_estimate``): the update that would carry the main
structure into it is US-3090's, and the loader takes it up with US-3150, whose examples read the own
estimates as differentials; until then, the examples of the risks the loader strays from are
declared where the tests compare them (US-3070/L3).
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from waterfall.core.planning.interface import (
    Place,
    ProgressLoad,
    Writer,
    load_own_estimate_again,
    load_progress,
    task_of_lineage,
)
from waterfall.core.revisions.interface import aimed_structure
from waterfall.core.risks.interface import (
    OccurrenceLoad,
    RiskEntry,
    RiskLoad,
    RiskReviewEntry,
    load_occurrence,
    load_risk,
    read_risk,
    review_risk,
)
from waterfall.witness.estimate_lines import write_lines
from waterfall.witness.filling import LineRow, Strict, TaskRow, node_identifier
from waterfall.witness.tasks import add_tasks

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface import RiskState
    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness
    from waterfall.witness.timeline import RiskDeclared, RiskOccurred, RiskReviewed

RISKS_FILE = "witness_risks.json"
NOT_STARTED = "not_started"
# The namespace the nodes of an own estimate are derived in, in a revision the examples do not read
# them in.
_NODE_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/own_estimate_node")


class _Structure(Strict):
    """The own estimate of a risk in a revision."""

    revision: int
    structure_id: UUID


class _Estimate(Strict):
    """What the own estimate of a risk holds in a revision where it is entered."""

    revision: int
    read_in: int
    planning_start_on: date
    tasks: list[TaskRow]
    lines: list[LineRow]


class _Grafted(Strict):
    """A node the occurrence grafts: the lineage of its own node, its copy and the lineage of it."""

    lineage_id: UUID
    node_id: UUID
    copy_lineage_id: UUID


class RiskRow(Strict):
    """A risk of the witness, as ``witness_risks.json`` describes it."""

    risk_id: UUID
    label: str
    description: str | None
    mitigation_notes: str | None
    probability: Decimal
    provision_task_lineage_id: UUID
    provision_cost_category_id: UUID
    provision_subproject_id: UUID | None
    provision_lineage_id: UUID
    provision_node_id: UUID
    structures: list[_Structure]
    estimates: list[_Estimate]
    grafted: list[_Grafted]

    def structure_in(self, revision: int) -> UUID | None:
        """Give the own estimate of the risk in a revision, if the witness names it."""
        found = [each.structure_id for each in self.structures if each.revision == revision]
        return found[0] if found else None

    def estimate_in(self, revision: int) -> _Estimate | None:
        """Give what its own estimate holds in a revision, if it is entered there."""
        found = [each for each in self.estimates if each.revision == revision]
        return found[0] if found else None


class Risks(Strict):
    """The risks of the witness, in the order of their declaration."""

    risks: list[RiskRow]

    def named(self, risk_id: UUID) -> RiskRow:
        """Give a risk the chronology names; or refuse the file."""
        for each in self.risks:
            if each.risk_id == risk_id:
                return each
        message = f"the chronology names a risk {risk_id} that {RISKS_FILE} does not"
        raise ValueError(message)

    def grafted(self) -> frozenset[UUID]:
        """Give the lineages of the nodes the occurrences graft into the main structure."""
        return frozenset(node.copy_lineage_id for risk in self.risks for node in risk.grafted)

    @classmethod
    def read(cls, witness: Witness) -> Risks:
        """Read the risks of the witness; a file that strays raises."""
        return witness.read(RISKS_FILE, cls)


@dataclass(frozen=True, slots=True)
class RiskWrite:
    """Where and by whom a write of a risk is made.

    The project, its revision in progress and its number, the project manager, and the instant of
    the event.
    """

    project_id: UUID
    revision: tuple[UUID, int]
    manager: Viewer
    at: Act

    @property
    def writer(self) -> Writer:
        """Give the writer of the write: the project manager, at the instant of the event."""
        return Writer(replace(self.at, author=self.manager.user_id), None)


def declare(session: Session, risks: Risks, write: RiskDeclared, made: RiskWrite) -> None:
    """Declare a risk in the revision in progress, enter its own estimate, review it as entered."""
    risk = risks.named(write.risk_id)
    revision_id, number = made.revision
    project_id = made.project_id
    main = aimed_structure(session, project_id, revision_id, None)
    task = (
        None
        if main is None
        else task_of_lineage(session, project_id, main, risk.provision_task_lineage_id)
    )
    structure_id = risk.structure_in(number)
    if task is None or structure_id is None:
        message = f"the risk {risk.label} names no task or no own estimate in revision {number}"
        raise ValueError(message)
    entry = RiskEntry(
        label=risk.label,
        probability=risk.probability,
        description=risk.description,
        mitigation_notes=risk.mitigation_notes,
        provision_cost_category_id=risk.provision_cost_category_id,
        provision_subproject_id=risk.provision_subproject_id,
        provision_task_id=task.node_id,
    )
    load = RiskLoad(entry, risk.risk_id, structure_id, risk.provision_lineage_id)
    load_risk(session, project_id, load, made.writer, made.manager)
    enter_estimate(session, risk, made, again=False)


def review(session: Session, write: RiskReviewed, made: RiskWrite) -> None:
    """Review a risk at the counter read, by the probability and the state of the chronology."""
    _reviewed(session, write.risk_id, (write.probability, write.state), made)


def _reviewed(
    session: Session, risk_id: UUID, retained: tuple[Decimal, RiskState], made: RiskWrite
) -> None:
    """Review a risk in the revision in progress, at its counter read there."""
    probability, state = retained
    read = read_risk(session, made.project_id, risk_id, made.revision[0], made.manager)
    entry = RiskReviewEntry(risk_id, probability, state, read.lock_version)
    review_risk(session, made.project_id, entry, made.writer, made.manager)


def occur(
    session: Session, risks: Risks, write: RiskOccurred, made: RiskWrite, tasks: Iterable[TaskRow]
) -> None:
    """Declare the occurrence of a risk, then lay the states of the tasks it merged.

    ``tasks`` the tasks the description gives the revision in progress, where the nodes the graft
    of EP-08 copied are described: the merge adds them under the lineage they have in the own
    estimate, by which their states are laid (US-3070/L3).
    """
    risk = risks.named(write.risk_id)
    occurrence = OccurrenceLoad(risk.risk_id)
    # Merged up to date: what the main structure received since is carried into it first.
    enter_estimate(session, risk, made, read_from=_last_estimate(risk))
    load_occurrence(session, made.project_id, occurrence, made.writer.act)
    project_id, revision_id = made.project_id, made.revision[0]
    main = aimed_structure(session, project_id, revision_id, None)
    merged = {each.copy_lineage_id: each.lineage_id for each in risk.grafted}
    rows = [task for task in tasks if task.lineage_id in merged]
    summaries = {task.parent_lineage_id for task in rows}
    for task in rows:
        if task.lineage_id in summaries or task.progress == NOT_STARTED or main is None:
            continue
        held = task_of_lineage(session, project_id, main, merged[task.lineage_id])
        if held is None:
            continue
        state = ProgressLoad(held.node_id, task.progress, task.started_on, task.completed_on)
        load_progress(session, project_id, state, made.writer.act)


def _last_estimate(risk: RiskRow) -> int | None:
    """Give the last revision that gives the own estimate of a risk, none if none does."""
    return max((each.revision for each in risk.estimates), default=None)


def enter_estimate(
    session: Session,
    risk: RiskRow,
    made: RiskWrite,
    *,
    again: bool = True,
    read_from: int | None = None,
) -> bool:
    """Enter the own estimate of a risk as the revision in progress gives it; tell whether it did.

    Its tasks then its lines, added to the copy of the main structure it holds (EP-30), under the
    identifiers the examples read them by in the revision they name, derived from those in another.
    ``again`` copies the main structure into it and its base again first, as the update would
    (``load_own_estimate_again``); ``read_from`` the revision whose description it takes, the one
    in progress by default.
    """
    revision_id, number = made.revision
    estimate = risk.estimate_in(number if read_from is None else read_from)
    structure_id = risk.structure_in(number)
    if estimate is None or structure_id is None:
        return False
    project_id = made.project_id
    if again:
        main = aimed_structure(session, project_id, revision_id, None)
        if main is None:
            message = f"revision {number} holds no main structure"
            raise ValueError(message)
        main_place = Place(project_id, revision_id, main)
        load_own_estimate_again(session, main_place, structure_id, made.writer.act)
    place = Place(project_id, revision_id, structure_id)

    def identified(row: TaskRow | LineRow) -> UUID:
        return node_identifier(_NODE_NAMESPACE, number, row.node_id, estimate.read_in)

    written = (estimate.planning_start_on, estimate.tasks)
    add_tasks(session, place, written, identified, made.at)
    write_lines(session, place, (estimate.lines, identified), made.at, additive=True)
    return True


def copied_nodes(risks: Risks, revision: int) -> dict[UUID, dict[UUID, UUID]]:
    """Give the identifiers the copy into a revision imposes on the nodes of the risks.

    In the own estimate the examples read there, its nodes by their lineage; in the main structure,
    the copy of each provision line, by its lineage.
    """
    nodes: dict[UUID, dict[UUID, UUID]] = {}
    for risk in risks.risks:
        estimate = risk.estimate_in(revision)
        structure_id = risk.structure_in(revision)
        if estimate is not None and structure_id is not None and estimate.read_in == revision:
            rows: Collection[TaskRow | LineRow] = [*estimate.tasks, *estimate.lines]
            nodes[structure_id] = {row.lineage_id: row.node_id for row in rows}
    return nodes


def provision_copies(risks: Risks) -> dict[UUID, UUID]:
    """Give the identifier of the copy of each provision line in the revision 102, by lineage."""
    return {risk.provision_lineage_id: risk.provision_node_id for risk in risks.risks}


def structure_copies(risks: Risks, revision: int, source: int) -> dict[UUID, UUID]:
    """Give the own estimate of each risk in a revision, by its identifier in ``source``."""
    return {
        each: found
        for risk in risks.risks
        if (each := risk.structure_in(source)) is not None
        and (found := risk.structure_in(revision)) is not None
    }
