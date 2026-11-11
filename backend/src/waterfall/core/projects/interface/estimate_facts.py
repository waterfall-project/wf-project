# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the estimate tells the projects of its lines: subprojects they bear, roles they employ.

A registry of this module (EP-07, "Les points d'extension"), filled by the estimate at the import of
its interface, which this module never imports: one entry holds the questions the projects ask
of the lines, and two acts — the subprojects a marked revision cites by its lines
(``subproject_is_cited``), those the lines of the current revision bear
(``subproject_is_estimated``, which the list of subprojects asks), and those lines, named
(``subproject_estimate_lines``, which the deletion of a subproject asks alone; WF-DAT-0080,
WF-PRJ-0050); the roles the labour lines of a project employ (``roles_employed``,
``listContributorSuggestions``, US-1540); whether a marked revision bears a line
(``marked_revision_has_lines``, ``getProjectNextState``, US-1540); the current revision priced
again when the inflation of its project changes (``reinflate_project``, ``updateProject``,
US-1500), its lock shared before the project is locked (``hold_revision``). Each story that asks a
question reads it here; while nothing is registered, no subproject is cited nor estimated, and no
marked revision bears a line.

Declared by US-1490/L4, which fills the questions of the subprojects; US-1500/L2 asks the
inflation (``hold_estimate``, ``reinflate_estimate``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class EstimatedLine:
    """A line of estimate a refusal names (``ProblemEstimateLine``).

    Its structure and the label of it, its node, its row number in the whole structure, its label.
    """

    structure_id: UUID
    structure_label: str
    node_id: UUID
    row_number: int
    label: str


@dataclass(frozen=True, slots=True)
class EstimateFacts:
    """What the estimate answers the projects, each question given its session and its project.

    ``subproject_is_cited`` gives, of the subprojects named, those a line of a marked revision
    bears; ``subproject_is_estimated`` those a line of the current revision bears;
    ``subproject_estimate_lines`` the lines of the current revision that bear each subproject
    named, a subproject that none bears left out, in the order a refusal names them;
    ``roles_employed`` the roles of resources the labour lines of the project employ;
    ``marked_revision_has_lines`` whether a marked revision of the project bears a line;
    ``reinflate_project`` prices the current revision of the project again, under the lock of the
    project, at the instant given; ``hold_revision`` shares the lock of its current revision,
    before the project is locked — the order of the marking, which locks the revision, then the
    project (US-1500).
    """

    subproject_is_cited: Callable[[Session, UUID, Collection[UUID]], frozenset[UUID]]
    subproject_is_estimated: Callable[[Session, UUID, Collection[UUID]], frozenset[UUID]]
    subproject_estimate_lines: Callable[
        [Session, UUID, Collection[UUID]], Mapping[UUID, tuple[EstimatedLine, ...]]
    ]
    roles_employed: Callable[[Session, UUID], frozenset[UUID]]
    marked_revision_has_lines: Callable[[Session, UUID], bool]
    reinflate_project: Callable[[Session, UUID, datetime], None]
    hold_revision: Callable[[Session, UUID], None]


# What the estimate answers of its lines, registered at the import of its interface.
_FACTS: Registry[EstimateFacts] = Registry("projects.estimate_facts")


def register_estimate_facts(facts: EstimateFacts) -> Callable[[], None]:
    """Add what the estimate answers the projects of its lines; give its withdrawal."""
    return _FACTS.register(facts)


def subprojects_cited(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project named, those a marked revision cites by a line."""
    cited: set[UUID] = set()
    if subproject_ids:
        for facts in _FACTS.entries():
            cited |= facts.subproject_is_cited(session, project_id, subproject_ids)
    return frozenset(cited)


def subprojects_estimated(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project named, those a line of the current revision bears."""
    found: set[UUID] = set()
    if subproject_ids:
        for facts in _FACTS.entries():
            found |= facts.subproject_is_estimated(session, project_id, subproject_ids)
    return frozenset(found)


def subproject_estimate_lines(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> dict[UUID, tuple[EstimatedLine, ...]]:
    """Give the lines of the current revision that bear each subproject named; none left out."""
    found: dict[UUID, tuple[EstimatedLine, ...]] = {}
    if subproject_ids:
        for facts in _FACTS.entries():
            for each, lines in facts.subproject_estimate_lines(
                session, project_id, subproject_ids
            ).items():
                found[each] = (*found.get(each, ()), *lines)
    return found


def roles_employed(session: Session, project_id: UUID) -> frozenset[UUID]:
    """Give the roles of resources the labour lines of a project employ; none while unregistered."""
    employed: set[UUID] = set()
    for facts in _FACTS.entries():
        employed |= facts.roles_employed(session, project_id)
    return frozenset(employed)


def marked_revision_has_lines(session: Session, project_id: UUID) -> bool:
    """Tell whether a marked revision of a project bears a line; no while unregistered."""
    return any(facts.marked_revision_has_lines(session, project_id) for facts in _FACTS.entries())


def hold_estimate(session: Session, project_id: UUID) -> None:
    """Share the lock of the current revision of a project, before the project is locked.

    What a change of the rate of inflation asks first (``updateProject``, US-1500): the revision
    it prices again is locked before the project, as the marking locks them.
    """
    for facts in _FACTS.entries():
        facts.hold_revision(session, project_id)


def reinflate_estimate(session: Session, project_id: UUID, at: datetime) -> None:
    """Price the current revision of a project again, its rate of inflation changed (WF-PRJ-0040).

    Under the lock of the project, its current revision held first (``hold_estimate``), at the
    instant of the change: nothing while nothing is registered.
    """
    for facts in _FACTS.entries():
        facts.reinflate_project(session, project_id, at)
