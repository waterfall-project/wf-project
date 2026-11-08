# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of the revisions of the witness: the content of each revision, between its events.

Registered by ``register_revision_filler`` (``chronology``): after the slice of the revisions opens
a revision of PRJ-001 — 100, 101, 102 — and before the next event marks it, it reconciles by
lineage the tasks the copy gave the revision with those ``witness_tasks.json`` describes for it —
created, changed, deleted, their links, their states, their inscriptions, the date the planning of
the structure starts on — through the interface of the planning, at the identifiers and the instant
imposed (EP-06, "Le chargeur du témoin"). The dates are those the engine computes.

Declared by US-1380/L1; US-1400/L2 fills the inscriptions — by the lineage of each task, so that
they follow it from revision to revision: those a revision describes replace the ones its lineage
held —, US-1480/L2 the rest.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from waterfall.core.planning.interface import TrackingLoad, TrackingSent, load_tracking

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness
    from waterfall.witness.revisions import OpenedRevision

TASKS_FILE = "witness_tasks.json"


class _Inscription(BaseModel):
    """An inscription of a task of the witness, as the description writes it."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    timeline_id: UUID | None


class _Task(BaseModel):
    """What the description says of a task of a revision that the inscriptions need."""

    # The rest of the description is read by US-1480/L2.
    model_config = ConfigDict(extra="ignore")

    revision: int
    lineage_id: UUID
    is_milestone: bool
    inscriptions: list[_Inscription]


class _Tasks(BaseModel):
    """The tasks of the witness by revision, as ``witness_tasks.json`` keeps them."""

    model_config = ConfigDict(extra="ignore")

    tasks: list[_Task]


def _number(revision_id: UUID) -> int | None:
    """Give the number an identifier of the witness ends with, ``None`` if it is not a number."""
    last = str(revision_id).rsplit("-", 1)[1]
    return int(last) if last.isdecimal() else None


def fill(session: Session, witness: Witness, opened: OpenedRevision) -> None:
    """Write the inscriptions the witness describes for a revision just opened, by lineage.

    The timelines are those of the slice before the revisions; a lineage the revision describes
    keeps the inscriptions it says, those of the revision before replaced.
    """
    number = _number(opened.revision.revision_id.root)
    project_id = opened.revision.project_id.root
    for task in witness.read(TASKS_FILE, _Tasks).tasks:
        if task.revision == number:
            entries = tuple(TrackingSent(each.kind, each.timeline_id) for each in task.inscriptions)
            load = TrackingLoad(task.lineage_id, entries, task.is_milestone)
            load_tracking(session, project_id, load, opened.act)
