# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The part of the estimate in the merge of a differential (WF-REV-0050; EP-08, "Modules").

Its part of ``register_merge``, after the planning's, whose plan says where each line stands
(``merged_lines``): a line of the differential the main structure lacks is added; one of the main
structure the differential lacks is removed, unless its task is kept, started, which keeps its lines
(their remaining to commit brought to nought by the application); one of both is updated by the
columns the differential designates — its label, its category, its role, its quantity, its hours,
its unit disbursement, its subproject, its delay of payment, in the order of ``NodeColumn`` — and by
its parent when it changes task. They become its reference figures, and its current ones when its
task is not started and nobody re-estimated it: the report does not tell the two apart (US-0701/L1,
M-08). What refuses the merge, of the lines: a task whose lines, once merged, would name roles whose
calendars share no hour in the week (``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010), judged as the
update of a differential judges it (``hourless_tasks``), before the end of the planning replays the
engine; the application, which judged the report before it wrote, judges none.

The provision lines stay out of the comparison (#4008): a risk alone writes them, on the main
structure, and a differential does not take them up at its opening; one a differential would still
hold is ignored. A provision line whose task the merge removes goes to another task, and the report
signals it by an update of its parent (WF-RIS-0010; #789).

The application (``StructureMerging.applying``) writes what the same computation finds
(``merged``): the nodes of the lines by the planning, their facets here — a line added a copy of
the differential's, a line designated its columns, its figures of reference and its budgeted
amount, its current figures too while its task is not started and nobody re-estimated it —, and
the lines of the started tasks the merge keeps and completes brought to a remaining of nought.

Written by US-2560/L1; the application by US-2560/L2.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.estimate.costing import TASK_WITHOUT_WORKING_HOURS, hourless_tasks
from waterfall.core.estimate.merged import LineMerged, write_lines
from waterfall.core.estimate.reading import line_rows
from waterfall.core.planning.interface import merged_lines
from waterfall.core.resource_settings.interface import role_calendars
from waterfall.core.revisions.interface import MergePart

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from uuid import UUID

    from waterfall.core.estimate.reading import LineRow
    from waterfall.core.planning.interface import MergedLine, MergedLines
    from waterfall.core.revisions.interface import StructureMerging

type Json = dict[str, Any]
LINE = "estimate_line"
# The columns of a line a differential designates, as ``NodeColumn`` names them, and their field.
COLUMNS = (
    ("label", "label"),
    ("cost_category", "cost_category_id"),
    ("resource_role", "resource_role_id"),
    ("quantity", "quantity"),
    ("hours", "hours"),
    ("unit_disbursement", "unit_disbursement"),
    ("subproject", "subproject_id"),
    ("payment_delay_days", "payment_delay_days"),
)


def _difference(change: str, line: MergedLine | None, label: str, fields: list[str]) -> Json:
    """Give a difference of a line (``ImportDifference``), its lineage none for one added."""
    return {
        "change": change,
        "target": LINE,
        "lineage_id": None if line is None else str(line.lineage_id),
        "label": label,
        "predecessor_label": None,
        "fields": fields,
    }


def _fields(held: tuple[MergedLine, LineRow], sent: tuple[MergedLine, LineRow]) -> list[str]:
    """Name what the differential changes of a line of the main structure, then its parent."""
    (line, old), (other, new) = held, sent
    fields = [name for name, column in COLUMNS if getattr(old, column) != getattr(new, column)]
    if line.task_lineage_id != other.task_lineage_id:
        fields.append("parent")
    return fields


def merge_lines(merging: StructureMerging) -> MergePart:
    """Give the part of the estimate in a merge: lines added, updated, removed, provisions moved.

    In the order of the plan of the differential, then those of the main structure; and, for the
    report, the tasks the merge would leave without a working hour.
    """
    where = merged_lines(merging)
    nodes = [each.node_id for each in (*where.main, *where.amendment)]
    rows = {row.node_id: row for row in line_rows(merging.session, merging.project_id, nodes)}
    held = {each.lineage_id: each for each in where.main if not each.is_provision}
    sent = {each.lineage_id: each for each in where.amendment if not each.is_provision}
    differences: list[Json] = []
    written: list[LineMerged] = []
    for lineage, line in sent.items():
        found = held.get(lineage)
        new = rows[line.node_id]
        if found is None:
            differences.append(_difference("added", None, new.label, []))
            written.append(LineMerged(line.node_id, None, frozenset(), line.task_lineage_id))
            continue
        fields = _fields((found, rows[found.node_id]), (line, new))
        if fields:
            differences.append(_difference("updated", found, new.label, fields))
            designated = frozenset(fields)
            written.append(
                LineMerged(line.node_id, found.node_id, designated, line.task_lineage_id)
            )
    for line in where.main:
        label = rows[line.node_id].label
        if line.is_provision:
            if line.task_lineage_id in where.moved:
                differences.append(_difference("updated", line, label, ["parent"]))
        elif line.lineage_id not in sent and line.task_lineage_id not in where.kept:
            differences.append(_difference("removed", line, label, []))
    if merging.applying:
        write_lines(merging, where, written)
        return MergePart(differences=tuple(differences))
    return MergePart(
        differences=tuple(differences), refusals=tuple(_hourless(merging, where, rows))
    )


def _hourless(
    merging: StructureMerging, where: MergedLines, rows: Mapping[UUID, LineRow]
) -> Iterator[Json]:
    """Refuse each task the merge leaves whose roles' calendars share no hour in the week.

    The roles of the lines each task bears once merged — the differential's lines of its task, the
    own lines of a started task kept —, intersected day by day as the update judges them
    (``hourless_tasks``, WF-PLA-0010); in the order of the plan, each task by its node in the main
    structure, or by its lineage for a task the differential adds, as the update names a task the
    main structure adds (``ProblemImportedTask``).
    """
    sent = {each.lineage_id for each in where.amendment}
    roles: dict[UUID, set[UUID]] = {task: set() for task in where.tasks}
    borne = [each for each in where.amendment if not each.is_provision]
    borne += [
        each
        for each in where.main
        if each.task_lineage_id in where.kept
        and not each.is_provision
        and each.lineage_id not in sent
    ]
    for line in borne:
        role = rows[line.node_id].resource_role_id
        if role is not None and line.task_lineage_id in roles:
            roles[line.task_lineage_id].add(role)
    calendars = role_calendars(merging.session, {role for held in roles.values() for role in held})
    for task, named in hourless_tasks(merging.session, roles, calendars):
        node, label = where.tasks[task]
        bearer: Json = (
            {"lineage_id": str(task), "label": label}
            if node is None
            else {"project_id": str(merging.project_id), "node_id": str(node), "label": label}
        )
        yield {
            "code": TASK_WITHOUT_WORKING_HOURS,
            "params": {"resource_roles": named, "tasks": [bearer]},
        }
