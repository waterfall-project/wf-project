# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The facet estimate line of a node: what the planning asks of it, by the hooks of its kind.

The planning knows no facet but the task's: it asks the hooks the estimate registers for the kind
``estimate_line`` (``register_facet``, EP-06 and EP-07, "Les points d'extension") — read the facets
of the lines named (``read_lines``), create the facet of a line created (``create_line``), copy the
lines into a revision opened (``copy_lines``), delete them with their nodes (``delete_lines``),
give the calendars of the roles of the lines of tasks (``line_calendars``), their snapshot and
their restoration for the history (``snapshot_lines``, ``restore_lines``), price again the lines of
the tasks redated (``reinflate_lines``), their figures for the totals (``line_totals``), their
filters and their sort (``line_filters``, ``line_sort``), what a computed value of a line depends
on (``line_dependencies``), and the lines a move gives another task, whose roles must leave it an
hour (``judge_moved_lines``, WF-PLA-0010; US-1490/L4), and the cells a paste gives a line, judged
and written (``judge_line_cell``, ``write_line_cell``, ``pasting``; US-1560/L1).

The copy of a line keeps its figures and its amounts, and takes for its budgeted amount that of the
line of the same lineage in the reference revision, nought without one; null on a project without a
reference, read as the re-estimated amount (EP-07, "Ce que le cadrage décide"). Its rates and their
projection when the year changes are US-1500's.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

from sqlalchemy import delete, insert, inspect, select

from waterfall.core.cost_settings.interface import share_natures
from waterfall.core.estimate.costing import judge_working_hours
from waterfall.core.estimate.pasting import judge_line_cell, write_line_cell
from waterfall.core.estimate.pricing import Amount, dependencies_of
from waterfall.core.estimate.reading import (
    budgeted_of,
    filter_lines,
    read_lines,
    rows_of,
    sort_lines,
    totals_of,
)
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.estimate.writing import create_line, reprice
from waterfall.core.planning.interface import (
    FacetHooks,
    FacetState,
    lineages_of,
    lines_of,
    lines_of_revision,
)
from waterfall.core.projects.interface import project_facts
from waterfall.core.resource_settings.interface import role_calendars

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.history.interface import JsonValue
    from waterfall.core.planning.interface import BearingTask
    from waterfall.core.revisions.interface import RevisionCopy
    from waterfall.platform.audit import Act

NOUGHT = Decimal("0.00")
# The columns a restoration leaves to the line, and those it writes as the restoring does.
KEPT = frozenset({"project_id", "node_id", "kind", "created_at", "created_by"})
STAMPED = frozenset({"lock_version", "updated_at", "updated_by"})
# The computed values of a line, by the amount each names.
AMOUNTS = {
    "estimate_line.base_amount": Amount.BASE,
    "estimate_line.budgeted_amount": Amount.BUDGETED,
    "estimate_line.reestimated_amount": Amount.REESTIMATED,
}


def _columns(row: EstimateLine) -> dict[str, object]:
    """Give the columns of a line, by name."""
    return {column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs}


def copy_lines(copy: RevisionCopy) -> None:
    """Copy the lines of the nodes copied into the revision opened (WF-DAT-0010).

    Under the nodes the planning copied (``copy.identifiers``), at their first version, with the
    stamp of the opening; the budgeted amount by the lineage in the reference revision.
    """
    session, ids = copy.session, copy.identifiers
    rows = [row for row in rows_of(session, copy.project_id, list(ids)) if row.node_id in ids]
    if not rows:
        return
    reference = project_facts(session, copy.project_id).reference_revision_id
    lineages = lineages_of(session, copy.project_id, [row.node_id for row in rows])
    budgets: dict[UUID, Decimal] = {}
    if reference is not None:
        held = lines_of_revision(session, copy.project_id, reference)
        by_node = {node: lineage for lineage, node in held.items()}
        budgets = {
            by_node[line.node_id]: budgeted_of(line)
            for line in rows_of(session, copy.project_id, list(held.values()))
        }
    session.execute(
        insert(EstimateLine),
        [
            {
                **_columns(row),
                "node_id": ids[row.node_id],
                "budgeted_amount": (
                    None if reference is None else budgets.get(lineages[row.node_id], NOUGHT)
                ),
                "lock_version": 1,
                "created_at": copy.at,
                "created_by": copy.author,
                "updated_at": copy.at,
                "updated_by": copy.author,
            }
            for row in rows
        ],
    )


def delete_lines(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> None:
    """Delete the facets of the lines deleted, before their nodes, which they follow anyway."""
    session.execute(
        delete(EstimateLine)
        .where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(list(node_ids)))
        .execution_options(synchronize_session=False)
    )


def line_calendars(
    session: Session, project_id: UUID, task_ids: Collection[UUID]
) -> dict[UUID, set[UUID]]:
    """Give the calendars of the roles of the labour lines of each task named (WF-PLA-0010)."""
    lines = lines_of(session, project_id, task_ids)
    bearer = {line: task for task, held in lines.items() for line in held}
    found: dict[UUID, set[UUID]] = {task: set() for task in task_ids}
    if not bearer:
        return found
    roles = dict(
        session.execute(
            select(EstimateLine.node_id, EstimateLine.resource_role_id).where(
                EstimateLine.project_id == project_id,
                EstimateLine.node_id.in_(list(bearer)),
                EstimateLine.resource_role_id.is_not(None),
            )
        ).all()
    )
    calendars = role_calendars(session, {role for role in roles.values() if role is not None})
    for line, role in roles.items():
        if role is not None and role in calendars:
            found[bearer[line]].add(calendars[role])
    return found


def _json(value: object) -> JsonValue:
    """Give a column of a line as JSON holds it: identifiers, decimals and instants as text."""
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if value is None or isinstance(value, bool | int | str):
        return value
    msg = f"a column of a line holds no {type(value).__name__}"
    raise TypeError(msg)


def snapshot_lines(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, FacetState]:
    """Give the facets of the lines named as the history keeps them, each named by its label."""
    return {
        row.node_id: FacetState(
            row.label, {key: _json(value) for key, value in _columns(row).items()}
        )
        for row in rows_of(session, project_id, node_ids)
    }


# The columns of a line kept as text, by the type they are read back in.
_UUIDS = frozenset(
    {"project_id", "node_id", "cost_category_id", "resource_role_id", "subproject_id"}
    | {"created_by", "updated_by"}
)
_INSTANTS = frozenset({"created_at", "updated_at", "reestimated_at"})
_TEXTS = frozenset({"kind", "label", "remaining_reason"})


def _typed(name: str, value: JsonValue) -> object:
    """Give a column of a line kept as JSON in the type of its table."""
    if not isinstance(value, str) or name in _TEXTS:
        return value
    if name in _UUIDS:
        return UUID(value)
    if name in _INSTANTS:
        return datetime.fromisoformat(value)
    return Decimal(value)


def restore_lines(
    session: Session, project_id: UUID, rows: Mapping[UUID, JsonValue], act: Act
) -> None:
    """Write back the facets of lines a snapshot kept, at the counter that follows, by ``act``."""
    held = {row.node_id: row for row in rows_of(session, project_id, rows)}
    for node_id, kept in rows.items():
        columns = {
            name: _typed(name, value)
            for name, value in cast("Mapping[str, JsonValue]", kept).items()
        }
        line = held.get(node_id)
        if line is None:
            counter = cast("int", columns["lock_version"]) + 1
            session.add(
                EstimateLine(
                    **{
                        **columns,
                        "lock_version": counter,
                        "updated_at": act.at,
                        "updated_by": act.author,
                    }
                )
            )
            continue
        for name, value in columns.items():
            if name not in KEPT | STAMPED:
                setattr(line, name, value)
        line.lock_version += 1
        line.updated_at, line.updated_by = act.at, act.author
    session.flush()


def reinflate_lines(
    session: Session, project_id: UUID, lines: Mapping[UUID, BearingTask]
) -> frozenset[UUID]:
    """Price again the lines of the tasks redated or written; give those whose amounts moved."""
    return reprice(session, project_id, lines)


def line_dependencies(
    session: Session, project_id: UUID, node_id: UUID, field: str
) -> tuple[str, ...] | None:
    """Name what a computed value of a line depends on (``getComputedValueDependencies``).

    The category of a labour line, its role's; its amounts, as ``pricing`` names them. None for a
    value the server does not compute for the line: the figures of a provision line are EP-08's.
    """
    found = rows_of(session, project_id, (node_id,))
    if not found:
        return None
    labour = found[0].resource_role_id is not None
    if field == "estimate_line.cost_category_id":
        return ("resource_role",) if labour else None
    amount = AMOUNTS.get(field)
    return None if amount is None else dependencies_of(amount, labour=labour)


def judge_moved_lines(
    session: Session, project_id: UUID, lines: Mapping[UUID, BearingTask]
) -> None:
    """Refuse a labour line moved whose role would leave the task receiving it without an hour.

    Judged once placed, on the roles of every labour line the task now bears, the first line
    concerned in the order given; the roles and the task named (``TASK_WITHOUT_WORKING_HOURS``).
    """
    roles = dict(
        session.execute(
            select(EstimateLine.node_id, EstimateLine.resource_role_id).where(
                EstimateLine.project_id == project_id,
                EstimateLine.node_id.in_(list(lines)),
                EstimateLine.resource_role_id.is_not(None),
            )
        ).all()
    )
    for line, bearer in lines.items():
        role = roles.get(line)
        if role is not None:
            judge_working_hours(session, (project_id, bearer, line), role)


line_filters = filter_lines
line_sort = sort_lines
line_totals = totals_of

# The hooks of the kind ``estimate_line``, which the interface registers in the planning.
LINE_FACET = FacetHooks(
    read=read_lines,
    copy=copy_lines,
    delete=delete_lines,
    calendars=line_calendars,
    create=create_line,
    snapshot=snapshot_lines,
    restore=restore_lines,
    reinflate=reinflate_lines,
    totals=totals_of,
    filters=filter_lines,
    sort=sort_lines,
    dependencies=line_dependencies,
    moved=judge_moved_lines,
    judge_cell=judge_line_cell,
    write_cell=write_line_cell,
    before_lock=share_natures,
)
