# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chronology of the witness, as ``make mock-data`` exports it, read and validated.

``project_state_transitions.json`` (US-0990/L1, ``wftools.mockchronology``): the events of the
witness in their order, each with its instant and what the slice of the projects writes at it. The
back reads it with a model of its own and never imports ``wftools``: a file that strays from the
model (a kind it does not know, a field missing or beyond, an instant without a zone, events out of
order) stops the command, nothing written (WF-CYC-0130).

A write names its project by its code (``projects.json``) and its revision by the number the
identifiers of the witness end with (``01926f3a-…-000000000100``).
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Iterator

    from waterfall.api.contract.models import Project
    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness

CHRONOLOGY_FILE = "project_state_transitions.json"
State = Literal["created", "pricing", "in_progress", "completed", "lost", "abandoned"]


class _Strict(BaseModel):
    """A model of the file: no field beyond those it names."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProjectCreated(_Strict):
    """The project created, in the state Created."""

    kind: Literal["project_created"]
    project: str


class RevisionOpened(_Strict):
    """A revision opened."""

    kind: Literal["revision_opened"]
    project: str
    revision: int


class RevisionMarked(_Strict):
    """A revision marked under a name of version."""

    kind: Literal["revision_marked"]
    project: str
    revision: int
    version_name: str


class DesignationAttempted(_Strict):
    """The designation of a revision as the reference, and the refusal it is met with."""

    kind: Literal["designation_attempted"]
    project: str
    revision: int
    refused: Literal["no_task"]


class CodeEntered(_Strict):
    """The code of the project entered."""

    kind: Literal["code_entered"]
    project: str
    code: str


class StateTransition(_Strict):
    """The project moved from a state to another, by what is written before it."""

    kind: Literal["state_transition"]
    project: str
    from_state: State = Field(alias="from")
    to_state: State = Field(alias="to")


type Write = Annotated[
    ProjectCreated
    | RevisionOpened
    | RevisionMarked
    | DesignationAttempted
    | CodeEntered
    | StateTransition,
    Field(discriminator="kind"),
]


class Event(_Strict):
    """An event of the witness: its place, its instant, its label, and what it writes."""

    sequence: int
    occurred_at: AwareDatetime
    what: str
    writes: list[Write]


class Chronology(_Strict):
    """The events of the witness, numbered from 1 and in the order of their instants."""

    events: list[Event]

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        """Refuse events out of order, and a chronology that creates no project."""
        for number, event in enumerate(self.events, start=1):
            if event.sequence != number:
                message = f"event {number} is numbered {event.sequence}"
                raise ValueError(message)
        for before, after in zip(self.events, self.events[1:], strict=False):
            if before.occurred_at >= after.occurred_at:
                message = f"event {after.sequence} does not come after event {before.sequence}"
                raise ValueError(message)
        if not any(isinstance(write, ProjectCreated) for _, write in self.writes()):
            message = "no event creates a project"
            raise ValueError(message)
        return self

    def writes(self) -> Iterator[tuple[Event, Write]]:
        """Give each write with its event, in the order of the chronology."""
        for event in self.events:
            for write in event.writes:
                yield event, write

    def created_at(self, code: str) -> AwareDatetime:
        """Give the instant a project is created at: its own, else the first creation's.

        The chronology dates the project of the witness alone; the other project, which has no
        event, is created at the same instant, so that two loadings agree on it.
        """
        created = {
            write.project: event.occurred_at
            for event, write in self.writes()
            if isinstance(write, ProjectCreated)
        }
        return created.get(code, min(created.values()))


def read(witness: Witness) -> Chronology:
    """Read the chronology the directory of the witness holds; a file that strays raises."""
    return witness.read(CHRONOLOGY_FILE, Chronology)


def at(witness: Witness, instant: AwareDatetime) -> Act:
    """Give the act of the platform at an instant the chronology imposes."""
    return replace(witness.act, at=instant)


def created(witness: Witness, project: Project) -> Act:
    """Give the act of the platform at the instant the chronology creates a project."""
    code = "" if project.code is None else project.code.root
    return at(witness, read(witness).created_at(code))
