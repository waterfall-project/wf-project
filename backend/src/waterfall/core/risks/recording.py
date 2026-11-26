# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The entries of the risks in the undoable history, private to the module (US-2590/L2).

The declaration, the change of the provision, the review and the deletion of a risk are entries of
the history of their writer (WF-IHM-0110, WF-RIS-0020; ``risk_create``, ``risk_update``,
``risk_review``, ``risk_delete``); the change of its identity, a datum of the project, is not (H-02,
#1782). Each write opens its entry once the revision it writes in is known — created if need be —
and before it locks a structure (``RiskRecording.open``), so that the locks keep the order of
every write: the revision, the stack, the structures, the risk. It then hands the history the risk
as it is before the write, under its locks, and as it is after it (``risk_state``). A writer whose
token carries no session of sign-in has no stack: its write is made, and no entry kept (#2472).

The history keeps a risk as one object, at the counter of the risk (``Risk.lock_version``), which
every write of the risk, of its evaluation or of its own estimate advances: a change another
contributor made since is a conflict. The change of its identity, which no entry restores, advances
it too, and carries the new counter to the entries (``carry_everywhere``): it is no conflict. Its
rows are what an undoing or a redoing brings back (``undoing``): the identity, to create the risk
again; its evaluation in the revision; its reviews there; the task that bears its provision line;
the start of its own estimate and, for a write that creates or deletes the risk, every node of it
and of its base, and the counter of the main structure it retained (``whole``; EP-30). Identifiers,
amounts, days and instants are kept as text.
"""

from contextlib import ExitStack, contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

from sqlalchemy import select

from waterfall.core.history import interface as history
from waterfall.core.history.interface import ObjectState, RecordedChange, UndoStack
from waterfall.core.planning.interface import bearing_of, structure_nodes
from waterfall.core.revisions.interface import (
    aimed_structure,
    differential_base,
    own_estimate_state,
    structure_facts,
)
from waterfall.core.risks.reading import evaluation_of
from waterfall.core.risks.tables import Risk, RiskReview

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue, Recording, Snapshot, UndoneKind
    from waterfall.core.planning.interface import Writer


def text(value: object) -> JsonValue:
    """Give a column as the history keeps it: identifiers, amounts, days and instants as text."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def identifier(row: Mapping[str, JsonValue], name: str) -> UUID | None:
    """Give an identifier a row keeps, none if null."""
    value = row[name]
    return None if value is None else UUID(cast("str", value))


def amount(row: Mapping[str, JsonValue], name: str) -> Decimal:
    """Give an amount or a probability a row keeps."""
    return Decimal(cast("str", row[name]))


def instant(row: Mapping[str, JsonValue], name: str) -> datetime:
    """Give an instant a row keeps."""
    return datetime.fromisoformat(cast("str", row[name]))


def encoded_nodes(states: Snapshot) -> list[JsonValue]:
    """Give the nodes of an own estimate as a row of the risk keeps them."""
    return [
        {
            "object_id": str(state.object_id),
            "lock_version": state.lock_version,
            "label": state.label,
            "rows": dict(state.rows),
        }
        for state in states
    ]


def decoded_nodes(kept: JsonValue) -> Snapshot:
    """Give back the nodes of an own estimate a row of the risk keeps, in their order."""
    items = cast("list[Mapping[str, JsonValue]]", kept)
    return tuple(
        ObjectState(
            object_id=UUID(cast("str", item["object_id"])),
            lock_version=cast("int", item["lock_version"]),
            label=cast("str", item["label"]),
            rows=cast("Mapping[str, JsonValue]", item["rows"]),
        )
        for item in items
    )


def risk_state(
    session: Session, project_id: UUID, held: tuple[UUID, UUID], *, whole: bool = False
) -> ObjectState | None:
    """Give a risk as the history keeps it in a revision; none if absent, or not evaluated there.

    ``held`` the risk and the revision; ``whole`` keeps every node of its own estimate besides.
    """
    risk_id, revision_id = held
    risk = session.scalars(
        select(Risk)
        .where(Risk.project_id == project_id, Risk.id == risk_id)
        .execution_options(populate_existing=True)
    ).first()
    evaluation = evaluation_of(session, project_id, risk_id, revision_id)
    if risk is None or evaluation is None:
        return None
    reviews = session.scalars(
        select(RiskReview)
        .where(
            RiskReview.project_id == project_id,
            RiskReview.risk_id == risk_id,
            RiskReview.revision_id == revision_id,
        )
        .order_by(RiskReview.created_at, RiskReview.id)
    )
    line = evaluation.provision_node_id
    bearer = None if line is None else bearing_of(session, project_id, [line]).get(line)
    own = evaluation.structure_id
    facts = structure_facts(session, project_id, own, lock=False)
    nodes = structure_nodes(session, project_id, own) if whole else ()
    base = differential_base(session, project_id, own) if whole else None
    based = () if base is None else structure_nodes(session, project_id, base)
    columns = ("label", "description", "mitigation_notes", "created_at", "created_by")
    kept = (
        "revision_id",
        "probability",
        "state",
        "structure_id",
        "provision_node_id",
        "provision_cost_category_id",
        "provision_subproject_id",
        "provision_task_lineage_id",
        "severity",
        "created_at",
        "created_by",
    )
    reviewed = ("id", "reviewed_on", "probability", "severity", "state", "created_at", "created_by")
    rows: dict[str, JsonValue] = {
        "risk": {name: text(getattr(risk, name)) for name in columns},
        "evaluation": {name: text(getattr(evaluation, name)) for name in kept},
        "reviews": [{name: text(getattr(each, name)) for name in reviewed} for each in reviews],
        "task_id": None if bearer is None else str(bearer.node_id),
        "own_estimate": {
            "planning_start_on": facts.planning_start_on.isoformat(),
            "nodes": encoded_nodes(nodes),
            "base_id": text(base),
            "base_nodes": encoded_nodes(based),
            **(_state_of(session, project_id, (own, revision_id)) if whole else {}),
        },
    }
    return ObjectState(risk.id, risk.lock_version, risk.label, rows)


def _state_of(session: Session, project_id: UUID, held: tuple[UUID, UUID]) -> dict[str, JsonValue]:
    """Give the state of an own estimate kept whole: up to date, and the counter of the main.

    ``held`` the own estimate and its revision. What its creation again judges its state by
    (``undoing``, EP-30).
    """
    own, revision_id = held
    main = aimed_structure(session, project_id, revision_id, None)
    counter = None if main is None else structure_facts(session, project_id, main, lock=False)
    return {
        "up_to_date": own_estimate_state(session, project_id, own).up_to_date,
        "main_lock_version": None if counter is None else counter.lock_version,
    }


class RiskRecording:
    """The entry of a write of a risk in the history of its writer, while the write is made.

    Opened by ``open``, once the revision is known; a writer without a stack keeps none, and the
    snapshots are then not taken.
    """

    __slots__ = ("_frame", "_frames", "_kind", "_project_id", "_revision_id", "_session", "_writer")

    def __init__(
        self,
        session: Session,
        project_id: UUID,
        change: tuple[Writer, UndoneKind],
        frames: ExitStack,
    ) -> None:
        """Hold what the entry is opened with: its writer and its kind, the frames it enters."""
        self._session, self._project_id = session, project_id
        self._writer: Writer = change[0]
        self._kind: UndoneKind = change[1]
        self._frames = frames
        self._frame: Recording | None = None
        self._revision_id: UUID | None = None

    def open(self, revision_id: UUID) -> None:
        """Open the entry in the stack of the writer in the revision written in, which it locks."""
        self._revision_id = revision_id
        act, session_id = self._writer.act, self._writer.session_id
        if act.author is None or session_id is None:
            return
        stack = UndoStack(revision_id, act.author, session_id)
        change = RecordedChange(self._project_id, stack, self._kind, (), act.at)
        self._frame = self._frames.enter_context(history.recording(self._session, change))

    def _state(self, risk_id: UUID, *, whole: bool) -> Snapshot:
        revision_id = cast("UUID", self._revision_id)
        found = risk_state(self._session, self._project_id, (risk_id, revision_id), whole=whole)
        return () if found is None else (found,)

    def before(self, risk_id: UUID | None, *, whole: bool = False) -> None:
        """Keep the risk as it is before the write, under its locks; none for a declaration."""
        if self._frame is not None:
            kept = () if risk_id is None else self._state(risk_id, whole=whole)
            self._frame.keep_before(kept)

    def after(self, risk_id: UUID, *, whole: bool = False) -> None:
        """Keep the risk as the write left it; absent once deleted."""
        if self._frame is not None:
            self._frame.keep_after(self._state(risk_id, whole=whole))

    def unchanged(self) -> None:
        """Keep no entry: the write changed nothing of the risk."""
        if self._frame is not None:
            self._frame.discard()


@contextmanager
def recorded(
    session: Session, project_id: UUID, writer: Writer, kind: UndoneKind
) -> Generator[RiskRecording]:
    """Frame a write of a risk: its entry kept once the block ends; nothing if the block raises."""
    with ExitStack() as frames:
        yield RiskRecording(session, project_id, (writer, kind), frames)
