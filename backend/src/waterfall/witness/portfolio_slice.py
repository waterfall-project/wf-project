# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the portfolio of the witness, as ``make mock-data`` describes it (EP-11, US-2770).

``fixtures/witness/portfolio/projects/PRJ-30n.json``, one file per project (``wftools.mockslice``):
the ten projects the witness loads beside PRJ-001 and PRJ-002, each with its tasks, its lines, its
risks and their reviews, its revisions and their markings, its actual costs and its transitions,
every write in the form of the schema of the contract that carries it (``ProjectCreate``,
``NodeCreate``, ``RiskWrite``, ``RiskReviewWrite``, ``ActualCostLine``, ``StateTransition``,
``RevisionCreate``, ``CurrentRevisionMark``), validated by its model: a file that strays stops the
command, nothing written. The slice lives out of the contract, in a directory beside the examples
(``fixtures/witness/``, EP-11, « Ce que le cadrage décide »): this module finds it from the
description (``directory``) and never imports ``wftools``.

The identifiers the description names are the platform's; those it does not — the revisions' main
structures, the own estimate of a risk, its provision line, the nodes of a revision that is not the
last of its project, the exchange that brought an import — are derived from them (``derived``), so
that two loadings give the same ones, as the slices of PRJ-001 do.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import AwareDatetime, RootModel

from waterfall.api.contract.models import (
    ActualCostLine,
    CurrentRevisionMark,
    NodeCreate,
    ProjectCreate,
    ProjectRatio,
    RevisionCreate,
    RiskReviewWrite,
    RiskWrite,
    StateTransition,
)
from waterfall.witness.filling import Strict

if TYPE_CHECKING:
    from pathlib import Path

    from waterfall.witness.description import Witness

PORTFOLIO_PATH = ("witness", "portfolio", "projects")
_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/portfolio")


def derived(kind: str, *parts: object) -> UUID:
    """Give the identifier of what the description does not name: derived from what it does."""
    return uuid5(_NAMESPACE, "/".join((kind, *(str(part) for part in parts))))


class Node(Strict):
    """A task or a line, under the identifier the description gives it, which is its lineage."""

    node_id: UUID
    node: NodeCreate


class Task(Node):
    """A task, with the days it was started and completed on, if it was."""

    started_on: date | None
    completed_on: date | None


class Revision(Strict):
    """A revision: when it is opened, and when it is marked or abandoned, if it is."""

    revision_id: UUID
    opened_at: AwareDatetime
    create: RevisionCreate
    marked_at: AwareDatetime | None
    mark: CurrentRevisionMark | None
    abandoned_at: AwareDatetime | None


class Review(Strict):
    """A review of a risk, after its declaration."""

    at: AwareDatetime
    review: RiskReviewWrite


class Risk(Strict):
    """A risk: declared at an instant, its own estimate, its reviews."""

    risk_id: UUID
    declared_at: AwareDatetime
    risk: RiskWrite
    own_estimate: list[Node]
    reviews: list[Review]


class Import(Strict):
    """An import of actual costs: its entry of the log, its instant, the lines it brought."""

    cost_import_id: UUID
    imported_at: AwareDatetime
    lines: list[ActualCostLine]


class Project(Strict):
    """A project of the slice, and everything the loader writes of it."""

    project_id: UUID
    created_at: AwareDatetime
    project: ProjectCreate
    inflation_rate: ProjectRatio
    win_probability: ProjectRatio
    reference_revision_id: UUID | None
    transitions: list[StateTransition]
    revisions: list[Revision]
    tasks: list[Task]
    lines: list[Node]
    risks: list[Risk]
    imports: list[Import]

    @property
    def code(self) -> str:
        """Give the code the project bears from its creation."""
        code = self.project.code
        if code is None:
            message = f"the project {self.project_id} of the slice has no code"
            raise ValueError(message)
        return code.root

    @property
    def last(self) -> int:
        """Give the number of its last revision, which keeps the identifiers the file names."""
        return len(self.revisions)

    def node(self, number: int, node_id: UUID) -> UUID:
        """Give the identifier of a node in a revision: the file's in the last one, else derived."""
        return node_id if number == self.last else derived("node", number, node_id)

    def planning_start_on(self) -> date:
        """Give the day the planning of its structures starts on: the first task's start."""
        starts = [
            task.node.task.start.date.root
            for task in self.tasks
            if task.node.task is not None and task.node.task.start is not None
        ]
        return min(starts)

    def revision_number(self, revision_id: UUID) -> int:
        """Give the number of a revision of the project, from one; or refuse the file."""
        for number, each in enumerate(self.revisions, start=1):
            if each.revision_id == revision_id:
                return number
        message = f"the project {self.code} names a revision {revision_id} it does not describe"
        raise ValueError(message)

    def moves(self) -> list[tuple[str | None, str, datetime, str | None]]:
        """Give its transitions as the base keeps them: left, taken, instant, reason."""
        return [
            (
                None if each.from_state is None else each.from_state.value,
                each.to_state.value,
                each.occurred_at.root,
                each.reason,
            )
            for each in self.transitions
        ]


@dataclass(frozen=True, slots=True)
class Progress:
    """The state of a task on a day, with the two days it keeps."""

    state: str
    started_on: date | None
    completed_on: date | None


NOT_STARTED, STARTED, COMPLETED = "not_started", "started", "completed"


def progress_on(task: Task, day: date) -> Progress:
    """Give a task's state on a day: completed from its completion, started from its start."""
    if task.completed_on is not None and task.completed_on <= day:
        return Progress(COMPLETED, task.started_on or task.completed_on, task.completed_on)
    if task.started_on is not None and task.started_on <= day:
        return Progress(STARTED, task.started_on, None)
    return Progress(NOT_STARTED, None, None)


def directory(witness: Witness) -> Path:
    """Give where the projects of the slice are: beside the description, not under it."""
    return witness.directory.parent.joinpath(*PORTFOLIO_PATH)


def read(witness: Witness) -> list[Project]:
    """Read the projects of the slice, in the order of their files; a file that strays raises."""
    where = replace(witness, directory=directory(witness))
    names = sorted(path.name for path in where.directory.glob("*.json"))
    if not names:
        message = f"{where.directory} holds no project of the slice of the portfolio"
        raise ValueError(message)
    return [where.read(name, Project) for name in names]


def money(amount: object) -> Decimal:
    """Give an amount of the contract, a string under one root or two, as a decimal."""
    while isinstance(amount, RootModel):
        amount = cast("RootModel[object]", amount).root
    return Decimal(str(amount))
