# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structures of the witness: its main structures and its amendments (US-2650/L1).

``witness_structures.json`` (``wftools.mockwitnessrisksfile``) names the main structure of the
revisions 101 and 102 and describes the two amendments of PRJ-001; the chronology says when each
amendment is opened, merged or updated (``amendment_opened``, ``amendment_merged``,
``amendment_rebased``; EP-08, "Le chargeur du témoin"). Each write is made through the interface of
the planning, by the rules of the API, at the instant of its event:

- **the opening** (``load_differential``), under the identifier the witness imposes, the copies of
  its nodes under the identifiers the examples name, the others derived from it and their lineage;
  its content is then entered if its revision gives it: the amendment 1 holds the reference 101
  entered whole — what separates the offer from the reference, the remplissage that was the 101's
  (EP-06, EP-07) —, so that its merge produces the reference;
- **the merge** (``load_merge``), which marks the revision under the name and the description of
  ``revisions.json`` and makes it the reference, the amendment updated first if the walk wrote the
  main structure since its opening;
- **the update** (``load_rebase``) from the main structure, then the content entered if the
  revision gives it: the amendment 2, taken over out of date by the revision 102, updated after the
  last write of its main structure, then its trials of the wiring resumed entered.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.planning.interface import (
    DifferentialLoad,
    Place,
    load_differential,
    load_merge,
    load_rebase,
)
from waterfall.witness.filling import Changes, LineRow, Strict, TaskRow

if TYPE_CHECKING:
    from collections.abc import Collection

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness

STRUCTURES_FILE = "witness_structures.json"


class _Main(Strict):
    """The main structure of a revision, as the examples name it."""

    revision: int
    structure_id: UUID


class _Named(Strict):
    """A node of an amendment the examples name: its lineage and its identifier."""

    lineage_id: UUID
    node_id: UUID


class AmendmentRow(Strict):
    """An amendment of the witness: where it is opened, what its content is made of.

    ``copies`` its copy in each revision that takes it up, as the examples name it; ``node_ids``
    the identifiers of its nodes the examples name in the revision whose rows it takes.
    """

    structure_id: UUID
    label: str
    revision: int
    rows_of: int
    copies: list[_Main]
    tasks: list[TaskRow]
    lines: list[LineRow]
    removed_lineage_ids: list[UUID]
    node_ids: list[_Named]

    def structure_in(self, revision: int) -> UUID | None:
        """Give the amendment in a revision: where it is opened, or its copy; none elsewhere."""
        if revision == self.revision:
            return self.structure_id
        found = [each.structure_id for each in self.copies if each.revision == revision]
        return found[0] if found else None

    def changes_in(self, revision: int) -> Changes:
        """Give what the amendment changes, in a revision, of the rows of the revision it takes.

        Its nodes are named as the examples name them in the revision whose rows it takes, and
        derived from its identifier in that revision elsewhere: two revisions never share one.
        """
        structure_id = self.structure_in(revision)
        if structure_id is None:
            message = f"the amendment {self.label} is not in revision {revision}"
            raise ValueError(message)
        return Changes(
            structure_id,
            tuple(self.tasks),
            tuple(self.lines),
            frozenset(self.removed_lineage_ids),
            {each.lineage_id: each.node_id for each in self.node_ids}
            if revision == self.rows_of
            else {},
        )


class Structures(Strict):
    """The main structures and the amendments of the witness, in the order of their opening."""

    main: list[_Main]
    amendments: list[AmendmentRow]

    def main_of(self, revision: int) -> UUID | None:
        """Give the main structure of a revision, if the witness names it."""
        found = [each.structure_id for each in self.main if each.revision == revision]
        return found[0] if found else None

    def named(self, structure_id: UUID) -> AmendmentRow:
        """Give an amendment the chronology names; or refuse the file."""
        for each in self.amendments:
            if each.structure_id == structure_id:
                return each
        message = f"the chronology names an amendment {structure_id} that the witness does not"
        raise ValueError(message)

    def carries(self, revision: int) -> bool:
        """Tell whether an amendment opened in a revision carries the rows given the revision."""
        return any(
            each.revision == revision and each.rows_of == revision for each in self.amendments
        )

    @classmethod
    def read(cls, witness: Witness) -> Structures:
        """Read the structures of the witness; a file that strays raises."""
        return witness.read(STRUCTURES_FILE, cls)


def open_amendment(
    session: Session,
    row: AmendmentRow,
    where: tuple[UUID, UUID],
    lineages: Collection[UUID],
    act: Act,
) -> None:
    """Open an amendment in a revision, its nodes copied under the identifiers of the witness.

    ``where`` the project and the revision, ``lineages`` those of the nodes its copy may meet.
    """
    changes = row.changes_in(row.revision)
    nodes = {lineage: changes.node(lineage) for lineage in lineages}
    load_differential(session, where, DifferentialLoad(row.structure_id, row.label, nodes), act)


def merge_amendment(
    session: Session, place: Place, named: tuple[str, str | None], act: Act
) -> None:
    """Merge an amendment, its revision marked under the name and the description given."""
    load_merge(session, place, named, act)


def rebase_amendment(session: Session, place: Place, act: Act) -> None:
    """Update an amendment from the main structure of its revision, without a report."""
    load_rebase(session, place, act)
