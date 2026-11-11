# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The remaining to commit of a structure as the workbook « Reste à engager » says it (US-1630/L4).

What the exporter ``remaining`` writes (EP-09, "Le format Excel du reste à engager"): the model the
writer of ``excel/`` turns into the workbook, built from the services as the transaction of the task
sees it, writing nothing.

- **The tabs.** One per subproject, by its code, and « Hors sous-projet »; the names are the
  layout's (``tab_names``), the rule the import reads them by. A tab holds the lines of its
  subproject, tasks not completed of a main structure only, a provision never (EP-08's), under the
  tasks that bear them in the order of the plan; a task is listed in each tab it bears a line in,
  one that bears none in « Hors sous-projet ». The choice of the « Tâche » column, in every tab, is
  every task not completed of the structure (#2834), not those the tab bears a line of.
- **The amounts of a header.** The budget and the actual costs of a tab are those of the indicators
  of the revision (``remaining_indicators``: the subproject's balance, or the lines of none and
  the costs imputed to the project alone); the provisions the sum of the provision lines of the
  tab. The remaining to commit, the projection and the gap are formulas of the workbook.
- **The lines.** The budgeted amount and the remaining of the review before as they are kept, the
  days left of a line of labour its quantity times its effort over the hours of a day, the amount
  left of any other its re-estimated amount (``remaining_days``). The designation is the label
  stored; the role of a line of labour, the category of any other, by their codes.
- **The tasks.** « Tâches » gives each task not completed once, its state and its inflation
  coefficient: the mean of the coefficients of the years of the task weighted by their shares
  (``task_coefficient``), the one the analysis converts an amount typed by, so that the formula of
  the workbook gives the amount the application does (#2848).
- **The header.** As the estimate's (``exporting``): the company, the client, the revision by its
  version, the structure by its label, the currency, and the date of the review the order carries,
  the day of the request when it carries none.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.cost_settings.interface import read_reference_settings
from waterfall.core.costs.interface import UNASSIGNED
from waterfall.core.estimate import exporting
from waterfall.core.estimate.costing import basis_of
from waterfall.core.estimate.reading import COMPLETED, budgeted_of, rows_of
from waterfall.core.estimate.remaining.analysing import task_coefficient
from waterfall.core.estimate.remaining.excel.layout import OUTSIDE_KEY
from waterfall.core.estimate.remaining.excel.model import (
    RemainingLine,
    RemainingTab,
    RemainingTask,
    RemainingWorkbook,
)
from waterfall.core.estimate.remaining.reviewing import provisions_of
from waterfall.core.planning.interface import (
    BearingTask,
    NodeFilters,
    Place,
    lineages_of,
    lines_of,
    list_nodes,
)
from waterfall.core.projects.interface import (
    SubprojectFilters,
    SubprojectSort,
    Viewer,
    current_day,
    list_subprojects,
    read_project,
)
from waterfall.core.resource_settings.interface import get_duration_units
from waterfall.core.revisions.interface import read_revision, structure_facts

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.costing import Basis
    from waterfall.core.estimate.remaining.excel.model import TaskState
    from waterfall.core.estimate.tables import EstimateLine
    from waterfall.core.exchanges.interface import ExportOrder
    from waterfall.core.planning.interface import NodeView, TaskView

TASK = "task"
STARTED = "started"
FILE_KIND = "reste-a-engager"
ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class _Pricing:
    """What prices the tasks of a tab: the basis of the revision, and the kind of the structure."""

    basis: Basis
    is_main: bool


@dataclass(slots=True)
class _Bucket:
    """What a tab holds before it is written: its lines by task, and its provisions."""

    lines: dict[UUID, list[RemainingLine]] = field(default_factory=dict[UUID, list[RemainingLine]])
    provisions: Decimal = ZERO


def _line(row: EstimateLine, lineage: UUID, codes: Mapping[UUID, str | None]) -> RemainingLine:
    """Give a line as the workbook says it: its role or its category by code, its figures."""
    code = codes[row.node_id]
    role = code if row.resource_role_id is not None else None
    category = code if row.resource_role_id is None else None
    return RemainingLine(
        lineage=str(lineage),
        role=role,
        category=category,
        label=row.label,
        budget=budgeted_of(row),
        previous=row.previous_reestimated_amount,
        quantity=row.quantity,
        hours=row.hours or ZERO,
        reestimated_amount=row.reestimated_amount,
    )


def remaining_of(
    session: Session,
    order: ExportOrder,
    balances: Mapping[str, tuple[Decimal, Decimal]],
    at: datetime,
) -> tuple[RemainingWorkbook, str]:
    """Give the remaining to commit of the structure of an order, and the name of its file.

    Read in the transaction of the task. ``balances`` gives the budget and the actual costs of each
    subproject, by its identifier, and of the lines of none under ``unassigned``, as the indicators
    of the revision compute them; ``at`` is the instant of the export.
    """
    project_id, revision_id, structure_id = order.project_id, order.revision_id, order.structure_id
    viewer = Viewer(exporting.NOBODY, frozenset())
    project = read_project(session, project_id, viewer)
    revision = read_revision(session, project_id, revision_id, viewer)
    structure = structure_facts(session, project_id, structure_id, lock=False)
    settings = read_reference_settings(session)
    reference = exporting.read_reference(
        session, order, revision.reference_year, marked=revision.status == "marked"
    )
    subprojects = sorted(
        list_subprojects(session, project_id, viewer, SubprojectFilters(), SubprojectSort()),
        key=lambda each: each.code,
    )
    read = list_nodes(
        session, Place(project_id, revision_id, structure_id), NodeFilters(kinds=(TASK,))
    )
    items = [item for item in read.items if item.task is not None]
    facets = {item.node_id: item.task for item in items if item.task is not None}
    bearing = lines_of(session, project_id, [item.node_id for item in items])
    rows = rows_of(session, project_id, [node for held in bearing.values() for node in held])
    by_node = {row.node_id: row for row in rows}
    lineages = lineages_of(session, project_id, list(by_node))
    held_provisions = provisions_of(session, rows)
    pricing = _Pricing(basis_of(session, project_id, revision_id), structure.is_main)
    number = exporting.outline(items)
    codes = {
        node: (
            reference.roles[row.resource_role_id].code
            if row.resource_role_id is not None
            else reference.categories[row.cost_category_id].code
        )
        for node, row in by_node.items()
    }
    buckets: dict[UUID | None, _Bucket] = {}
    tasks_by_id = {item.node_id: item for item in items}
    for item in items:
        if structure.is_main and facets[item.node_id].progress == COMPLETED:
            continue
        listed: set[UUID | None] = set()
        for node in bearing.get(item.node_id, ()):
            row = by_node.get(node)
            if row is None:
                continue
            bucket = buckets.setdefault(row.subproject_id, _Bucket())
            if node in held_provisions:
                bucket.provisions += row.reestimated_amount
                continue
            bucket.lines.setdefault(item.node_id, []).append(_line(row, lineages[node], codes))
            listed.add(row.subproject_id)
        if not listed:
            buckets.setdefault(None, _Bucket()).lines.setdefault(item.node_id, [])

    def tab(code: str, label: str, key: UUID | None) -> RemainingTab:
        bucket = buckets.get(key, _Bucket())
        budget, actual = balances.get(UNASSIGNED if key is None else str(key), (ZERO, ZERO))
        return RemainingTab(
            code,
            label,
            budget,
            actual,
            bucket.provisions,
            tuple(
                _task(tasks_by_id[node], facets[node], number[node], lines, pricing)
                for node, lines in bucket.lines.items()
            ),
        )

    held = exporting.referential(reference, rows)
    book = RemainingWorkbook(
        company=settings.company_name,
        client=project.client or "",
        project=project.label,
        revision=revision.version_name or exporting.IN_PROGRESS_VERSION,
        structure=structure.label,
        review_date=order.review_date or current_day(at),
        currency=settings.currency_code,
        exported_at=at,
        hours_per_day=get_duration_units(session).units.hours_per_day,
        natures=held.natures,
        categories=held.categories,
        roles=held.roles,
        subprojects=tuple(tab(each.code, each.label, each.subproject_id) for each in subprojects),
        outside=tab(OUTSIDE_KEY, "", None),
    )
    name = exporting.file_name(
        project.code, project.label, (revision.version_name, revision_id), FILE_KIND
    )
    return book, name


def _task(
    item: NodeView, task: TaskView, number: str, lines: list[RemainingLine], pricing: _Pricing
) -> RemainingTask:
    """Give a task of a tab: its state, the inflation coefficient of its years, its lines."""
    basis = pricing.basis
    bearer = BearingTask(
        item.node_id,
        basis.revision_id,
        task.label,
        task.start,
        task.finish,
        task.calendar_hours,
        task.progress,
        pricing.is_main,
    )
    coefficient = task_coefficient(basis, bearer, basis.reference_year)
    state: TaskState = STARTED if task.progress == STARTED else "not_started"
    return RemainingTask(
        lineage=str(item.lineage_id),
        number=number,
        label=task.label,
        state=state,
        inflation=coefficient,
        description=task.description or "",
        lines=tuple(lines),
    )
