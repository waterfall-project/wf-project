# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The timelines of the project of the witness, before its revisions.

``timelines.json``: the two timelines of PRJ-001, under the identifiers the examples give them,
loaded after the work breakdown and before the revisions, so that the inscriptions of the tasks
find them (EP-06, "Le chargeur du témoin"), at the instant the chronology creates the project.
Written through the interface of the planning, by the very rules of the creation.
"""

from typing import TYPE_CHECKING

from pydantic import RootModel

from waterfall.api.contract.models import Project, Timeline
from waterfall.core.planning.interface import TimelineView, load_timeline, timelines_present
from waterfall.witness import timeline
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

TIMELINES_FILE = "timelines.json"
PROJECT_FILE = "project.json"


class Timelines(RootModel[list[Timeline]]):
    """The timelines of the witness, as ``listTimelines`` answers them."""


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    project = witness.read(PROJECT_FILE, Project)
    project_id = project.project_id.root
    loads = tuple(
        TimelineView(item.timeline_id.root, item.label)
        for item in witness.read(TIMELINES_FILE, Timelines).root
    )
    imposed = {load.timeline_id for load in loads}
    if is_loaded(imposed, timelines_present(session, imposed)):
        return False
    act = timeline.created(witness, project)
    for load in loads:
        load_timeline(session, project_id, load, act)
    return True
