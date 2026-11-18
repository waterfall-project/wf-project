# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of an amendment into the main structure: what each module finds and writes of it.

A registry of this module (EP-08, "La fusion et la survenance"), that the planning and the estimate
fill at the import of their interface, the planning first: the revisions do not read the nodes nor
the lines of a structure. Each module gives its part of the differences of the amendment with the
main structure, matched by the lineage (WF-DAT-0030), and of their application — the planning its
tasks and links, the estimate its lines —, by one function: called while the report is computed
(``StructureMerging.applying`` false), it writes nothing; called by the application, under the lock
of the two structures, it writes what the very same computation finds, so that what the report
presented is what is written. The parts are in the forms of the contract, the report of a merge
taking up those of an import (``ImportDifference``, ``ImportCompletedTask``, ``ReportRefusal``).

Declared by US-2550/L1, the socle of EP-08, with nothing registered; filled by US-2560/L1 (the
report) and US-2560/L2 (the application), which add here the merge itself.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.revisions.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class StructureMerging:
    """A merge of an amendment into the main structure of its revision, in its transaction.

    ``applying`` tells the application, which writes, from the report, which writes nothing.
    """

    session: Session
    project_id: UUID
    revision_id: UUID
    main_structure_id: UUID
    amendment_id: UUID
    act: Act
    applying: bool


@dataclass(frozen=True, slots=True)
class MergePart:
    """What a module finds of a merge, each in the form of the contract, empty when nothing.

    ``differences`` as ``ImportDifference``, ``completed_tasks`` the started tasks the amendment
    removes and the merge completes as ``ImportCompletedTask``, ``refusals`` as ``ReportRefusal``.
    """

    differences: tuple[Mapping[str, object], ...] = ()
    completed_tasks: tuple[Mapping[str, object], ...] = ()
    refusals: tuple[Mapping[str, object], ...] = ()


# What each module finds and writes of a merge, in the order of registration: the planning before
# the estimate, whose lines name its tasks.
_MERGES: Registry[Callable[[StructureMerging], MergePart]] = Registry("revisions.merge")


def register_merge(part: Callable[[StructureMerging], MergePart]) -> Callable[[], None]:
    """Add the part a module takes of a merge after those registered; give its withdrawal.

    A module registers at the import of its interface, which imports this one first.
    """
    return _MERGES.register(part)


def merge_parts(merging: StructureMerging) -> MergePart:
    """Give what every module registered finds of a merge, in their order; empty while none is."""
    found = [part(merging) for part in _MERGES.entries()]
    return MergePart(
        differences=tuple(each for part in found for each in part.differences),
        completed_tasks=tuple(each for part in found for each in part.completed_tasks),
        refusals=tuple(each for part in found for each in part.refusals),
    )
