# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of the project of the witness.

``subprojects.json``: the subprojects of the project of ``project.json``, each under the
identifier the witness imposes, with its code and its label, at the instant the chronology
creates the project. Written through the interface of the
projects, by the very rules of the creation: the code is judged and unique in the project. The
costs and the commands the example says are what the later EPICs derive, not what is loaded.
"""

from typing import TYPE_CHECKING

from pydantic import RootModel

from waterfall.api.contract.models import Project, Subproject
from waterfall.core.projects.interface import (
    SubprojectLoad,
    SubprojectWrite,
    load_subprojects,
    subprojects_present,
)
from waterfall.witness import timeline
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

SUBPROJECTS_FILE = "subprojects.json"
PROJECT_FILE = "project.json"


class Subprojects(RootModel[list[Subproject]]):
    """The subprojects of the witness, as ``listSubprojects`` answers them."""


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    project = witness.read(PROJECT_FILE, Project)
    project_id = project.project_id.root
    described = witness.read(SUBPROJECTS_FILE, Subprojects).root
    loads = tuple(
        SubprojectLoad(item.subproject_id.root, SubprojectWrite(item.code.root, item.label))
        for item in described
    )
    imposed = {load.subproject_id for load in loads}
    if is_loaded(imposed, subprojects_present(session, imposed)):
        return False
    load_subprojects(session, project_id, loads, timeline.created(witness, project))
    return True
