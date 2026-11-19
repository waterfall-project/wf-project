# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of a revision as the indicators read them (EP-10, "Modules"; US-1660/L3).

``lines_for_indicators`` gives each line of the main structure of a revision, the provisions left
out: its node, the task that bears it — its node, its lineage, the risk it comes from —, its
subproject in that revision, its budgeted and re-estimated amounts, its payment delay, and its task
as a spreading sees it, on the calendar it is worked on, its role's for a labour line, its task's
otherwise. A marked revision is read on the images its marking kept of the calendars of the roles
(``kept_reference``); its dates are those its marking froze. ``planned_value_at`` is the planned
value of lines at the end of a day, by the pure spreading of EP-07, the share of each line rounded
to the cent, so that the planned value of a scope is the sum of those of its lines; the
``planned_value`` of EP-07 is this one on the lines of the reference (#3566).

The lines and their planned value are read by ``lining``, private to the module, which this file
re-exports: the estimate does not import its own interface (#3591).

``lines_stamp``, the number of the lines of a revision and the last instant one was written, which
the key of the cache of the indicators reads (EP-10, "Le cache"), is declared here and filled by
US-1720/L2.

Filled by US-1660/L3, the only lot of EP-10 that writes the ``__init__`` of the estimate.
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.estimate.lining import (
    IndicatorLine,
    LinesStamp,
    lines_for_indicators,
    planned_value_at,
)
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import revision_lines
from waterfall.platform.database import among

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

# The types are the interface's own to give: only a name in ``__all__`` is re-exported.
__all__ = [
    "IndicatorLine",
    "LinesStamp",
    "lines_for_indicators",
    "lines_stamp",
    "planned_value_at",
]


def lines_stamp(session: Session, project_id: UUID, revision_id: UUID) -> LinesStamp:
    """Give the number of the lines of a revision and the last instant one was written.

    The lines of every structure of the revision, whatever their kind, but the bases of its
    differentials, which no indicator reads (US-3050): a re-estimate, a rate or an inflation that
    prices a line again writes its ``updated_at`` without passing by a grid.
    """
    nodes = list(revision_lines(session, project_id, revision_id, bases=False))
    if not nodes:
        return LinesStamp(0, None)
    count, last = session.execute(
        select(func.count(), func.max(EstimateLine.updated_at)).where(
            EstimateLine.project_id == project_id, among(EstimateLine.node_id, nodes)
        )
    ).one()
    return LinesStamp(count, last)
