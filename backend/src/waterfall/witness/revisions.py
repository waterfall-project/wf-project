# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of the projects of the witness, and the events of their chronology.

``revisions.json`` for the revisions, ``project_state_transitions.json`` for their order and their
instants (``timeline``): the revision 100 opened (Created to Pricing), its marking, the 101 opened,
the update of its rates accepted, the designation of 100, the code entered, the 101 marked, the 102
opened. The witness abandons none.

Each write is made through the interface of its module, by the rules of the API, at the instant of
its event (``Act.at``; WF-CYC-0130), its author the platform. The revisions are opened by the rules
of the opening (#1402) and marked by the very transaction of the worker (``load_marking``). A marked
revision bears the name of version and the description of ``revisions.json``, the object the
contract answers, which the chronology only orders: its ``version_name`` must be the one of the
event, « Offre v1.0 ». The update of the rates is accepted at the counter the revision holds
(``apply_rate_update``), for the categories the event names. The designation is made by the project
manager of the witness, at the instant of its event, and must succeed, the lines being loaded: a
refusal, whatever its cause, is a defect that stops the command (``witness.reference_designated``).
The code is entered by the same project manager, with the day the order was received, through the
change of a project, and the project must then have moved from Pricing to In progress at the
instant of the event (WF-CYC-0030). The inflation rate and the win probability of ``project.json``
are given to the project at its creation, before any revision is priced: the amounts of the lines
are those of the rate (WF-PRJ-0040), and the probability is frozen once the project is In progress.
The state a transition write names is checked against the transitions the writes before it left.

The content of a revision is written between its opening and the next event, by the fillers
registered (``register_revision_filler``, EP-06): the tasks (``witness.tasks``), then the lines
(``witness.estimate_lines``), each reconciling what the copy gave the revision with what the witness
describes of it, before its marking comes. From EP-08 (US-2650/L1), the risks and the amendments
are written at their events (``witness.risks``, ``witness.amendments``): the 101 is opened by the
declaration of the risks, its content entered in the amendment 1, whose merge marks it and makes it
the reference — the designation of the offer 100 at the order received stays —; the 102, opened by a
review, takes up the structures of the 101 under the identifiers the examples give them, and the
nodes the occurrence of 752 grafts into it later are left out of its content; the amendment 2 is
updated in it after the last write of its main structure, then entered. The revisions copied, the
amendments opened and the risks declared bear the identifiers of the examples; whatever no example
names is drawn in order (``drawn_in_order``), the same at every loading. The actual costs come
after the lines, at the instants of their events (``witness.costs``, EP-09): the imports applied,
the line excluded and the extraction expired, by the project manager, the account an import is
requested by; their description is checked against the chronology before its first event, so that
one that strays writes nothing at all (``check``). A marking keeps the
indicators of its revision as the worker's does (EP-10): the loader imports their interface
(``loader.EXTENDING``).
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import ContributorList, Project, Revision
from waterfall.core.estimate.interface import RateUpdate, apply_rate_update
from waterfall.core.planning.interface import Place
from waterfall.core.projects.interface import (
    ProjectChange,
    Viewer,
    list_state_transitions,
    stored_lock_version,
    update_project,
)
from waterfall.core.revisions.interface import (
    CopyImposed,
    ReferenceToDesignate,
    designate_reference,
    load_marking,
    load_revision,
    read_revision,
    revisions_present,
)
from waterfall.platform.errors import (
    VALIDATION_FAILED,
    FieldError,
    UnprocessableError,
)
from waterfall.platform.logs import get_logger
from waterfall.platform.registry import Registry
from waterfall.witness import amendments, costs, risks, timeline
from waterfall.witness.description import is_loaded
from waterfall.witness.filling import Filling, Nodes, Tasks, number_of
from waterfall.witness.timeline import (
    AmendmentMerged,
    AmendmentOpened,
    AmendmentRebased,
    CodeEntered,
    CostImportApplied,
    CostLineExcluded,
    DesignationAttempted,
    ProjectCreated,
    RateUpdateApplied,
    RevisionMarked,
    RevisionOpened,
    RiskDeclared,
    RiskOccurred,
    RiskReviewed,
    StateTransition,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness
    from waterfall.witness.timeline import Event, Write

REVISIONS_FILE = "revisions.json"
TASKS_FILE = "witness_tasks.json"
LINES_FILE = "witness_lines.json"
PROJECT_FILE = "project.json"
PROJECTS_FILE = "projects.json"
CONTRIBUTORS_FILE = "contributors.json"
MANAGER = "project_manager"
VALUE_REQUIRED = "VALUE_REQUIRED"
PRICING = "pricing"
IN_PROGRESS = "in_progress"

logger = get_logger(__name__)


# What writes the content of a structure of the witness, in their order: its tasks, then its lines.
_FILLERS: Registry[Callable[[Session, Witness, Filling], None]] = Registry(
    "witness.revision_fillers"
)


def register_revision_filler(
    filler: Callable[[Session, Witness, Filling], None],
) -> Callable[[], None]:
    """Add what writes the content of a structure, after the others; give its removal."""
    return _FILLERS.register(filler)


class Revisions(BaseModel):
    """The revisions of the witness, as ``listRevisions`` answers them."""

    items: list[Revision]


class Projects(BaseModel):
    """The projects of the witness, as ``listProjects`` answers them."""

    items: list[Project]


class _Walk:
    """What the walk of the chronology reads of the description, and writes event by event."""

    def __init__(self, session: Session, witness: Witness) -> None:
        self.session = session
        self.witness = witness
        self.codes = {
            project.code.root: project.project_id.root
            for project in witness.read(PROJECTS_FILE, Projects).items
            if project.code is not None
        }
        self.numbered = {
            (revision.project_id.root, number_of(revision.revision_id.root)): revision
            for revision in witness.read(REVISIONS_FILE, Revisions).items
        }
        self.manager = self._manager(witness)
        self.designated: set[UUID] = set()
        # What the slice of the costs reads of the description, before the first event (``check``).
        self.costs: costs.Costs | None = None
        # The risks and the structures of the witness, and the revision in progress of each
        # project, with its number, which their writes read (US-2650/L1).
        self.risks = risks.Risks.read(witness)
        self.structures = amendments.Structures.read(witness)
        self.current: dict[UUID, tuple[UUID, int]] = {}
        self.declared: set[UUID] = set()
        self._nodes: list[tuple[int, UUID, UUID]] | None = None

    @staticmethod
    def _manager(witness: Witness) -> Viewer:
        """Give the project manager of the witness: he tries the designation and enters the code."""
        for item in witness.read(CONTRIBUTORS_FILE, ContributorList).items:
            if item.kind.value == MANAGER and item.is_active:
                return Viewer(item.user_id.root, ())
        message = f"{CONTRIBUTORS_FILE} names no active project manager"
        raise ValueError(message)

    def project(self, code: str) -> UUID:
        """Give the identifier of a project of the chronology by its code; or refuse the file."""
        if code not in self.codes:
            message = f"the chronology names a project {code} that {PROJECTS_FILE} does not"
            raise ValueError(message)
        return self.codes[code]

    def revision(
        self,
        write: RevisionOpened
        | RevisionMarked
        | RateUpdateApplied
        | DesignationAttempted
        | AmendmentOpened
        | AmendmentMerged
        | AmendmentRebased,
    ) -> Revision:
        """Give the revision of a write, as ``revisions.json`` describes it; or refuse the file."""
        found = self.numbered.get((self.project(write.project), write.revision))
        if found is None:
            message = (
                f"the chronology names a revision {write.revision} that {REVISIONS_FILE} does not"
            )
            raise ValueError(message)
        return found

    def opened(self) -> set[UUID]:
        """Give the identifiers of the revisions the chronology opens."""
        chronology = timeline.read(self.witness)
        return {
            self.revision(write).revision_id.root
            for _, write in chronology.writes()
            if isinstance(write, RevisionOpened)
        }

    def write(self, event: Event, write: Write) -> None:
        """Make each write of the chronology at its event's instant."""
        act = timeline.at(self.witness, event.occurred_at)
        match write:
            case ProjectCreated():
                self._configure(write, act)
            case RevisionOpened():
                self._open(write, act)
            case RiskDeclared() | RiskReviewed() | RiskOccurred():
                self._risk(write, act)
            case AmendmentOpened() | AmendmentMerged() | AmendmentRebased():
                self._amendment(write, act)
            case RevisionMarked():
                self._mark(write, act)
            case RateUpdateApplied():
                self._rates(write, act)
            case DesignationAttempted():
                self._designate(write, act)
            case CodeEntered():
                self._enter(write, act)
            case StateTransition():
                self._check(write, event)
            case CostImportApplied() | CostLineExcluded():
                self._cost(write, act)

    def check(self) -> None:
        """Refuse, before anything is written, a description of the costs the chronology belies.

        The costs come last in the chronology: checked at their events, a description that strays
        was refused only once the whole witness before them had been written, then rolled back.
        """
        for event, write in timeline.read(self.witness).writes():
            if isinstance(write, CostImportApplied | CostLineExcluded):
                if self.costs is None:
                    self.costs = costs.Costs.read(self.witness)
                costs.check(self.costs, write, timeline.at(self.witness, event.occurred_at).at)

    def _fill(self, filling: Filling) -> None:
        """Write the content of a structure, by the fillers registered, in their order."""
        for fill in _FILLERS.entries():
            fill(self.session, self.witness, filling)

    def nodes(self) -> list[tuple[int, UUID, UUID]]:
        """Give the revision, the node and the lineage of every task and line described, once."""
        if self._nodes is None:
            self._nodes = [
                (row.revision, row.node_id, row.lineage_id)
                for name in (TASKS_FILE, LINES_FILE)
                for row in self.witness.read(name, Nodes).rows()
            ]
        return self._nodes

    def lineages(self) -> frozenset[UUID]:
        """Give the lineages of every task and line the witness describes."""
        return frozenset(lineage for _, _, lineage in self.nodes())

    def _imposed(self, project_id: UUID, number: int) -> CopyImposed:
        """Give the identifiers the copy into a revision imposes: those the examples name there.

        The main structure, its nodes by their lineage and the copies of the provision lines; the
        own estimate of each risk, its nodes where the examples read them; each amendment taken up,
        its nodes named or derived from it.
        """
        main = self.structures.main_of(number)
        structures = risks.structure_copies(self.risks, number, number - 1)
        nodes: dict[UUID, dict[UUID, UUID]] = dict(risks.copied_nodes(self.risks, number))
        for row in self.structures.amendments:
            source, copy = row.structure_in(number - 1), row.structure_in(number)
            if source is None or copy is None or copy == source:
                continue
            structures[source] = copy
            changes = row.changes_in(number)
            nodes[copy] = {lineage: changes.node(lineage) for lineage in self.lineages()}
        if main is not None:
            own = {
                **risks.provision_copies(self.risks),
                **self._file_nodes(project_id, number),
            }
            nodes[main] = own
        return CopyImposed(main, structures, nodes)

    def _file_nodes(self, project_id: UUID, number: int) -> dict[UUID, UUID]:
        """Give the identifier of each node the files give a revision, by its lineage.

        Only the revision in progress of the project, the last it has, keeps the files'
        identifiers; another derives its own.
        """
        current = max(
            each for project, each in self.numbered if project == project_id and each is not None
        )
        if number != current:
            return {}
        return {lineage: node for each, node, lineage in self.nodes() if each == number}

    def _open(self, write: RevisionOpened, act: Act) -> None:
        """Open a revision under the identifiers of the witness, then write its content.

        Its main structure, unless an amendment opened in it carries the rows the witness gives
        it (the 101, US-2650/L1), the nodes the occurrence of a risk grafts later left out; then
        the own estimate of each risk declared, as the revision gives it.
        """
        revision = self.revision(write)
        project_id, revision_id = revision.project_id.root, revision.revision_id.root
        imposed = self._imposed(project_id, write.revision)
        load_revision(self.session, project_id, revision_id, act, imposed)
        self.current[project_id] = (revision_id, write.revision)
        if not self.structures.carries(write.revision):
            self._fill(Filling(revision, act, left_out=self.risks.grafted()))
        made = self._made(project_id, act)
        for risk in self.risks.risks:
            if risk.risk_id in self.declared:
                risks.enter_estimate(self.session, risk, made)

    def _made(self, project_id: UUID, act: Act) -> risks.RiskWrite:
        """Give where and by whom a write of a risk is made, in the revision in progress."""
        current = self.current.get(project_id)
        if current is None:
            message = "the chronology writes a risk into a project without a revision in progress"
            raise ValueError(message)
        return risks.RiskWrite(project_id, current, self.manager, act)

    def _risk(self, write: RiskDeclared | RiskReviewed | RiskOccurred, act: Act) -> None:
        """Declare, review or make occur a risk, by the project manager, at its instant."""
        made = self._made(self.project(write.project), act)
        match write:
            case RiskDeclared():
                risks.declare(self.session, self.risks, write, made)
                self.declared.add(write.risk_id)
            case RiskReviewed():
                risks.review(self.session, write, made)
            case RiskOccurred():
                number = made.revision[1]
                tasks = [
                    row
                    for row in self.witness.read(TASKS_FILE, Tasks).tasks
                    if row.revision == number
                ]
                risks.occur(self.session, self.risks, write, made, tasks)

    def _amendment(
        self, write: AmendmentOpened | AmendmentMerged | AmendmentRebased, act: Act
    ) -> None:
        """Open, merge or update an amendment at its instant; enter its content if it is due."""
        revision = self.revision(write)
        project_id, revision_id = revision.project_id.root, revision.revision_id.root
        row = self.structures.named(write.structure_id)
        structure_id = row.structure_in(write.revision)
        if structure_id is None:
            message = f"the amendment {row.label} is not in revision {write.revision}"
            raise ValueError(message)
        place = Place(project_id, revision_id, structure_id)
        match write:
            case AmendmentOpened():
                where = (project_id, revision_id)
                amendments.open_amendment(self.session, row, where, self.lineages(), act)
            case AmendmentMerged():
                amendments.merge_amendment(self.session, place, self._named(write), act)
                self.current.pop(project_id, None)
                return
            case AmendmentRebased():
                amendments.rebase_amendment(self.session, place, act)
        if row.rows_of == write.revision:
            changes = row.changes_in(write.revision)
            self._fill(Filling(revision, act, rows_of=row.rows_of, changes=changes))

    def _named(self, write: AmendmentMerged) -> tuple[str, str | None]:
        """Give the name of version and the description of the revision a merge marks.

        Those of ``revisions.json``, the object the contract answers, whose name must be the one
        of the event.
        """
        revision = self.revision(write)
        if revision.version_name is None:
            raise UnprocessableError(
                VALIDATION_FAILED, fields=(FieldError("/version_name", VALUE_REQUIRED),)
            )
        name = revision.version_name.root
        if name != write.version_name:
            message = f"revision {write.revision} is marked {write.version_name}, not {name}"
            raise ValueError(message)
        return name, revision.description

    def _cost(self, write: CostImportApplied | CostLineExcluded, act: Act) -> None:
        """Make a write of the actual costs at its instant, by the project manager (EP-09).

        An import is requested by an account, which the platform is not: the manager of the
        witness applies the imports and excludes the line, as he enters the code.
        """
        if self.costs is None:
            self.costs = costs.Costs.read(self.witness)
        made = costs.CostWrite(self.project(write.project), self.manager.user_id, act.at)
        costs.write(self.session, self.costs, write, made)

    def _mark(self, write: RevisionMarked, act: Act) -> None:
        revision = self.revision(write)
        if revision.version_name is None:
            raise UnprocessableError(
                VALIDATION_FAILED, fields=(FieldError("/version_name", VALUE_REQUIRED),)
            )
        name = revision.version_name.root
        if name != write.version_name:
            message = f"revision {write.revision} is marked {write.version_name}, not {name}"
            raise ValueError(message)
        load_marking(self.session, revision.revision_id.root, name, revision.description, act)

    def _designate(self, write: DesignationAttempted, act: Act) -> None:
        """Designate a revision the reference, by the project manager, at the instant of the event.

        It must succeed, the tasks and the lines being loaded: a refusal, whatever its cause, is a
        defect of the description that stops the command. The project moves from Pricing to In
        progress once the code is entered (WF-CYC-0030), which ``_enter`` observes.
        """
        revision = self.revision(write)
        project_id = revision.project_id.root
        designated = ReferenceToDesignate(
            revision.revision_id.root, stored_lock_version(self.session, project_id), act.at
        )
        designate_reference(self.session, project_id, designated, act, self.manager)
        self.designated.add(project_id)
        logger.info("witness.reference_designated", project=write.project, revision=write.revision)

    def _rates(self, write: RateUpdateApplied, act: Act) -> None:
        """Accept the update of the rates of a revision in progress, for the categories named."""
        revision = self.revision(write)
        project_id = revision.project_id.root
        revision_id = revision.revision_id.root
        read = read_revision(self.session, project_id, revision_id, self.manager)
        update = RateUpdate(revision_id, read.lock_version, tuple(write.cost_category_ids))
        apply_rate_update(self.session, project_id, update, act)

    def _configure(self, write: ProjectCreated, act: Act) -> None:
        """Give the project the inflation rate and the win probability it is described with.

        By the project manager, at the instant of the creation, before any revision is priced:
        the amounts of the lines are those of the rate (WF-PRJ-0040), and the probability can no
        longer change once the project is in progress. ``project.json`` describes the project of
        the witness alone.
        """
        project_id = self.project(write.project)
        described = self.witness.read(PROJECT_FILE, Project)
        if described.project_id.root != project_id:
            return
        values = {
            "inflation_rate": described.inflation_rate.root,
            "win_probability": described.win_probability.root,
        }
        change = ProjectChange(values, stored_lock_version(self.session, project_id))
        update_project(self.session, project_id, change, act, self.manager)

    def _enter(self, write: CodeEntered, act: Act) -> None:
        """Enter the code of a project, and the day its order was received, by its manager.

        A project whose reference is designated moves from Pricing to In progress by it, at the
        instant of the event: the transitions say so, or the description is at fault.
        """
        project_id = self.project(write.project)
        if write.code != write.project:
            message = f"the code {write.code} entered is not the one of {write.project}"
            raise ValueError(message)
        values: dict[str, object] = {"code": write.code}
        described = self.witness.read(PROJECT_FILE, Project)
        if described.project_id.root == project_id and described.order_received_on is not None:
            values["order_received_on"] = described.order_received_on.root
        change = ProjectChange(values, stored_lock_version(self.session, project_id))
        update_project(self.session, project_id, change, act, self.manager)
        if project_id in self.designated:
            last = list_state_transitions(self.session, project_id)[-1]
            if (last.from_state, last.to_state, last.occurred_at) != (PRICING, IN_PROGRESS, act.at):
                message = f"the code of {write.project} entered did not move it to In progress"
                raise ValueError(message)

    def _check(self, write: StateTransition, event: Event) -> None:
        """Check that the writes before it moved the project as the transition says."""
        last = list_state_transitions(self.session, self.project(write.project))[-1]
        moved = (last.from_state, last.to_state, last.occurred_at)
        if moved != (write.from_state, write.to_state, event.occurred_at):
            moved_to = f"{write.from_state} to {write.to_state}"
            message = f"event {event.sequence}: the project did not move {moved_to}"
            raise ValueError(message)


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    walk = _Walk(session, witness)
    imposed = walk.opened()
    if is_loaded(imposed, revisions_present(session, imposed)):
        return False
    walk.check()
    for event, write in timeline.read(witness).writes():
        walk.write(event, write)
    return bool(imposed)
