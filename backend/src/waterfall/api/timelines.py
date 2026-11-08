# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The named timelines of a project and the inscriptions of its tasks (WF-PLA-0140).

``listTimelines``, ``createTimeline`` and ``deleteTimeline`` (US-1400/L1);
``setNodeTracking`` (US-1400/L2).

A project is read by whoever may consult its planning; its timelines are written by its
contributors who may write the planning, the command ``manage_timelines`` of the project
(WF-PLA-0140, WF-CYC-0100).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import Timeline, TimelineCreate
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.core.planning.interface import (
    TimelineView,
    create_timeline,
    delete_timeline,
    list_timelines,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["planning"])

CONSULT = "planning.read"
CHANGE = "planning.write"


def described(view: TimelineView) -> Timeline:
    """Describe a timeline as the contract does."""
    return Timeline.model_validate({"timeline_id": view.timeline_id, "label": view.label})


@router.get(
    "/projects/{project_id}/timelines",
    operation_id="listTimelines",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_timelines(project_id: UUID, session: Transaction) -> list[dict[str, Any]]:
    """Give the timelines of a project, in the order they were created."""
    return [described(view).model_dump(mode="json") for view in list_timelines(session, project_id)]


@router.post(
    "/projects/{project_id}/timelines",
    operation_id="createTimeline",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    status_code=201,
    response_model=Timeline,
)
def post_timeline(
    project_id: UUID, body: TimelineCreate, actor: Acting, session: Transaction
) -> Timeline:
    """Create a timeline of a project, without inscription; its label is not unique."""
    act = Act(actor.user_id, utc_now())
    return described(create_timeline(session, project_id, body.label, act))


@router.delete(
    "/projects/{project_id}/timelines/{timeline_id}",
    operation_id="deleteTimeline",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    status_code=204,
)
def remove_timeline(project_id: UUID, timeline_id: UUID, session: Transaction) -> Response:
    """Delete for good a timeline and its inscriptions, without a counter (#1733)."""
    delete_timeline(session, project_id, timeline_id)
    return Response(status_code=204)
