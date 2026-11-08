# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The named timelines of a project (WF-PLA-0140): listed, created, deleted.

A label is not unique, from 1 to 200 characters and not blank; a timeline is deleted for good, its
inscriptions with it (the key of the inscription cascades), without a counter (#1733), under the
command ``manage_timelines`` of the project (EP-06, US-1400). A write decides on the state of the
project under the lock of the project: refused if it is terminal (409 ``project_not_terminal``,
WF-CYC-0100), before anything is written. ``load_timeline`` writes one of the witness at the
identifier and the instant it imposes, by the very rules of the creation.

The inscriptions of the tasks are those of ``tracking`` (US-1400/L2).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.planning.tables import TIMELINE_LABEL_LENGTH, Timeline
from waterfall.core.projects.interface import lock_project, project_facts
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
PROJECT_NOT_TERMINAL = "project_not_terminal"
# The states that end the cycle of life (WF-CYC-0080), as the projects name them.
TERMINAL = ("completed", "lost", "abandoned")


@dataclass(frozen=True, slots=True)
class TimelineView:
    """A timeline: its identifier and its label, as it is read or as the witness imposes it."""

    timeline_id: UUID
    label: str


def _view(row: Timeline) -> TimelineView:
    return TimelineView(row.id, row.label)


def _refuse_label(label: str) -> None:
    """Refuse a label that is blank or too long (422), judged again for the witness."""
    if not label.strip():
        fault = FieldError("/label", VALUE_REQUIRED)
    elif len(label) > TIMELINE_LABEL_LENGTH:
        fault = FieldError("/label", VALUE_TOO_LONG, {"maximum": TIMELINE_LABEL_LENGTH})
    else:
        return
    raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))


def _lock_unterminated(session: Session, project_id: UUID) -> None:
    """Lock a project, then read its state under the lock; refuse a terminal one (409)."""
    facts = lock_project(session, project_id)
    if facts.state in TERMINAL:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": PROJECT_NOT_TERMINAL})


def _insert(
    session: Session, project_id: UUID, timeline_id: UUID, label: str, act: Act
) -> Timeline:
    row = Timeline(
        id=timeline_id,
        project_id=project_id,
        label=label,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
    )
    session.add(row)
    session.flush()
    return row


def list_timelines(session: Session, project_id: UUID) -> list[TimelineView]:
    """List the timelines of a project, in the order they were created (``listTimelines``).

    Refused if the project is unknown (404).
    """
    project_facts(session, project_id)
    rows = session.scalars(
        select(Timeline)
        .where(Timeline.project_id == project_id)
        .order_by(Timeline.created_at, Timeline.id)
    )
    return [_view(row) for row in rows]


def create_timeline(session: Session, project_id: UUID, label: str, act: Act) -> TimelineView:
    """Create a timeline of a project, without inscription (``createTimeline``).

    The label is judged first (422); then the project is locked and read under the lock: refused
    if unknown (404) or terminal (409 ``project_not_terminal``). The label is not unique.
    """
    _refuse_label(label)
    _lock_unterminated(session, project_id)
    return _view(_insert(session, project_id, new_id(), label, act))


def delete_timeline(session: Session, project_id: UUID, timeline_id: UUID) -> None:
    """Delete a timeline and its inscriptions for good (``deleteTimeline``).

    Under the lock of the project, read under it: refused if the project is unknown (404) or
    terminal (409 ``project_not_terminal``), and if the project holds no such timeline (404), a
    timeline already deleted included. The inscriptions go with it, by the key that cascades.
    """
    _lock_unterminated(session, project_id)
    deleted = session.scalars(
        delete(Timeline)
        .where(Timeline.id == timeline_id, Timeline.project_id == project_id)
        .returning(Timeline.id)
    ).first()
    if deleted is None:
        raise NotFoundError(NOT_FOUND)


def timelines_present(session: Session, timeline_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of the identifiers given, those of the timelines that exist (the witness's)."""
    if not timeline_ids:
        return frozenset()
    found = select(Timeline.id).where(Timeline.id.in_(timeline_ids))
    return frozenset(session.scalars(found))


def load_timeline(session: Session, project_id: UUID, load: TimelineView, act: Act) -> None:
    """Write a timeline of the witness, at the identifier and the instant it imposes.

    By the rules of the creation: the label is judged, the project is not terminal.
    """
    _refuse_label(load.label)
    _lock_unterminated(session, project_id)
    _insert(session, project_id, load.timeline_id, load.label, act)
