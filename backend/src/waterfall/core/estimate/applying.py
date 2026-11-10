# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of the workbook of an estimate to a structure, private to the module (US-1550).

The task of the application (``import_apply``) reads the file again — the format prepares it,
before any lock (``read_workbook``) —, locks the structure, and
analyses it again against the structure as it stands under that lock (``importing``), with what
the report the user confirmed holds back (``Confirmed``): a line the report rejected is left out,
as the user read it before confirming (WF-INTF-0080), and a line of the structure absent from the
file goes only if the report announced its removal — not one entered since the analysis —, and
never under a task started or completed since (``kept``, WF-INTF-0100). A line the report accepted
and that the analysis now rejects fails the import, by its reason and its parameters. The hours of
the tasks are judged by that analysis on the structure the import leaves, every write made
(WF-PLA-0010): what the confirmed report says is what is written.

The locks come in the order of the writes of the tree — the revision, the stack, the structure
(``planning.writing``) —: the task holds the current revision ``FOR SHARE``, then the project,
since it judged the import (``exchanges.running._judged``), in its transaction; the structure is
locked after them, and the writer has no stack. A marking or an abandonment, which lock the
revision before the project, wait for the task, and it never waits for them holding the structure.

The lines are written by the functions of the planning, in the transaction of the task: the lines
removed first, one write each — a role that leaves a task never takes its hours —; then those the
file gives another task, those it changes and those it creates, in one write of the tree
(``write_lines``), its structure redated once: written a line at a time, two lines of a task that
exchange their roles, or a line moved under a task whose other line changes its role, would pass
through a task without an hour the end does not leave, which the engine refuses. The lines moved
go after the lines of their task, those created after them. A line created is priced as the entry
prices it, its budgeted amount nought on a project that has a reference revision (WF-DEV-0020); a
line changed keeps its lineage and its budgeted amount. The writer has no session of sign-in: the
undo history receives nothing (WF-IHM-0110); it names the task that applies, which does not suspend
its own writes (``no_background_task_running``).
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.cost_settings.interface import share_natures
from waterfall.core.estimate import importing
from waterfall.core.estimate.writing import HoursJudged, change_line
from waterfall.core.planning.interface import (
    LinesWrite,
    Place,
    Writer,
    delete_node,
    node_versions,
    write_lines,
)
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.excel.reader import WorkbookRead
    from waterfall.core.estimate.importing import Aimed, Analysis, Planned
    from waterfall.core.exchanges.interface import ImportTarget
    from waterfall.core.planning.interface import FacetWrite
    from waterfall.platform.audit import Act

REMOVED = "removed"
PARENT = "parent"


def apply(
    session: Session, target: ImportTarget, read: WorkbookRead, report: Mapping[str, Any], act: Act
) -> None:
    """Write the report of a workbook into the structure of the current revision, judged again."""
    project_id, revision_id, structure_id = (
        target.project_id,
        target.revision_id,
        target.structure_id,
    )
    if revision_id is None or structure_id is None:
        msg = "an estimate is applied to a structure of the current revision"
        raise LookupError(msg)
    # The lock of the natures before that of the structure, as every write of a line (#2615).
    share_natures(session)
    structure_facts(session, project_id, structure_id, lock=True)
    held = importing.aimed(session, target)
    confirmed = confirmed_by(report)
    found = importing.analyse(session, held, read, confirmed)
    _judged_again(found, confirmed)
    place = Place(project_id, revision_id, structure_id)
    writer = Writer(act, None, target.running)
    for node in found.removed:
        version = node_versions(session, project_id, (node,))[node]
        delete_node(session, place, node, version, writer)
    lines = _lines(held, found.planned)
    if lines.moved or lines.changed or lines.created:
        write_lines(session, place, lines, writer)


def confirmed_by(report: Mapping[str, Any]) -> importing.Confirmed:
    """Read what the report confirmed holds back: the rows it rejected, the lines it removes."""
    return importing.Confirmed(
        frozenset((each["sheet"], each["row"]) for each in report.get("rejected", [])),
        frozenset(
            each["lineage_id"]
            for each in report.get("differences", [])
            if each["change"] == REMOVED and each["target"] == importing.LINE
        ),
    )


def _judged_again(found: Analysis, confirmed: importing.Confirmed) -> None:
    """Refuse a line the report accepted that is now rejected, the first by its reason (422)."""
    for each in found.rejected:
        if (each["sheet"], each["row"]) not in confirmed.rejected:
            raise UnprocessableError(each["code"], each["params"])


def _lines(held: Aimed, planned: list[Planned]) -> LinesWrite:
    """Give what the lines accepted write: moved under their task, changed, created."""
    moved: dict[UUID, list[UUID]] = {}
    changed: dict[UUID, Callable[[FacetWrite], None]] = {}
    created: list[tuple[UUID, object]] = []
    for each in planned:
        current = each.current
        if current is None:
            created.append((each.task_id, HoursJudged(each.entry)))
            continue
        if held.bearers[current.node_id] != each.task_id:
            moved.setdefault(each.task_id, []).append(current.node_id)
        if set(each.fields) - {PARENT}:
            changed[current.node_id] = _change(HoursJudged(each.entry))
    return LinesWrite(
        {task_id: tuple(nodes) for task_id, nodes in moved.items()}, changed, tuple(created)
    )


def _change(sent: HoursJudged) -> Callable[[FacetWrite], None]:
    """Give what writes the facet of a line changed: what the file sends of it."""

    def written(write: FacetWrite) -> None:
        change_line(write, sent)

    return written
