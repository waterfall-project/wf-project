# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the projects of the witness (EP-04): its objects in order, after the reference.

The loader calls this entry once, after the slices of the reference (``loader``); it calls the
slices of the projects, one per object, each in a file of its own that the story of the object
fills, in the order of their dependencies: the projects and the local accounts of their
contributors, the contributors, the subprojects, the work breakdown, then the revisions and the
events of the chronology at the instants it imposes (``Act.at``; WF-CYC-0130). Each tells whether
it wrote, as a slice of the loader does; this entry, whether one of them did.

The chronology of the witness, ``make mock-data`` writes it beside the examples (US-0990/L1), and
US-0990/L2 reads it here: until then each slice writes nothing.
"""

from typing import TYPE_CHECKING

from waterfall.witness import contributors, projects, revisions, subprojects, work_breakdown

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness
    from waterfall.witness.loader import Slice

# A contributor names its project and its account, a subproject and an element of the work
# breakdown their project; a revision and its events come last, the code entered among them.
SLICES: tuple[tuple[str, Slice], ...] = (
    ("projects", projects.load),
    ("contributors", contributors.load),
    ("subprojects", subprojects.load),
    ("work_breakdown", work_breakdown.load),
    ("revisions", revisions.load),
)


def load(session: Session, witness: Witness) -> bool:
    """Load each slice of the projects in its order; tell whether one of them wrote."""
    written = [write(session, witness) for _, write in SLICES]
    return any(written)
