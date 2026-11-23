# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks tell the projects of the subprojects their provisions designate (#4208).

A registry of this module, filled by the risks at the import of their interface, which this module
never imports (the risks sit above the projects): the subprojects the evaluation of a risk in a
marked revision designates for its provision, which the deletion of a subproject counts as a
citation (``subproject_not_cited``, WF-DAT-0020: a marked revision is never written); and the
designation the evaluations of the current revision give up once that deletion is admitted, the
counter of each risk advanced and its audit naming the author of the deletion (``deleteSubproject``,
#732). While nothing is registered, no risk designates a subproject.

Declared and filled by US-3060/L4.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class RiskDesignations:
    """What the risks answer the projects of the subprojects their provisions designate.

    ``marked(session, project_id, subproject_ids)`` gives, of the subprojects named, those the
    evaluation of a risk in a marked revision designates; ``undesignate(session, project_id,
    subproject_id, act)`` sets to null the designation of a subproject being deleted in the
    evaluations of the current revision.
    """

    marked: Callable[[Session, UUID, Collection[UUID]], frozenset[UUID]]
    undesignate: Callable[[Session, UUID, UUID, Act], None]


# What the risks answer of their designations, registered at the import of their interface.
_DESIGNATIONS: Registry[RiskDesignations] = Registry("projects.risk_designations")


def register_risk_designations(designations: RiskDesignations) -> Callable[[], None]:
    """Add what the risks answer the projects of their designations; give its withdrawal."""
    return _DESIGNATIONS.register(designations)


def subprojects_designated(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project named, those a risk of a marked revision designates."""
    found: set[UUID] = set()
    if subproject_ids:
        for designations in _DESIGNATIONS.entries():
            found |= designations.marked(session, project_id, subproject_ids)
    return frozenset(found)


def undesignate_subproject(
    session: Session, project_id: UUID, subproject_id: UUID, act: Act
) -> None:
    """Set to null, in the current revision, the designation of a subproject being deleted."""
    for designations in _DESIGNATIONS.entries():
        designations.undesignate(session, project_id, subproject_id, act)
