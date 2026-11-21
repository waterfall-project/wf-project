# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the fillers of a structure of the witness — its tasks, its lines — read alike.

The files they read (``witness_tasks.json``, ``witness_lines.json``, and the own estimates of
``witness_risks.json`` and the amendments of ``witness_amendments.json``, US-2650/L1) are read by
strict models, and name the revision they belong to by an identifier that ends with its number; the
node of a task or a line in a revision other than the one in progress is derived from the file's
(US-1570/L2, #2701).

A structure is filled from the rows a revision of the description gives (``Filling``): the main
structure of that revision, or an amendment, which takes the rows of a revision and changes some of
them (``Changes``), under the identifiers the examples name, the others derived from its own and the
lineage; and the nodes the occurrence of a risk grafts later are left out of the revision they come
into, which receives them from the occurrence (US-2650/L1).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict

from waterfall.core.planning.scheduling import DurationUnit, LagUnit

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from waterfall.api.contract.models import Revision
    from waterfall.platform.audit import Act

# The namespace the nodes of an amendment of the witness are derived in, by its identifier and the
# lineage of the node: its tasks and its lines alike, whose lineages are not shared.
_AMENDMENT_NAMESPACE = uuid5(NAMESPACE_URL, "https://waterfall.example/witness/amendment_node")


class Strict(BaseModel):
    """A part of a file of the witness: every key it holds is read, none is missing."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class _Noded(BaseModel):
    """A task or a line of a file of the witness, read for its revision, node and lineage alone."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    revision: int
    node_id: UUID
    lineage_id: UUID


class Nodes(BaseModel):
    """The nodes of a file of the tasks or of the lines of the witness, every revision's."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    tasks: list[_Noded] = []
    lines: list[_Noded] = []

    def rows(self) -> list[_Noded]:
        """Give the tasks and the lines the file holds."""
        return [*self.tasks, *self.lines]


class Duration(Strict):
    """A duration: a value and its unit."""

    value: Decimal
    unit: DurationUnit


class Lag(Strict):
    """A lag: a value and its unit."""

    value: Decimal
    unit: LagUnit


class Moment(Strict):
    """A start or a finish: a day and the hours of work elapsed that day."""

    date: date
    hours: Decimal


class LinkRow(Strict):
    """A link to a predecessor, by its lineage."""

    predecessor_lineage_id: UUID
    link_type: str
    lag: Lag


class Inscription(Strict):
    """An inscription of a task of the witness, as the description writes it."""

    kind: str
    timeline_id: UUID | None


class TaskRow(Strict):
    """A task of a structure, as the description writes it (``witness_tasks.json``)."""

    revision: int
    node_id: UUID
    lineage_id: UUID
    parent_lineage_id: UUID | None
    position: int
    label: str
    description: str | None
    is_summary: bool
    is_milestone: bool
    scheduling_mode: str
    duration: Duration
    start: Moment
    finish: Moment
    order_item_id: UUID | None
    work_package_id: UUID | None
    predecessors: list[LinkRow]
    progress: str
    started_on: date | None
    completed_on: date | None
    inscriptions: list[Inscription]


class LineRow(Strict):
    """A line of a structure, as the description writes it: its place, what it is entered with."""

    revision: int
    node_id: UUID
    lineage_id: UUID
    task_lineage_id: UUID
    position: int
    label: str
    cost_category_id: UUID
    resource_role_id: UUID | None
    quantity: Decimal
    hours: Decimal | None
    unit_disbursement: Decimal | None
    payment_delay_days: int
    subproject_id: UUID | None


class Tasks(BaseModel):
    """The tasks of the file of the tasks, every revision's, read without its revisions."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    tasks: list[TaskRow]


def number_of(revision_id: UUID) -> int | None:
    """Give the number an identifier of the witness ends with, ``None`` if it is not a number."""
    last = str(revision_id).rsplit("-", 1)[1]
    return int(last) if last.isdecimal() else None


def node_identifier(namespace: UUID, revision: int, file_node: UUID, current: int) -> UUID:
    """Give the identifier of a node in its revision: the file's in the one in progress.

    In another revision it is derived from the file's, in the namespace of the slice, so that two
    loadings give the same one.
    """
    if revision == current:
        return file_node
    return uuid5(namespace, f"{revision}/{file_node}")


def amendment_node(structure_id: UUID, lineage_id: UUID, named: Mapping[UUID, UUID]) -> UUID:
    """Give the identifier of a node of an amendment: the one the examples name, else derived."""
    found = named.get(lineage_id)
    if found is not None:
        return found
    return uuid5(_AMENDMENT_NAMESPACE, f"{structure_id}/{lineage_id}")


@dataclass(frozen=True, slots=True)
class Changes:
    """What an amendment changes of the rows of the revision it takes.

    Rows added or changed by lineage, lineages removed, and the identifiers of its nodes the
    examples name, by lineage.
    """

    structure_id: UUID
    tasks: tuple[TaskRow, ...]
    lines: tuple[LineRow, ...]
    removed: frozenset[UUID]
    named: Mapping[UUID, UUID]

    def node(self, lineage_id: UUID) -> UUID:
        """Give the identifier of a node of the amendment, by its lineage."""
        return amendment_node(self.structure_id, lineage_id, self.named)


@dataclass(frozen=True, slots=True)
class Filling:
    """A structure of the witness to fill, from the rows a revision of the description gives.

    ``revision`` the revision it belongs to, as ``revisions.json`` describes it, ``act`` the instant
    and the author of its writes; ``rows_of`` the revision whose rows fill it, its own by default;
    ``changes`` what an amendment changes of them, none for a main structure; ``left_out`` the
    lineages written later into it, which the occurrence of a risk grafts (US-2650/L1).
    """

    revision: Revision
    act: Act
    rows_of: int | None = None
    changes: Changes | None = None
    left_out: frozenset[UUID] = field(default_factory=frozenset[UUID])

    @property
    def number(self) -> int | None:
        """Give the number of the revision whose rows fill the structure."""
        if self.rows_of is not None:
            return self.rows_of
        return number_of(self.revision.revision_id.root)

    @property
    def structure_id(self) -> UUID | None:
        """Give the structure filled: an amendment, or none for the main structure."""
        return None if self.changes is None else self.changes.structure_id

    def tasks(self, described: Iterable[TaskRow]) -> list[TaskRow]:
        """Give the tasks the structure holds, from those of its revision, in their order.

        A task an amendment changes replaces the revision's, one it adds comes after; a task of
        an amendment bears no lot, no post and no inscription, the main structure's alone
        (WF-PLA-0170).
        """
        changes = self.changes
        kept = [each for each in described if each.lineage_id not in self.left_out]
        if changes is None:
            return kept
        changed = {each.lineage_id: each for each in changes.tasks}
        held = {each.lineage_id for each in kept}
        rows = [
            changed.get(each.lineage_id, each)
            for each in kept
            if each.lineage_id not in changes.removed
        ]
        rows.extend(each for each in changes.tasks if each.lineage_id not in held)
        detached: dict[str, object] = {
            "order_item_id": None,
            "work_package_id": None,
            "inscriptions": [],
        }
        return [each.model_copy(update=detached) for each in rows]

    def lines(self, described: Iterable[LineRow]) -> list[LineRow]:
        """Give the lines the structure holds, from those of its revision, in their order."""
        changes = self.changes
        kept = [each for each in described if each.lineage_id not in self.left_out]
        if changes is None:
            return kept
        changed = {each.lineage_id: each for each in changes.lines}
        held = {each.lineage_id for each in kept}
        rows = [
            changed.get(each.lineage_id, each)
            for each in kept
            if each.lineage_id not in changes.removed
        ]
        rows.extend(each for each in changes.lines if each.lineage_id not in held)
        return rows
