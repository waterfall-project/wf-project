# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the portfolio of the witness: ten projects, written at the instants they describe.

Called by the slices of the projects (``witness.chronology``) after the march of the events of
PRJ-001, the risks and the amendments of EP-08 among them (EP-11, US-2770). Each project of
``portfolio_slice`` is written by the interfaces of the modules, by the rules of the API, at the
instants its description dates (``Act.at``; WF-CYC-0130), its author the platform, the project
manager of the witness — the contributor of each of them — the viewer of the writes that judge one:

- its creation, with its code (WF-CYC-0030), its inflation rate and the probability of winning;
- a revision opened, the first by the rules of the opening, the next by the copy of the last
  marked; the tasks and the lines of the project written into the first, as ``witness.tasks`` and
  ``witness.estimate_lines`` write those of PRJ-001, and carried by the copies;
- a risk declared in the revision in progress, its own estimate entered as the description gives
  it, and each review of it;
- an import of actual costs, with its entry of the log and the lines it brought;
- a revision marked, by the transaction of the worker (``load_marking``), the states of its tasks
  laid as they stand on the day of the marking — completed from their completion, started from
  their start —; or abandoned;
- the reference designated, which moves the project from Pricing to In progress, its code being
  set; its exit to a terminal state, with its reason.

The events of a project come in the order of their instants, those of the same instant in the order
of the list above, and each project after the one before it. At the end of a project, the
transitions the platform holds are those the description gives, or the file is at fault and the
command stops, nothing written. A project is a contributor of nobody but the project manager of the
witness; no revision of a project is written by an account that is not him.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from waterfall.api.contract.models import ContributorList, ImportReport, PaymentDelayDays2, Uuid
from waterfall.core.costs.interface import (
    CostImportLoad,
    CostLineLoad,
    load_cost_import,
    load_cost_lines,
)
from waterfall.core.exchanges.interface import ImportLoad, load_import
from waterfall.core.planning.interface import (
    Place,
    ProgressLoad,
    Writer,
    load_progress,
    task_of_lineage,
)
from waterfall.core.projects.interface import (
    TERMINAL,
    ContributorEntry,
    ContributorsLoad,
    ExitRequest,
    ExitState,
    ProjectChange,
    ProjectDraft,
    ProjectLoad,
    Viewer,
    exit_project,
    list_state_transitions,
    load_contributors,
    load_project,
    projects_present,
    stored_lock_version,
    update_project,
)
from waterfall.core.resource_settings.interface import DAYS
from waterfall.core.revisions.interface import (
    CopyImposed,
    ReferenceToDesignate,
    RevisionToAbandon,
    abandon_revision,
    aimed_structure,
    create_project_partitions,
    designate_reference,
    load_marking,
    load_revision,
    read_revision,
)
from waterfall.core.risks.interface import (
    RiskEntry,
    RiskLoad,
    RiskReviewEntry,
    load_risk,
    read_risk,
    review_risk,
)
from waterfall.witness import calendars, portfolio_slice
from waterfall.witness.description import is_loaded
from waterfall.witness.estimate_lines import write_lines
from waterfall.witness.filling import Duration, LineRow, Moment, TaskRow
from waterfall.witness.portfolio_slice import NOT_STARTED, Project, derived, money, progress_on
from waterfall.witness.tasks import write_tasks

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness
    from waterfall.witness.portfolio_slice import Import, Node, Review, Revision, Risk

type Week = tuple[Decimal, ...]
CONTRIBUTORS_FILE = "contributors.json"
MANAGER = "project_manager"
ACTUAL_COSTS = "actual_costs"
# What an import of the exchanges keeps of its analysis: five minutes before it is applied, for a
# day (``load_import``).
ANALYSED_BEFORE = timedelta(minutes=5)
EXPIRES_AFTER = timedelta(hours=24)
# The order of the events of one instant.
CREATED, OPENED, DECLARED, REVIEWED, IMPORTED, MARKED, ABANDONED, DESIGNATED, EXITED = range(9)
IN_PROGRESS = "in_progress"
EXIT_STATE: TypeAdapter[ExitState] = TypeAdapter(ExitState)
ONE_DAY = Duration(value=Decimal(1), unit="d")


def partition(session: Session, witness: Witness) -> None:
    """Create the partitions of the projects of the slice, first thing of the transaction.

    As ``projects.partition`` does for PRJ-001 and PRJ-002 (#2937), and nothing on a platform that
    holds one of the projects of the slice already.
    """
    imposed = sorted(project.project_id for project in portfolio_slice.read(witness))
    if projects_present(session, imposed):
        return
    for project_id in imposed:
        create_project_partitions(session, project_id)


def load(session: Session, witness: Witness) -> bool:
    """Write the slice unless the platform holds it; tell whether it wrote."""
    described = portfolio_slice.read(witness)
    imposed = {project.project_id for project in described}
    if is_loaded(imposed, projects_present(session, imposed)):
        return False
    manager, week = _manager(witness), default_week(witness)
    for project in described:
        write_project(session, witness.act, project, (manager, week))
    return True


def write_project(session: Session, act: Act, project: Project, who: tuple[Viewer, Week]) -> None:
    """Write a project described as those of the slice, its manager and the hours of its week given.

    The projects the reference set draws are written so too (US-2950).
    """
    _Writing(session, act, project, who).run()


def default_week(witness: Witness) -> Week:
    """Give the hours of work of each day of the week on the default calendar of the witness."""
    for each in witness.read(calendars.FILE, calendars.Calendars).items:
        if each.is_default:
            return tuple(Decimal(getattr(each.weekly_hours, day).root.root) for day in DAYS)
    message = f"{calendars.FILE} names no default calendar"
    raise ValueError(message)


def _manager(witness: Witness) -> Viewer:
    """Give the project manager of the witness: the contributor of each project of the slice."""
    for item in witness.read(CONTRIBUTORS_FILE, ContributorList).items:
        if item.kind.value == MANAGER and item.is_active:
            return Viewer(item.user_id.root, ())
    message = f"{CONTRIBUTORS_FILE} names no active project manager"
    raise ValueError(message)


@dataclass(frozen=True, slots=True)
class _Event:
    """A write of a project: its instant, its place among those of the instant, and what it does."""

    at: datetime
    rank: int
    write: Callable[[Act], None]


class _Writing:
    """The writes of one project, in the order of its events."""

    def __init__(
        self, session: Session, act: Act, project: Project, who: tuple[Viewer, Week]
    ) -> None:
        self.session = session
        self.act = act
        self.project = project
        self.manager, self.week = who
        # The revision in progress and its number; the state of each task as it was last laid.
        self.current: tuple[UUID, int] | None = None
        self.laid: dict[UUID, str] = {}

    def run(self) -> None:
        """Write the events of the project in order, then check its transitions against its file."""
        for event in sorted(self._events(), key=lambda each: (each.at, each.rank)):
            event.write(replace(self.act, at=event.at))
        held = [
            (each.from_state, each.to_state, each.occurred_at, each.reason)
            for each in list_state_transitions(self.session, self.project.project_id)
        ]
        if held != self.project.moves():
            message = f"the transitions of {self.project.code} are not those its file gives"
            raise ValueError(message)

    def _events(self) -> list[_Event]:
        """Give every write of the project, with its instant."""
        project = self.project
        found = [_Event(project.created_at, CREATED, self._create)]
        for number, revision in enumerate(project.revisions, start=1):
            found.append(_Event(revision.opened_at, OPENED, self._opening(number, revision)))
            if revision.marked_at is not None:
                found.append(_Event(revision.marked_at, MARKED, self._marking(number, revision)))
            if revision.abandoned_at is not None:
                found.append(_Event(revision.abandoned_at, ABANDONED, self._abandon(revision)))
        for risk in project.risks:
            found.append(_Event(risk.declared_at, DECLARED, self._declaration(risk)))
            found.extend(
                _Event(each.at, REVIEWED, self._review(risk, each)) for each in risk.reviews
            )
        found.extend(
            _Event(each.imported_at, IMPORTED, self._import(each)) for each in project.imports
        )
        for transition in project.transitions:
            state = transition.to_state.value
            instant = transition.occurred_at.root
            if state == IN_PROGRESS:
                found.append(_Event(instant, DESIGNATED, self._designation))
            elif state in TERMINAL:
                exit_ = self._exit(EXIT_STATE.validate_python(state), transition.reason)
                found.append(_Event(instant, EXITED, exit_))
        return found

    def _writer(self, act: Act) -> Writer:
        """Give the writer of a risk: the platform, at the instant of the event."""
        return Writer(act, None)

    def _create(self, act: Act) -> None:
        """Create the project with its code, its contributor, its inflation rate and probability."""
        project, draft = self.project, self.project.project
        client = None if draft.client is None else draft.client.root
        created = ProjectDraft(draft.label, draft.description, client, project.code)
        load_project(self.session, ProjectLoad(project.project_id, created), act)
        entries = (ContributorEntry(self.manager.user_id, MANAGER),)
        load_contributors(self.session, ContributorsLoad(project.project_id, entries, 1), act)
        values = {
            "inflation_rate": project.inflation_rate.root,
            "win_probability": project.win_probability.root,
        }
        counter = stored_lock_version(self.session, project.project_id)
        update_project(
            self.session, project.project_id, ProjectChange(values, counter), act, self.manager
        )

    def _imposed(self, number: int, revision: Revision) -> CopyImposed:
        """Give the identifiers the copy into a revision imposes: those the description names."""
        project = self.project
        main = derived("main", revision.revision_id)
        rows = {
            each.node_id: project.node(number, each.node_id)
            for each in (*project.tasks, *project.lines)
        }
        structures = {
            derived("own", each.risk_id): derived("own", each.risk_id, number)
            for each in project.risks
        }
        nodes = {main: rows}
        for risk in project.risks:
            nodes[derived("own", risk.risk_id, number)] = {
                each.node_id: project.node(number, each.node_id) for each in risk.own_estimate
            }
        return CopyImposed(main, structures, nodes)

    def _opening(self, number: int, revision: Revision) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            project = self.project
            revision_id = revision.revision_id
            load_revision(
                self.session, project.project_id, revision_id, act, self._imposed(number, revision)
            )
            self.current = (revision_id, number)
            if number == 1:
                self._fill(act)

        return write

    def _place(self) -> Place:
        """Give the main structure of the revision in progress."""
        project_id = self.project.project_id
        revision_id, _ = self._in_progress()
        structure_id = aimed_structure(self.session, project_id, revision_id, None)
        if structure_id is None:
            message = f"the revision {revision_id} of {self.project.code} holds no main structure"
            raise ValueError(message)
        return Place(project_id, revision_id, structure_id)

    def _in_progress(self) -> tuple[UUID, int]:
        if self.current is None:
            message = f"{self.project.code} is written without a revision in progress"
            raise ValueError(message)
        return self.current

    def _fill(self, act: Act) -> None:
        """Write the tasks, then the lines, of the project into its first revision."""
        project = self.project
        place = self._place()
        number, start = 1, project.planning_start_on()
        tasks = [
            _task_row(
                each, (number, position, project.node(number, each.node_id)), (start, self.week)
            )
            for position, each in enumerate(project.tasks, start=1)
        ]
        write_tasks(self.session, place, (start, tasks), lambda row: row.node_id, act)
        lines = _line_rows(project.lines, number, project.node)
        write_lines(self.session, place, (lines, lambda row: row.node_id), act)

    def _lay_progress(self, day: date, act: Act) -> None:
        """Lay the state of each task of the revision in progress as it stands on a day."""
        project_id = self.project.project_id
        place = self._place()
        for task in self.project.tasks:
            state = progress_on(task, day)
            if self.laid.get(task.node_id, NOT_STARTED) == state.state:
                continue
            found = task_of_lineage(self.session, project_id, place.structure_id, task.node_id)
            if found is None:
                message = f"{self.project.code} holds no task {task.node_id} to lay a state on"
                raise ValueError(message)
            laid = ProgressLoad(found.node_id, state.state, state.started_on, state.completed_on)
            load_progress(self.session, project_id, laid, act)
            self.laid[task.node_id] = state.state

    def _marking(self, number: int, revision: Revision) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            if revision.mark is None:
                message = f"{self.project.code} marks its revision {number} without a name"
                raise ValueError(message)
            self._lay_progress(act.at.date(), act)
            mark = revision.mark
            load_marking(
                self.session, revision.revision_id, mark.version_name, mark.description, act
            )
            self.current = None

        return write

    def _abandon(self, revision: Revision) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            project_id = self.project.project_id
            read = read_revision(self.session, project_id, revision.revision_id, self.manager)
            abandoned = RevisionToAbandon(revision.revision_id, read.lock_version)
            abandon_revision(self.session, project_id, abandoned, act, self.manager)
            self.current = None

        return write

    def _designation(self, act: Act) -> None:
        """Designate the reference revision, which moves the project to In progress."""
        project, reference = self.project, self.project.reference_revision_id
        if reference is None:
            message = f"{project.code} moves to In progress without a reference revision"
            raise ValueError(message)
        counter = stored_lock_version(self.session, project.project_id)
        designated = ReferenceToDesignate(reference, counter, act.at)
        designate_reference(self.session, project.project_id, designated, act, self.manager)

    def _exit(self, state: ExitState, reason: str | None) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            project_id = self.project.project_id
            request = ExitRequest(state, reason, stored_lock_version(self.session, project_id))
            exit_project(self.session, project_id, request, act, self.manager)

        return write

    def _declaration(self, risk: Risk) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            project, place = self.project, self._place()
            _, number = self._in_progress()
            task = (
                None
                if risk.risk.provision_task_id is None
                else task_of_lineage(
                    self.session,
                    project.project_id,
                    place.structure_id,
                    risk.risk.provision_task_id.root,
                )
            )
            if task is None:
                message = f"the risk {risk.risk_id} of {project.code} names no task to bear it"
                raise ValueError(message)
            written = risk.risk
            entry = RiskEntry(
                label=written.label,
                probability=money(written.probability),
                description=written.description,
                mitigation_notes=written.mitigation_notes,
                provision_cost_category_id=_root(written.provision_cost_category_id),
                provision_subproject_id=_root(written.provision_subproject_id),
                provision_task_id=task.node_id,
            )
            own = derived("own", risk.risk_id)
            load = RiskLoad(entry, risk.risk_id, own, derived("provision", risk.risk_id))
            load_risk(self.session, project.project_id, load, self._writer(act), self.manager)
            self._own_estimate(risk, own, number, act)

        return write

    def _own_estimate(self, risk: Risk, structure_id: UUID, number: int, act: Act) -> None:
        """Enter the own estimate of a risk: its task, then its line, as the description gives."""
        project = self.project
        revision_id, _ = self._in_progress()
        place = Place(project.project_id, revision_id, structure_id)
        start = project.planning_start_on()
        tasks = [
            _task_row(each, (number, 1, project.node(number, each.node_id)), (start, self.week))
            for each in risk.own_estimate
            if each.node.task is not None
        ]
        write_tasks(self.session, place, (start, tasks), lambda row: row.node_id, act)
        lines = _line_rows(risk.own_estimate, number, project.node)
        write_lines(self.session, place, (lines, lambda row: row.node_id), act)

    def _review(self, risk: Risk, review: Review) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            project_id = self.project.project_id
            revision_id, _ = self._in_progress()
            read = read_risk(self.session, project_id, risk.risk_id, revision_id, self.manager)
            retained = review.review
            entry = RiskReviewEntry(
                risk.risk_id, money(retained.probability), retained.state.value, read.lock_version
            )
            review_risk(self.session, project_id, entry, self._writer(act), self.manager)

        return write

    def _import(self, imported: Import) -> Callable[[Act], None]:
        def write(act: Act) -> None:
            project_id = self.project.project_id
            lines = imported.lines
            first = min(each.document_date.root for each in lines)
            last = max(each.document_date.root for each in lines)
            exchange = derived("import", imported.cost_import_id)
            opened = act.at - ANALYSED_BEFORE
            loaded = ImportLoad(
                import_id=exchange,
                project_id=project_id,
                kind=ACTUAL_COSTS,
                filename=f"{lines[0].document_number}.xlsx",
                period_from=first,
                period_to=last,
                report=_report(imported),
                created_at=opened,
                expires_at=opened + EXPIRES_AFTER,
            )
            requested = replace(act, author=self.manager.user_id)
            load_import(self.session, loaded, requested)
            logged = CostImportLoad(
                cost_import_id=imported.cost_import_id,
                import_report_id=exchange,
                imported_at=act.at,
                requested_by=self.manager.user_id,
                period_from=first,
                period_to=last,
                created_count=len(lines),
                updated_count=0,
                unchanged_count=0,
                rejected_count=0,
            )
            load_cost_import(self.session, project_id, logged)
            brought = [
                CostLineLoad(
                    cost_line_id=each.cost_line_id.root,
                    document_number=each.document_number,
                    document_item=each.document_item,
                    document_date=each.document_date.root,
                    amount=money(each.amount),
                    subproject_code=None
                    if each.subproject_code is None
                    else each.subproject_code.root,
                    passthrough=each.passthrough,
                )
                for each in lines
            ]
            load_cost_lines(self.session, project_id, imported.cost_import_id, brought, requested)

        return write


def _root(value: Uuid | None) -> UUID | None:
    """Give the identifier a nullable identifier of the contract holds."""
    return None if value is None else value.root


def _report(imported: Import) -> dict[str, object]:
    """Give the analysis an import is applied after: every line added, none refused."""
    differences: list[object] = [
        {
            "change": "added",
            "target": "actual_cost_line",
            "lineage_id": None,
            "label": each.document_number,
            "document_item": each.document_item,
            "predecessor_label": None,
            "fields": [],
        }
        for each in imported.lines
    ]
    report: dict[str, object] = {
        "format_version": None,
        "read_count": len(imported.lines),
        "unchanged_count": 0,
        "rejected": [],
        "refusals": [],
        "differences": differences,
        "ignored": [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": [],
        "unknown_wbs_elements": [],
        "unit_constants": None,
        "calendar_gap": None,
    }
    return ImportReport.model_validate(report).model_dump(mode="json", exclude_unset=True)


def _task_row(node: Node, where: tuple[int, int, UUID], when: tuple[date, Week]) -> TaskRow:
    """Give a task of the description as the planning loads it, in a revision it is written in.

    A task of the project is in manual mode, from its start at the first hour of its day to the
    close of its finish — the hours of that day on the default calendar —, and lasts the days that
    calendar works between them; the task of the own estimate of a risk is an automatic one, of a
    day, which the engine places from the planning start. It is written not started: the states
    are laid before each marking (``_Writing._lay_progress``).
    """
    number, position, node_id = where
    planning_start, week = when
    facet = node.node.task
    if facet is None:
        message = f"the node {node.node_id} is no task"
        raise ValueError(message)
    manual = facet.start is not None and facet.finish is not None
    if facet.start is None or facet.finish is None:
        day = ends = planning_start
        duration = ONE_DAY
    else:
        day, ends = facet.start.date.root, facet.finish.date.root
        duration = Duration(value=Decimal(_working_days(day, ends, week)), unit="d")
    return TaskRow(
        revision=number,
        node_id=node_id,
        lineage_id=node.node_id,
        parent_lineage_id=None,
        position=position,
        label=facet.label,
        description=facet.description,
        is_summary=False,
        is_milestone=False,
        scheduling_mode="manual" if manual else "automatic",
        duration=duration,
        start=Moment(date=day, hours=Decimal(0)),
        finish=Moment(date=ends, hours=week[ends.weekday()]),
        order_item_id=None,
        work_package_id=None,
        predecessors=[],
        progress=NOT_STARTED,
        started_on=None,
        completed_on=None,
        inscriptions=[],
    )


def _working_days(start: date, finish: date, week: Week) -> int:
    """Count the days the calendar works between two days, both included.

    A calendar is seven numbers of hours and no public holiday (WF-REF-0110): nothing else to count.
    """
    days = (start + timedelta(days=each) for each in range((finish - start).days + 1))
    return sum(1 for each in days if week[each.weekday()] > 0)


def _line_rows(
    nodes: list[Node], number: int, identified: Callable[[int, UUID], UUID]
) -> list[LineRow]:
    """Give the lines of a list of nodes as the estimate loads them, ranked within their task."""
    ranks: dict[UUID, int] = {}
    found: list[LineRow] = []
    for each in nodes:
        entry = each.node.estimate_line
        if entry is None or each.node.parent_id is None:
            continue
        parent = each.node.parent_id.root
        ranks[parent] = ranks.get(parent, 0) + 1
        found.append(
            LineRow(
                revision=number,
                node_id=identified(number, each.node_id),
                lineage_id=each.node_id,
                task_lineage_id=parent,
                position=ranks[parent],
                label=entry.label or "",
                cost_category_id=_required(entry.cost_category_id, each.node_id),
                resource_role_id=_root(entry.resource_role_id),
                quantity=money(entry.quantity),
                hours=None if entry.hours is None else money(entry.hours),
                unit_disbursement=(
                    None if entry.unit_disbursement is None else money(entry.unit_disbursement)
                ),
                payment_delay_days=_delay(entry.payment_delay_days),
                subproject_id=_root(entry.subproject_id),
            )
        )
    return found


def _required(value: Uuid | None, node_id: UUID) -> UUID:
    """Give the identifier of a category a line of the description must bear."""
    found = _root(value)
    if found is None:
        message = f"the line {node_id} of the slice names no cost category"
        raise ValueError(message)
    return found


def _delay(value: PaymentDelayDays2 | None) -> int:
    """Give a payment delay of the contract in days: none is nought."""
    return 0 if value is None else value.root
