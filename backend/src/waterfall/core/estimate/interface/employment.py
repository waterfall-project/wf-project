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
``listCostStructures``, each in the order of the plan; ``forget_subproject`` the subproject the
lines of the bases of the current revision bear, once its deletion is admitted. The lines of a
base, which no operation serves, employ nothing and bear nothing (US-3050).

Declared by US-1490/L1; filled and registered by US-1490/L4.
"""

from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import (
    node_revisions,
    node_rows,
    outside_bases,
    revision_lines,
)
from waterfall.core.projects.interface import EstimatedLine, project_facts
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.database import among

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def category_is_employed(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those a line of an estimate employs, in any revision.

    A line of the base of a differential employs nothing (US-3050).
    """
    if not category_ids:
        return frozenset()
    rows = session.execute(
        select(EstimateLine.project_id, EstimateLine.node_id, EstimateLine.cost_category_id).where(
            EstimateLine.cost_category_id.in_(list(category_ids))
        )
    ).all()
    by_project: dict[UUID, list[tuple[UUID, UUID]]] = {}
    for project_id, node, category in rows:
        by_project.setdefault(project_id, []).append((node, category))
    found: set[UUID] = set()
    for project_id, held in by_project.items():
        kept = outside_bases(session, project_id, [node for node, _ in held])
        found |= {category for node, category in held if node in kept}
    return frozenset(found)


def _bearing(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID], *, bases: bool
) -> list[tuple[UUID, UUID, str]]:
    """Give the lines of a project that bear one of the subprojects: node, subproject, label.

    ``bases`` keeps those of the bases of the differentials, which no operation serves (US-3050).
    """
    rows = session.execute(
        select(EstimateLine.node_id, EstimateLine.subproject_id, EstimateLine.label).where(
            EstimateLine.project_id == project_id,
            EstimateLine.subproject_id.in_(list(subproject_ids)),
        )
    ).all()
    held = [(node, subproject, label) for node, subproject, label in rows if subproject is not None]
    if bases:
        return held
    kept = outside_bases(session, project_id, [node for node, _, _ in held])
    return [each for each in held if each[0] in kept]


def subproject_is_cited(
    session: Session, project_id: UUID, subproject_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give, of the subprojects of a project given, those a line of a marked revision bears.

    Every revision of the project but its current one is marked: an abandoned one keeps no line.
    The base a merged differential keeps in the revision its merge marked counts with it: a row of
    a marked revision is never written, and its line holds the key of the subproject (US-3050).
    """
    held = _bearing(session, project_id, subproject_ids, bases=True)
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
    """Give the lines of the current revision of a project that bear one of the subprojects.

    Those of the bases of its differentials left out: their subproject is forgotten at its deletion
    (``forget_subproject``, US-3050).
    """
    current = project_facts(session, project_id).current_revision_id
    held = _bearing(session, project_id, subproject_ids, bases=False)
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


def forget_subproject(session: Session, project_id: UUID, subproject_id: UUID) -> None:
    """Make the lines of the bases of the current revision of a project bear a subproject no more.

    What the deletion of a subproject asks once nothing refuses it (``deleteSubproject``): a line of
    a base, which no operation serves, neither refuses it nor keeps its key (US-3050). The base
    says the main structure as it was, but for a subproject that no longer is. The lines the
    session holds are synchronised with the statement (``fetch``): a line of a base loaded and
    changed in the same transaction would otherwise write the key back at its flush (#4212).
    """
    current = project_facts(session, project_id).current_revision_id
    if current is None:
        return
    every = revision_lines(session, project_id, current, bases=True)
    served = revision_lines(session, project_id, current, bases=False)
    nodes = [node for node in every if node not in served]
    if not nodes:
        return
    session.execute(
        update(EstimateLine)
        .where(
            EstimateLine.project_id == project_id,
            EstimateLine.subproject_id == subproject_id,
            among(EstimateLine.node_id, nodes),
        )
        .values(subproject_id=None)
        .execution_options(synchronize_session="fetch")
    )
