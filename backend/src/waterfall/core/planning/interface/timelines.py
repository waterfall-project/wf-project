# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The named timelines of a project (WF-PLA-0140): listed, created, deleted.

A label is not unique, from 1 to 200 characters; a timeline is deleted for good, its inscriptions
with it, without a counter (#1733), under the command ``manage_timelines`` of the project (EP-06,
US-1400). ``load_timeline`` writes one of the witness at the identifier and the instant it imposes.

Declared by US-1380/L1; US-1400/L1 fills them, and gives each its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def list_timelines(session: Session, project_id: UUID) -> None:
    """List the timelines of a project (``listTimelines``)."""
    msg = "list_timelines is filled by US-1400/L1"
    raise NotImplementedError(msg)


def create_timeline(session: Session, project_id: UUID, act: Act) -> None:
    """Create a timeline of a project (``createTimeline``)."""
    msg = "create_timeline is filled by US-1400/L1"
    raise NotImplementedError(msg)


def delete_timeline(session: Session, project_id: UUID, timeline_id: UUID, act: Act) -> None:
    """Delete a timeline and its inscriptions (``deleteTimeline``)."""
    msg = "delete_timeline is filled by US-1400/L1"
    raise NotImplementedError(msg)


def load_timeline(session: Session, project_id: UUID, timeline_id: UUID, act: Act) -> None:
    """Write a timeline of the witness, at the identifier and the instant it imposes."""
    msg = "load_timeline is filled by US-1400/L1"
    raise NotImplementedError(msg)
