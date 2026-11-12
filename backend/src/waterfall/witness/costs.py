# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs of the witness: its imports, their lines and the exclusion, at their instants.

Called by the march of the events of the revisions (``witness.revisions``), after the lines, for
each write of the chronology that concerns the actual costs (EP-09, "Le chargeur du témoin"):

- an import applied (``cost_import_applied``): the import of the exchanges that applied it, in its
  state, with its report as its analysis presented it and its period (``load_import``); the entry
  of the journal of the costs, its period, its columns kept and its four counts
  (``load_cost_import``); then the lines it created or updated (``load_cost_lines``), each imputed
  by the service to the subproject its code names, or to the project alone;
- a line excluded (``cost_line_excluded``): the line of its document and its item taken out of the
  tracked scope for its reason (``load_exclusion``);
- an extraction expired (``import_expired``): the import of the exchanges, analysed, expired the
  day after without being applied (``load_import``).

Each at the identifiers of ``witness_costs.json`` — written by ``make mock-data`` beside the
examples, read here by a model of its own, strict, without importing ``wftools`` — and the instant
of its event, the project manager of the witness for account: an import is requested by an
account, which the platform is not. The instants and the files of the imports of the exchanges are
those ``imports.json`` lists, the report of the extraction expired that of
``import_actual_costs_analysed.json``; a description whose files disagree with the chronology
stops the command, nothing written. The amounts and the imputations are those the service computes:
the computed becomes the expected. Nothing is loaded for the remaining to commit: the copy of the
revision 102 from the reference 101 gives it.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from waterfall.api.contract.models import Import, ImportReport
from waterfall.core.costs.interface import (
    CostImportLoad,
    CostLineLoad,
    load_cost_import,
    load_cost_lines,
    load_exclusion,
)
from waterfall.core.exchanges.interface import ImportLoad, load_import
from waterfall.platform.audit import Act
from waterfall.witness.timeline import CostImportApplied, CostLineExcluded, ImportExpired

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

COSTS_FILE = "witness_costs.json"
IMPORTS_FILE = "imports.json"
EXPIRED_FILE = "import_actual_costs_analysed.json"
ACTUAL_COSTS = "actual_costs"

type Count = Annotated[int, Field(ge=0)]


class _Strict(BaseModel):
    """A model of the file: no field beyond those it names."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CostImportEntry(_Strict):
    """An import of actual costs of the journal, as ``wftools.mockwitnesscostfile`` writes it."""

    cost_import_id: UUID
    imported_at: AwareDatetime
    import_id: UUID
    filename: str
    period_from: date | None
    period_to: date | None
    kept_columns: list[str]
    report: ImportReport
    created_count: Count
    updated_count: Count
    unchanged_count: Count
    rejected_count: Count


class Exclusion(_Strict):
    """When a line was taken out of the tracked scope, and why."""

    excluded_at: AwareDatetime
    reason: str


class CostLineEntry(_Strict):
    """A line of cost of the witness: its document, its figures, the imports that brought it."""

    cost_line_id: UUID
    document_number: str
    document_item: str | None
    document_date: date
    amount: Decimal
    subproject_code: str | None
    subproject_id: UUID | None
    passthrough: dict[str, str]
    created_by_cost_import_id: UUID
    updated_by_cost_import_ids: list[UUID]
    excluded: Exclusion | None

    def brought_by(self, cost_import_id: UUID) -> bool:
        """Tell whether an import created or updated the line."""
        return cost_import_id in {self.created_by_cost_import_id, *self.updated_by_cost_import_ids}

    def load(self) -> CostLineLoad:
        """Give the line as an import of the witness writes it."""
        return CostLineLoad(
            cost_line_id=self.cost_line_id,
            document_number=self.document_number,
            document_item=self.document_item,
            document_date=self.document_date,
            amount=self.amount,
            subproject_code=self.subproject_code,
            passthrough=self.passthrough,
        )


class WitnessCosts(_Strict):
    """The imports of actual costs of the witness, in the order of the journal, and their lines."""

    imports: list[CostImportEntry]
    lines: list[CostLineEntry]


class Imports(BaseModel):
    """The imports of the project of the witness, as ``listImports`` answers them."""

    items: list[Import]


@dataclass(frozen=True, slots=True)
class Costs:
    """What the slice reads of the description: the costs, the imports listed, the one expired."""

    costs: WitnessCosts
    listed: dict[UUID, Import]
    expired: Import

    @classmethod
    def read(cls, witness: Witness) -> Costs:
        """Read the three files of the description the slice writes from."""
        listed = witness.read(IMPORTS_FILE, Imports).items
        return cls(
            witness.read(COSTS_FILE, WitnessCosts),
            {item.import_id.root: item for item in listed},
            witness.read(EXPIRED_FILE, Import),
        )

    def entry(self, cost_import_id: UUID) -> CostImportEntry:
        """Give an import of the journal by its identifier; or refuse the file."""
        for each in self.costs.imports:
            if each.cost_import_id == cost_import_id:
                return each
        message = f"the chronology names an import of costs {cost_import_id} {COSTS_FILE} does not"
        raise ValueError(message)

    def line(self, document: str, item: str | None) -> CostLineEntry:
        """Give a line of cost by its document and its item; or refuse the file."""
        for each in self.costs.lines:
            if (each.document_number, each.document_item) == (document, item):
                return each
        message = f"the chronology names a line {document} {item} that {COSTS_FILE} does not"
        raise ValueError(message)

    def listing(self, import_id: UUID, status: Literal["applied", "expired"]) -> Import:
        """Give an import of the exchanges as ``imports.json`` lists it, in its state; or refuse."""
        found = self.listed.get(import_id)
        if found is None or found.kind.value != ACTUAL_COSTS or found.status.value != status:
            message = f"{IMPORTS_FILE} lists no import {import_id} of actual costs {status}"
            raise ValueError(message)
        return found


def _report(report: ImportReport | None, source: str) -> dict[str, object]:
    """Give a report as its analysis presented it: the keys the file gives, nothing added."""
    if report is None:
        message = f"the import of {source} has no report"
        raise ValueError(message)
    return report.model_dump(mode="json", exclude_unset=True)


def _import(listed: Import, project_id: UUID, report: dict[str, object]) -> ImportLoad:
    """Give an import of the exchanges listed, with its report, as the witness writes it."""
    period_from, period_to = _period(listed)
    return ImportLoad(
        import_id=listed.import_id.root,
        project_id=project_id,
        kind=ACTUAL_COSTS,
        filename=listed.filename,
        status="applied" if listed.status.value == "applied" else "expired",
        period_from=period_from,
        period_to=period_to,
        report=report,
        created_at=listed.created_at.root,
        expires_at=_expiry(listed),
    )


def _expiry(listed: Import) -> AwareDatetime:
    """Give the instant the report of an import listed expires at; one without is refused."""
    if listed.expires_at is None:
        message = f"{IMPORTS_FILE} gives the import {listed.import_id.root} no expiry"
        raise ValueError(message)
    return listed.expires_at.root


@dataclass(frozen=True, slots=True)
class CostWrite:
    """A write of the costs at its event: the project, the account it is made by, the instant."""

    project_id: UUID
    account: UUID
    at: datetime

    @property
    def act(self) -> Act:
        """Give the act of the write: the account, at the instant of the event."""
        return Act(self.account, self.at)


def write(
    session: Session,
    costs: Costs,
    made: CostImportApplied | CostLineExcluded | ImportExpired,
    at: CostWrite,
) -> None:
    """Make a write of the chronology that concerns the actual costs, at its event's instant."""
    match made:
        case CostImportApplied():
            _apply(session, costs, made.cost_import_id, at)
        case CostLineExcluded():
            _exclude(session, costs, made, at)
        case ImportExpired():
            _expire(session, costs, made.import_id, at)


def _apply(session: Session, costs: Costs, cost_import_id: UUID, at: CostWrite) -> None:
    """Write an import applied: its import of the exchanges, its entry, the lines it brought."""
    entry = costs.entry(cost_import_id)
    if entry.imported_at != at.at:
        message = f"the import of costs {cost_import_id} is not applied at its event"
        raise ValueError(message)
    listed = costs.listing(entry.import_id, "applied")
    if (listed.filename, _period(listed)) != (entry.filename, (entry.period_from, entry.period_to)):
        message = f"{IMPORTS_FILE} and {COSTS_FILE} disagree on the import {entry.import_id}"
        raise ValueError(message)
    report = _report(entry.report, COSTS_FILE)
    load_import(session, _import(listed, at.project_id, report), at.act)
    load_cost_import(
        session,
        at.project_id,
        CostImportLoad(
            cost_import_id=cost_import_id,
            import_report_id=entry.import_id,
            imported_at=at.at,
            requested_by=at.account,
            period_from=entry.period_from,
            period_to=entry.period_to,
            created_count=entry.created_count,
            updated_count=entry.updated_count,
            unchanged_count=entry.unchanged_count,
            rejected_count=entry.rejected_count,
            passthrough_columns=tuple(entry.kept_columns),
        ),
    )
    brought = [line.load() for line in costs.costs.lines if line.brought_by(cost_import_id)]
    load_cost_lines(session, at.project_id, cost_import_id, brought, at.act)


def _period(listed: Import) -> tuple[date | None, date | None]:
    """Give the period an import listed declared, each bound possibly missing."""
    return (
        None if listed.period_from is None else listed.period_from.root,
        None if listed.period_to is None else listed.period_to.root,
    )


def _exclude(session: Session, costs: Costs, made: CostLineExcluded, at: CostWrite) -> None:
    """Take a line out of the tracked scope at the instant of its event, for its reason."""
    line = costs.line(made.document, made.item)
    if line.excluded != Exclusion(excluded_at=at.at, reason=made.reason):
        message = f"{COSTS_FILE} does not exclude the line {made.document} as the chronology does"
        raise ValueError(message)
    load_exclusion(session, at.project_id, line.cost_line_id, made.reason, at.act)


def _expire(session: Session, costs: Costs, import_id: UUID, at: CostWrite) -> None:
    """Write an extraction analysed at the instant of its event, expired without being applied."""
    if costs.expired.import_id.root != import_id:
        message = f"{EXPIRED_FILE} is not the import {import_id} the chronology expires"
        raise ValueError(message)
    listed = costs.listing(import_id, "expired")
    load_import(
        session, _import(listed, at.project_id, _report(costs.expired.report, EXPIRED_FILE)), at.act
    )
