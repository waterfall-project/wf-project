# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evolution of the indices of a project (``getIndexHistory``; US-1700).

For each scope, or the one asked for, a point by revision that kept the indicators of the project
at its marking, by its marking, then the point of the current day; the thresholds of the day
(WF-IND-0130, WF-REF-0170). A project before In progress is refused (409).

The points a marking kept are read as it kept them — the two indices of its document ``project``,
the zone classified at the reading on the thresholds of the day (WF-REF-0130) —, an index it could
not compute left as not computable, never omitted (#1777). A revision marked before In progress kept
no such document and gives no point (WF-DAT-0040); nor does it for a subproject created after the
marking. The point of the day is the computation of ``getProjectIndicators`` (US-1660), on the
current revision or, without one, the last marked, its ``version_name`` null, its instant the
``computed_at`` of that computation, read in the cache of the indicators of the day when the
process has one (US-1720/L2); the ``context`` is its.
The refusals are those of ``getProjectIndicators``: the state, then the scope.

Declared by US-1660/L1, the socle of EP-10; ``scope`` none gives every scope, ``at`` is the instant
of the computation, read by the caller.
"""

from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import select

from waterfall.core.cost_settings.interface import (
    read_reference_settings,
    thresholds_document,
)
from waterfall.core.costs.interface import PROJECT, UNASSIGNED
from waterfall.core.indicators.interface.project_indicators import day_indicators, day_reading
from waterfall.core.indicators.interface.reading import IndicatorsReading
from waterfall.core.indicators.interface.stored_documents import kept_revisions
from waterfall.core.indicators.shaping import classified, instant
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import (
    NOBODY,
    SubprojectFilters,
    SubprojectSort,
    list_subprojects,
)
from waterfall.core.revisions.interface import revision_version_names

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import IndexThresholds
    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.indicators.interface.project_indicators import DayReading
    from waterfall.platform.cache import IndicatorsCache


def _labelled_scopes(
    session: Session, project_id: UUID, scope: CostScope | None
) -> list[tuple[CostScope, str | None]]:
    """Give the scopes to draw, each with its label: all of them, or the one asked for.

    The project, the subprojects in the order of ``listSubprojects``, then what is in none.
    """
    views = list_subprojects(session, project_id, NOBODY, SubprojectFilters(), SubprojectSort())
    everything: list[tuple[CostScope, str | None]] = [
        (PROJECT, None),
        *((view.subproject_id, view.label) for view in views),
        (UNASSIGNED, None),
    ]
    if scope is None:
        return everything
    return [each for each in everything if each[0] == scope]


def _point(
    at: str, revision_id: UUID, version_name: str | None, document: Document
) -> dict[str, Any]:
    return {
        "at": at,
        "revision_id": str(revision_id),
        "version_name": version_name,
        "cost_index": document["cost_index"],
        "schedule_index": document["schedule_index"],
    }


def _kept_documents(
    session: Session, project_id: UUID, revision_ids: list[UUID], scopes: list[CostScope]
) -> dict[tuple[UUID, str], Document]:
    """Read, in one statement, the document ``project`` each revision kept for the scopes drawn."""
    if not revision_ids:
        return {}
    rows = session.execute(
        select(
            RevisionIndicator.revision_id, RevisionIndicator.scope, RevisionIndicator.document
        ).where(
            RevisionIndicator.project_id == project_id,
            RevisionIndicator.kind == "project",
            RevisionIndicator.scope.in_([str(each) for each in scopes]),
            RevisionIndicator.revision_id.in_(revision_ids),
        )
    )
    return {(revision_id, scope): document for revision_id, scope, document in rows}


def _stored_points(
    session: Session, project_id: UUID, scopes: list[CostScope], thresholds: IndexThresholds
) -> dict[CostScope, list[dict[str, Any]]]:
    """Give, for each scope, the points the markings kept, earliest first."""
    kept = kept_revisions(session, project_id)
    ids = [each for each, _ in kept]
    names = revision_version_names(session, ids)
    documents = _kept_documents(session, project_id, ids, scopes)
    points: dict[CostScope, list[dict[str, Any]]] = {scope: [] for scope in scopes}
    for revision_id, marked_at in kept:
        for scope in scopes:
            found = documents.get((revision_id, str(scope)))
            if found is not None:
                points[scope].append(
                    _point(
                        instant(marked_at),
                        revision_id,
                        names.get(revision_id),
                        classified(found, thresholds),
                    )
                )
    return points


def index_history(
    session: Session,
    project_id: UUID,
    scope: CostScope | None,
    at: datetime,
    cache: IndicatorsCache | None = None,
) -> Document:
    """Give the evolution of the cost and schedule indices of a project, by scope.

    The point of the day is the computation of ``getProjectIndicators``, read in ``cache`` when one
    is given (US-1720/L2): its instant is the ``computed_at`` of that computation, and the
    ``context`` that of the scope asked, the project's without one. Each scope has its entry
    (US-2420, #3628): the point of a scope is at the instant of its own computation.
    """
    # No revision and no date is named: the reading is of the current day, which is never none.
    asked = IndicatorsReading(scope or PROJECT, at)
    reading = cast("DayReading", day_reading(session, project_id, asked))
    labelled = _labelled_scopes(session, project_id, scope)
    scopes: list[CostScope] = [each for each, _ in labelled]
    thresholds = read_reference_settings(session).index_thresholds
    stored = _stored_points(session, project_id, scopes, thresholds)
    today = day_indicators(session, reading, scopes, cache)
    revision_id = reading.basis.revision_id
    context = today[asked.scope]["context"]
    return {
        "context": context,
        "thresholds": thresholds_document(thresholds),
        "scopes": [
            {
                "scope": str(each),
                "label": label,
                "points": [
                    *stored[each],
                    _point(
                        today[each]["context"]["computed_at"],
                        revision_id,
                        None,
                        classified(today[each], thresholds),
                    ),
                ],
            }
            for each, label in labelled
        ],
    }
