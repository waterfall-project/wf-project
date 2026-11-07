# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of the projects of the witness, and the events of their chronology.

``revisions.json`` for the revisions, ``project_state_transitions.json`` for their order: the
revision 100 opened (Created to Pricing), its marking, the 101 opened, the designation of 100
tried and refused, the code entered, the 101 marked, the 102 opened. The witness abandons none.

A write of the chronology names its project by its code (``projects.json``) and its revision by
the number the identifiers of the witness end with (``01926f3a-…-000000000100``). The revisions
are opened by the rules of the opening (#1402) and marked by the very transaction of the worker
(``load_marking``), in the order of the chronology, at the instant of the loading until US-0990/L2
imposes the chronology's. A marked revision bears the name of version and the description of
``revisions.json``, the object the contract answers, which the chronology only orders: its
``version_name`` is the name of the event, « Offre v1.0 ». A write this slice
does not know — the designation and the code, US-0980's — changes nothing of what the openings and
the markings judge, and is passed over.

Filled by US-0960 and US-0970; US-0980 adds the designation and the code.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import Project, Revision
from waterfall.core.revisions.interface import load_marking, load_revision, revisions_present
from waterfall.platform.errors import FieldError, UnprocessableError
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

REVISIONS_FILE = "revisions.json"
PROJECTS_FILE = "projects.json"
CHRONOLOGY_FILE = "project_state_transitions.json"
OPENED = "revision_opened"
MARKED = "revision_marked"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_REQUIRED = "VALUE_REQUIRED"


class Revisions(BaseModel):
    """The revisions of the witness, as ``listRevisions`` answers them."""

    items: list[Revision]


class Projects(BaseModel):
    """The projects of the witness, as ``listProjects`` answers them."""

    items: list[Project]


class Write(BaseModel):
    """A write of an event of the chronology: what, in which project, of which revision."""

    kind: str
    project: str
    revision: int | None = None


class Event(BaseModel):
    """An event of the chronology, and what the slice of the projects writes at it."""

    sequence: int
    writes: list[Write]


class Chronology(BaseModel):
    """The events of the witness, in their order (``wftools.mockchronology``)."""

    events: list[Event]


def _numbered(revision: UUID) -> int | None:
    """Give the number an identifier of the witness ends with, ``None`` if it is not a number."""
    last = str(revision).rsplit("-", 1)[1]
    return int(last) if last.isdecimal() else None


@dataclass(frozen=True, slots=True)
class Marking:
    """The name of version and the description a revision of the witness is marked under."""

    version_name: str
    description: str | None


@dataclass(frozen=True, slots=True)
class Step:
    """A write of the chronology this slice makes: a revision opened, or marked (``marking``)."""

    project_id: UUID
    revision_id: UUID
    marking: Marking | None = None


def _marking(revision: Revision) -> Marking:
    """Give what ``revisions.json`` says a revision is marked under; refuse it without a name."""
    if revision.version_name is None:
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError("/version_name", VALUE_REQUIRED),)
        )
    return Marking(revision.version_name.root, revision.description)


def steps(witness: Witness) -> list[Step]:
    """Give the openings and the markings of the chronology, in its order."""
    codes = {
        project.code.root: project.project_id.root
        for project in witness.read(PROJECTS_FILE, Projects).items
        if project.code is not None
    }
    numbered = {
        (revision.project_id.root, _numbered(revision.revision_id.root)): revision
        for revision in witness.read(REVISIONS_FILE, Revisions).items
    }
    walked: list[Step] = []
    for event in witness.read(CHRONOLOGY_FILE, Chronology).events:
        for write in event.writes:
            if write.kind not in {OPENED, MARKED}:
                continue
            project_id = codes[write.project]
            revision = numbered[project_id, write.revision]
            marking = _marking(revision) if write.kind == MARKED else None
            walked.append(Step(project_id, revision.revision_id.root, marking))
    return walked


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    walked = steps(witness)
    imposed = {step.revision_id for step in walked if step.marking is None}
    if is_loaded(imposed, revisions_present(session, imposed)):
        return False
    for step in walked:
        if step.marking is None:
            load_revision(session, step.project_id, step.revision_id, witness.act)
        else:
            marking = step.marking
            load_marking(
                session, step.revision_id, marking.version_name, marking.description, witness.act
            )
    return bool(walked)
