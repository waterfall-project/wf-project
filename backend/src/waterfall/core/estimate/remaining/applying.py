# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of the workbook of a remaining to commit to a structure, private (US-1630/L3).

The task of the application (``import_apply``) has the format read the file before any lock
(``prepare``, #2582), judges the import again and creates the current revision if there is none
— a copy of the last marked one, its rates projected and its remaining before the review copied
(EP-06, EP-07, US-1580) —; then this module locks the structure and analyses the file again against
it as it stands under that lock (``analysing``), with what the report the user confirmed holds back
(``Confirmed``): a row it rejected is left out, and a line it counted unchanged is not written,
whatever the structure became since (WF-INTF-0080). A line the report accepted and that the analysis
now rejects fails the import, by its reason and its parameters.

The lines are written in the transaction of the task, the undo history receiving nothing
(WF-IHM-0110): those the file creates and those it changes in one write of the tree
(``write_lines``) — the figures of a line by the function of the re-estimate (``reestimate``), its
mark set; a line that only changes subproject by the function of the estimate, unmarked; a line
created marked once written —; then, for each task the import completes, its last line set to
nought by ``set_line_remaining``, at the date of the review: the line marked, the task completed
by the planning in the same write, a task not started started that day too (WF-RAE-0040,
WF-RAE-0030). The writer names the task that applies, which does not suspend its own writes
(``no_background_task_running``).
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from sqlalchemy import update

from waterfall.core.cost_settings.interface import share_natures
from waterfall.core.estimate import importing
from waterfall.core.estimate.applying import confirmed_by as confirmed_rows
from waterfall.core.estimate.applying import judged_again
from waterfall.core.estimate.interface.remaining import LineRemaining, set_line_remaining
from waterfall.core.estimate.remaining import analysing
from waterfall.core.estimate.remaining.reviewing import reestimate
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.estimate.writing import HoursJudged, change_line
from waterfall.core.planning.interface import (
    LinesWrite,
    Place,
    Writer,
    node_versions,
    write_lines,
)
from waterfall.core.revisions.interface import structure_facts

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.entries import LineEntry
    from waterfall.core.estimate.importing import Planned
    from waterfall.core.estimate.remaining.excel.reader import RemainingRead
    from waterfall.core.exchanges.interface import ImportTarget
    from waterfall.core.planning.interface import FacetWrite
    from waterfall.platform.audit import Act

UPDATED = "updated"


def apply(
    session: Session,
    target: ImportTarget,
    read: RemainingRead,
    report: Mapping[str, Any],
    act: Act,
) -> None:
    """Write the report of a workbook into the structure of the current revision, judged again."""
    project_id, revision_id, structure_id = (
        target.project_id,
        target.revision_id,
        target.structure_id,
    )
    if revision_id is None or structure_id is None:
        msg = "a remaining to commit is applied to a structure of the current revision"
        raise LookupError(msg)
    # The lock of the natures before that of the structure, as every write of a line (#2615).
    share_natures(session)
    structure_facts(session, project_id, structure_id, lock=True)
    held = importing.aimed(session, target)
    confirmed = confirmed_by(report)
    reviewed = analysing.analyse(session, held, read, confirmed)
    judged_again(reviewed.found, confirmed.rejected)
    place = Place(project_id, revision_id, structure_id)
    writer = Writer(act, None, target.running)
    # Only a task the report announced completed is: the others, whatever the analysis now finds.
    closing = {
        node
        for task_id, node in reviewed.closing.items()
        if str(held.task_lineages[task_id]) in confirmed.completed
    }
    lines = _lines(reviewed.found.planned, closing)
    if lines.changed or lines.created:
        written = write_lines(session, place, lines, writer)
        created = {each.node_id for each in written.nodes if each.kind == importing.LINE}
        _mark(session, project_id, created - set(lines.changed), act)
    by_node = {
        each.current.node_id: each.entry
        for each in reviewed.found.planned
        if each.current is not None and each.current.node_id in closing
    }
    for node, entry in by_node.items():
        counter = node_versions(session, project_id, (node,))[node]
        sent = LineRemaining(replace(entry, lock_version=counter), None, reviewed.review_date)
        set_line_remaining(session, place, node, sent, writer)


def confirmed_by(report: Mapping[str, Any]) -> analysing.Confirmed:
    """Read what the report confirmed holds back: rejected rows, updated lines, completed tasks."""
    rows = confirmed_rows(report)
    return analysing.Confirmed(
        rows.rejected,
        rows.removed,
        frozenset(
            each["lineage_id"]
            for each in report.get("differences", [])
            if each["change"] == UPDATED and each["target"] == importing.LINE
        ),
        frozenset(each["lineage_id"] for each in report.get("completed_tasks", [])),
    )


def _lines(planned: list[Planned], closing: set[UUID]) -> LinesWrite:
    """Give what the lines accepted write but those that complete a task: changed, created."""
    changed: dict[UUID, Callable[[FacetWrite], None]] = {}
    created: list[tuple[UUID, object]] = []
    for each in planned:
        current = each.current
        if current is None:
            created.append((each.task_id, HoursJudged(each.entry)))
        elif current.node_id not in closing:
            changed[current.node_id] = _change(each.entry, marked=analysing.writes_figures(each))
    return LinesWrite({}, changed, tuple(created))


def _change(sent: LineEntry, *, marked: bool) -> Callable[[FacetWrite], None]:
    """Give what writes the facet of a line changed: re-estimated, or only moved to a subproject."""

    def written(write: FacetWrite) -> None:
        if marked:
            reestimate(write, sent, None)
        else:
            change_line(write, sent)

    return written


def _mark(session: Session, project_id: UUID, created: set[UUID], act: Act) -> None:
    """Mark the lines the file created as re-estimated, at the instant of the application."""
    if not created:
        return
    session.execute(
        update(EstimateLine)
        .where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(created))
        .values(reestimated_at=act.at)
    )
