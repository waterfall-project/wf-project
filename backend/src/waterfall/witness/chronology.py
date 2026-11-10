# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the projects of the witness (EP-04): its objects in order, after the reference.

The loader calls this entry once, after the slices of the reference (``loader``); it calls the
slices of the projects, one per object, each in a file of its own that the story of the object
fills, in the order of their dependencies: the projects and the local accounts of their
contributors, the contributors, the subprojects, the work breakdown, the timelines (EP-06), then
the revisions and the events of the chronology at the instants it imposes (``Act.at``;
WF-CYC-0130). The tasks, then the lines, fill each revision between its opening and the next
event, by the fillers this entry registers (``register_revision_filler``, EP-06, EP-07); the actual
costs come after them, at the instants of their events (EP-09). Each tells whether it wrote, as a
slice of the loader does; this entry, whether one of them did.

The chronology of the witness, ``make mock-data`` writes it beside the examples
(``project_state_transitions.json``, US-0990/L1): this entry reads it first (``timeline``), so that
a file that strays from its model stops the command before any slice writes, and the slices
that write at an instant of it read it again. The platform is the author of all; the instant of each
write is the event's (``Act.at``), but for the reference, which the loader sets at the loading.
"""

from typing import TYPE_CHECKING

from waterfall.witness import (
    contributors,
    costs,
    estimate_lines,
    projects,
    revisions,
    subprojects,
    tasks,
    timeline,
    timelines,
    work_breakdown,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness
    from waterfall.witness.loader import Slice

# A contributor names its project and its account, a subproject, an element of the work breakdown
# and a timeline their project; a revision and its events come last, the code entered among them,
# the tasks of a revision inscribed to the timelines.
SLICES: tuple[tuple[str, Slice], ...] = (
    ("projects", projects.load),
    ("contributors", contributors.load),
    ("subprojects", subprojects.load),
    ("work_breakdown", work_breakdown.load),
    ("timelines", timelines.load),
    ("revisions", revisions.load),
)
# The tasks of a revision, then its lines, which name them, written once it is opened, before its
# marking.
revisions.register_revision_filler(tasks.fill)
revisions.register_revision_filler(estimate_lines.fill)
# The actual costs, after the lines, which the march of the events writes at their instants from
# US-1650/L2 on (EP-09): their slice, and the extensions of their module, held from the socle on.
EXTENDING = costs.EXTENDING


def load(session: Session, witness: Witness) -> bool:
    """Load each slice of the projects in its order; tell whether one of them wrote."""
    timeline.read(witness)
    written = [write(session, witness) for _, write in SLICES]
    return any(written)
