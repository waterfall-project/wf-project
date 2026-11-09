# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of the workbook of an estimate to a structure, private to the module (US-1550).

The task of the application (``import_apply``) reads the file again, locks the structure, and
analyses it again against the structure as it stands under that lock (``importing``): a line the
report accepted and that the analysis now rejects fails the import, by its reason and its
parameters; a line the report rejected is left out, as the user read it before confirming
(WF-INTF-0080). The report is what is written: a line of the structure absent from the file goes
only if the report announced its removal — not one entered since the analysis —, and never under a
task started or completed since (``kept``, WF-INTF-0100).

The lines are written by the functions of the entry, each in the frame of a write of the tree —
its revision judged, the lock of its structure, the structure redated and its lines priced again —
(EP-07, "Le format Excel du devis"), in the transaction of the task: the lines removed first, then
those the file gives another task, moved together under each, then those it changes, then those it
creates, at the end of the lines of their task. A line created is priced as the entry prices it,
its budgeted amount nought on a project that has a reference revision (WF-DEV-0020); a line
changed keeps its lineage and its budgeted amount. The writer has no session of sign-in: the undo
history receives nothing (WF-IHM-0110); it names the task that applies, which does not suspend its
own writes (``no_background_task_running``). Each write replays the whole structure: an import
replays it once per line it writes.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.estimate import importing
from waterfall.core.estimate.excel.reader import read_workbook
from waterfall.core.estimate.writing import change_line
from waterfall.core.planning.interface import (
    FacetChange,
    NodeCreation,
    NodeMoving,
    Place,
    Writer,
    create_line_node,
    delete_node,
    move_nodes,
    node_versions,
    write_facet,
)
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.entries import LineEntry
    from waterfall.core.estimate.importing import Aimed, Analysis, Planned
    from waterfall.core.exchanges.interface import ImportTarget
    from waterfall.core.planning.interface import FacetWrite
    from waterfall.platform.audit import Act

REMOVED = "removed"
PARENT = "parent"


def apply(
    session: Session, target: ImportTarget, content: bytes, report: Mapping[str, Any], act: Act
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
    read = read_workbook(content)
    structure_facts(session, project_id, structure_id, lock=True)
    held = importing.aimed(session, target)
    found = importing.analyse(session, held, read)
    planned = _judged_again(found, report)
    place = Place(project_id, revision_id, structure_id)
    writer = Writer(act, None, target.running)
    for node in _removed(held, found, report):
        delete_node(session, place, node, _version(session, project_id, node), writer)
    _move(session, place, held, planned, writer)
    for each in planned:
        if each.current is not None and set(each.fields) - {PARENT}:
            _change(session, place, each.current.node_id, each.entry, writer)
    for each in planned:
        if each.current is None:
            creation = NodeCreation(
                each.task_id, None, after_given=False, kind=importing.LINE, facet=each.entry
            )
            create_line_node(session, place, creation, writer)


def _judged_again(found: Analysis, report: Mapping[str, Any]) -> list[Planned]:
    """Refuse a line the report accepted that is now rejected; give the others the report accepts.

    The first such rejection the analysis finds names its reason (422).
    """
    rejected = {(each["sheet"], each["row"]) for each in report.get("rejected", [])}
    for each in found.rejected:
        if (each["sheet"], each["row"]) not in rejected:
            raise UnprocessableError(each["code"], each["params"])
    return [each for each in found.planned if (each.line.sheet, each.line.row) not in rejected]


def _removed(held: Aimed, found: Analysis, report: Mapping[str, Any]) -> list[UUID]:
    """Give the lines to remove: absent from the file, announced removed, under a task unstarted."""
    announced = {
        each["lineage_id"]
        for each in report.get("differences", [])
        if each["change"] == REMOVED and each["target"] == importing.LINE
    }
    lineages = {line.node_id: str(lineage) for lineage, line in held.lines.items()}
    return [
        node
        for node in found.left
        if lineages[node] in announced and not importing.started(held, node)
    ]


def _version(session: Session, project_id: UUID, node_id: UUID) -> int:
    """Read the counter of a node as it is now, which an earlier write may have moved."""
    return node_versions(session, project_id, (node_id,))[node_id]


def _move(
    session: Session, place: Place, held: Aimed, planned: list[Planned], writer: Writer
) -> None:
    """Move the lines the file gives another task, together under each, after its lines."""
    moving: dict[UUID, list[UUID]] = {}
    for each in planned:
        current = each.current
        if current is not None and held.bearers[current.node_id] != each.task_id:
            moving.setdefault(each.task_id, []).append(current.node_id)
    for task_id, nodes in moving.items():
        counter = structure_facts(session, place.project_id, place.structure_id, lock=True)
        moved = NodeMoving(
            tuple(nodes), task_id, None, after_given=False, lock_version=counter.lock_version
        )
        move_nodes(session, place, moved, writer)


def _change(
    session: Session, place: Place, node_id: UUID, entry: LineEntry, writer: Writer
) -> None:
    """Write what the file changes of a line, at its counter as it is now (``write_facet``)."""

    def written(write: FacetWrite) -> None:
        change_line(write, entry)

    change = FacetChange(node_id, _version(session, place.project_id, node_id), written)
    write_facet(session, place, change, writer)
