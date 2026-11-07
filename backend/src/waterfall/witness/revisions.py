# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revisions of the projects of the witness, and the events of their chronology.

``revisions.json`` for the revisions, ``project_state_transitions.json`` for their order: the
revision 100 opened (Created to Pricing), its marking, the 101 opened, the designation of 100
tried and refused, the code entered, the 101 marked, the 102 opened. The witness abandons none.

A write of the chronology names its project by its code (``projects.json``) and its revision by
the number the identifiers of the witness end with (``01926f3a-…-000000000100``). The revisions
are opened by the rules of the opening (#1402), in the order of the chronology, at the instant of
the loading until US-0990/L2 imposes the chronology's; the walk stops at the first marking, which
US-0970 writes: a revision opened after it would be refused, the one before it being current.

Filled by US-0960; US-0970 adds the markings, US-0980 the designation and the code.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

from waterfall.api.contract.models import Project, Revision
from waterfall.core.revisions.interface import load_revision, revisions_present
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

REVISIONS_FILE = "revisions.json"
PROJECTS_FILE = "projects.json"
CHRONOLOGY_FILE = "project_state_transitions.json"
OPENED = "revision_opened"
# The writes after which the walk stops until their story writes them (US-0970).
UNWRITTEN = frozenset({"revision_marked"})


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


def openings(witness: Witness) -> list[tuple[UUID, UUID]]:
    """Give the revisions the chronology opens, project and revision, until its first marking."""
    codes = {
        project.code.root: project.project_id.root
        for project in witness.read(PROJECTS_FILE, Projects).items
        if project.code is not None
    }
    numbered = {
        (revision.project_id.root, _numbered(revision.revision_id.root)): revision.revision_id.root
        for revision in witness.read(REVISIONS_FILE, Revisions).items
    }
    opened: list[tuple[UUID, UUID]] = []
    for event in witness.read(CHRONOLOGY_FILE, Chronology).events:
        for write in event.writes:
            if write.kind in UNWRITTEN:
                return opened
            if write.kind == OPENED:
                project_id = codes[write.project]
                opened.append((project_id, numbered[project_id, write.revision]))
    return opened


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    opened = openings(witness)
    imposed = {revision for _, revision in opened}
    if is_loaded(imposed, revisions_present(session, imposed)):
        return False
    for project_id, revision_id in opened:
        load_revision(session, project_id, revision_id, witness.act)
    return bool(opened)
