# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the lines employ of the reference and of the project, as the modules below ask it.

``category_is_employed`` tells the cost settings the categories a line employs — a line of any
revision, current or marked: an abandoned one keeps none —, which a change of the kind of a nature
or of a category refuses (``register_employment``, WF-REF-0030, WF-REF-0040).
``subproject_is_cited`` and ``subproject_is_estimated`` tell the projects the subprojects a line of
a marked revision, and of the current one, bears; ``subproject_estimate_lines`` the lines of the
current revision that bear each, which the deletion of a subproject names when it refuses
(``register_estimate_facts``, WF-DAT-0080, WF-PRJ-0050): each by its structure and the label of it,
its node, its row number and its label, the main structure first, then the others in the order of
``listCostStructures``, each in the order of the plan.

Declared by US-1490/L1; filled and registered by US-1490/L4.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import node_revisions, node_rows
from waterfall.core.projects.interface import EstimatedLine, project_facts
from waterfall.core.revisions.interface import structure_facts

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def category_is_employed(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those a line of an estimate employs, in any revision."""
    if not category_ids:
        return frozenset()
    found = session.scalars(
        select(EstimateLine.cost_category_id)
        .where(EstimateLine.cost_category_id.in_(list(category_ids)))
        .distinct()
    )
    return frozenset(found)


def _bearing(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> list[tuple[UUID, UUID, str]]:
    """Give the lines of a project that bear one of the subprojects: node, subproject, label."""
    rows = session.execute(
        select(EstimateLine.node_id, EstimateLine.subproject_id, EstimateLine.label).where(
            EstimateLine.project_id == project_id,
            EstimateLine.subproject_id.in_(list(subproject_ids)),
        )
    )
    return [(node, subproject, label) for node, subproject, label in rows if subproject is not None]


def subproject_is_cited(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project given, those a line of a marked revision bears.

    Every revision of the project but its current one is marked: an abandoned one keeps no line.
    """
    held = _bearing(session, project_id, subproject_ids)
    if not held:
        return frozenset()
    current = project_facts(session, project_id).current_revision_id
    revisions = node_revisions(session, project_id, [node for node, _, _ in held])
    return frozenset(
        subproject for node, subproject, _ in held if revisions.get(node, current) != current
    )


def _current_bearing(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> list[tuple[UUID, UUID, str]]:
    """Give the lines of the current revision of a project that bear one of the subprojects."""
    current = project_facts(session, project_id).current_revision_id
    held = _bearing(session, project_id, subproject_ids)
    if current is None or not held:
        return []
    revisions = node_revisions(session, project_id, [node for node, _, _ in held])
    return [each for each in held if revisions.get(each[0]) == current]


def subproject_is_estimated(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project given, those a line of its current revision bears.

    Without the lines: the list of subprojects asks no more, and reads no tree for it.
    """
    return frozenset(
        subproject for _, subproject, _ in _current_bearing(session, project_id, subproject_ids)
    )


def subproject_estimate_lines(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> dict[UUID, tuple[EstimatedLine, ...]]:
    """Give the lines of the current revision of a project that bear each subproject given.

    A subproject none bears is left out. The lines named in the order a refusal names them: the
    main structure first, then the others by their label, each in the order of the plan.
    """
    held = _current_bearing(session, project_id, subproject_ids)
    if not held:
        return {}
    rows = node_rows(session, project_id, [node for node, _, _ in held])
    structures = {
        each: structure_facts(session, project_id, each, lock=False)
        for each in {row.structure_id for row in rows.values()}
    }

    def order(line: tuple[UUID, UUID, str]) -> tuple[bool, str, UUID, int]:
        row = rows[line[0]]
        facts = structures[row.structure_id]
        return (not facts.is_main, facts.label, row.structure_id, row.row_number)

    found: dict[UUID, tuple[EstimatedLine, ...]] = {}
    for node, subproject, label in sorted(held, key=order):
        row = rows[node]
        named = EstimatedLine(
            row.structure_id, structures[row.structure_id].label, node, row.row_number, label
        )
        found[subproject] = (*found.get(subproject, ()), named)
    return found
