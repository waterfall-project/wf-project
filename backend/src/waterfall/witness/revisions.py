# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of the projects of the witness, and the events of their chronology.

``revisions.json`` for the revisions, ``project_state_transitions.json`` for their order and their
instants (``timeline``): the revision 100 opened (Created to Pricing), its marking, the 101 opened,
the designation of 100 tried and refused, the code entered, the 101 marked, the 102 opened. The
witness abandons none.

Each write is made through the interface of its module, by the rules of the API, at the instant of
its event (``Act.at``; WF-CYC-0130), its author the platform. The revisions are opened by the rules
of the opening (#1402) and marked by the very transaction of the worker (``load_marking``). A marked
revision bears the name of version and the description of ``revisions.json``, the object the
contract answers, which the chronology only orders: its ``version_name`` must be the one of the
event, « Offre v1.0 ». The designation is tried by the project manager of the witness and is
refused for the lack of tasks, which the loader notes (``witness.designation_refused``) — a
designation that succeeds, or any other refusal, is a defect that stops the command. The code is
entered by the same project manager, through the change of a project. The state a transition
write names is checked against the transitions the writes before it left.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import ContributorList, Project, Revision
from waterfall.core.projects.interface import (
    ProjectChange,
    Viewer,
    list_state_transitions,
    stored_lock_version,
    update_project,
)
from waterfall.core.revisions.interface import (
    ReferenceToDesignate,
    designate_reference,
    load_marking,
    load_revision,
    revisions_present,
)
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    UnprocessableError,
)
from waterfall.platform.logs import get_logger
from waterfall.witness import timeline
from waterfall.witness.description import is_loaded
from waterfall.witness.timeline import (
    CodeEntered,
    DesignationAttempted,
    RevisionMarked,
    RevisionOpened,
    StateTransition,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness
    from waterfall.witness.timeline import Event, Write

REVISIONS_FILE = "revisions.json"
PROJECTS_FILE = "projects.json"
CONTRIBUTORS_FILE = "contributors.json"
MANAGER = "project_manager"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_REQUIRED = "VALUE_REQUIRED"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
NO_TASKS_AND_LINES = "revision_has_tasks_and_lines"

logger = get_logger(__name__)


class Revisions(BaseModel):
    """The revisions of the witness, as ``listRevisions`` answers them."""

    items: list[Revision]


class Projects(BaseModel):
    """The projects of the witness, as ``listProjects`` answers them."""

    items: list[Project]


def _numbered(revision: UUID) -> int | None:
    """Give the number an identifier of the witness ends with, ``None`` if it is not a number."""
    last = str(revision).rsplit("-", 1)[1]
    return int(last) if last.isdecimal() else None


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
            (revision.project_id.root, _numbered(revision.revision_id.root)): revision
            for revision in witness.read(REVISIONS_FILE, Revisions).items
        }
        self.manager = self._manager(witness)

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

    def revision(self, write: RevisionOpened | RevisionMarked | DesignationAttempted) -> Revision:
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
        """Make a write of the chronology at its event's instant; the others are passed over."""
        act = timeline.at(self.witness, event.occurred_at)
        match write:
            case RevisionOpened():
                revision = self.revision(write)
                load_revision(
                    self.session, revision.project_id.root, revision.revision_id.root, act
                )
            case RevisionMarked():
                self._mark(write, act)
            case DesignationAttempted():
                self._designate(write, act)
            case CodeEntered():
                self._enter(write, act)
            case StateTransition():
                self._check(write, event)
            case _:
                pass

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
        """Try the designation of a revision: refused for the lack of tasks, which is noted."""
        revision = self.revision(write)
        project_id = revision.project_id.root
        designated = ReferenceToDesignate(
            revision.revision_id.root, stored_lock_version(self.session, project_id)
        )
        try:
            designate_reference(
                self.session,
                project_id,
                designated,
                act,
                self.manager,
            )
        except ConflictError as refused:
            condition = refused.params.get("missing_condition")
            if refused.code != STATE_FORBIDS_OPERATION or condition != NO_TASKS_AND_LINES:
                raise
            logger.info(
                "witness.designation_refused",
                project=write.project,
                revision=write.revision,
                missing_condition=condition,
            )
            return
        message = f"the designation of revision {write.revision} was not refused"
        raise ValueError(message)

    def _enter(self, write: CodeEntered, act: Act) -> None:
        """Enter the code of a project, through the change of a project by its manager."""
        project_id = self.project(write.project)
        if write.code != write.project:
            message = f"the code {write.code} entered is not the one of {write.project}"
            raise ValueError(message)
        change = ProjectChange({"code": write.code}, stored_lock_version(self.session, project_id))
        update_project(self.session, project_id, change, act, self.manager)

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
    for event, write in timeline.read(witness).writes():
        walk.write(event, write)
    return bool(imposed)
