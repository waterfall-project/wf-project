# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The estimate of a structure as the workbook « Devis » says it, private to the module (US-1550).

What the exporter ``estimate`` writes (EP-07, "Le format Excel du devis"): the model the writer of
``excel/`` turns into the workbook, built from the service as the transaction of the task sees it,
writing nothing.

- **The tabs.** A task belongs to the tab of the nearest order item (« poste ») it or an ancestor
  bears, else to the tab of the nearest work package (« lot ») — the lines of the subtree of its
  task outside those of its postes —, else to « Hors lot » (WF-PLA-0170). A tab is numbered by its
  place in the work breakdown, « 1.1 » for the first order item of the first work package, « 1 » for
  the work package; a lot or a poste a marked revision bears and the breakdown deleted since is
  numbered after those that remain.
- **The reference.** A current revision follows the reference for its roles and its categories — the
  active ones and those its lines employ —; a marked one reads its images (``kept_reference``), or
  the reference when it keeps none (marked before US-1500). A category is designated by its
  accounting code, not its technical code (WF-REF-0040, #2688). The rate of a category of labour is
  the one the revision is priced at (``held_rates``): its own, else the reference's for its year.
- **The lines.** Each as the facet keeps it, in the order of the plan; « Montant Waterfall » is its
  re-estimated amount, inflation included (WF-DEV-0050). The designation is the label stored, so
  that the import finds the line as it was; the role of a line of labour, the category of any
  other.
- **The header.** The company and the currency of the installation (WF-EXP-0020, WF-REF-0140), the
  client of the project (WF-PRJ-0080), the revision by its version — a revision in progress has
  none: « En cours » —, the structure by its label.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.cost_settings.interface import read_cost_categories, read_reference_settings
from waterfall.core.estimate.costing import held_rates
from waterfall.core.estimate.excel.model import (
    Category,
    Estimate,
    Line,
    Lot,
    Nature,
    Role,
    Subproject,
    Tab,
    Task,
)
from waterfall.core.estimate.excel.writer import NO_LOT
from waterfall.core.estimate.imaging import kept_reference
from waterfall.core.estimate.importing import reference_of
from waterfall.core.estimate.reading import rows_of
from waterfall.core.planning.interface import (
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
    WorkBreakdownFilters,
    list_subprojects,
    read_project,
    read_work_breakdown,
    work_breakdown_items,
)
from waterfall.core.revisions.interface import read_revision, structure_facts
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from datetime import datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.excel.model import NatureKind
    from waterfall.core.estimate.tables import EstimateLine
    from waterfall.core.exchanges.interface import ExportOrder
    from waterfall.core.planning.interface import NodeView

TASK = "task"
IN_PROGRESS_VERSION = "En cours"
IN_PROGRESS_FILE = "en-cours"
NOBODY = UUID(int=0)
# The kinds of a nature, as the reference says them, and as the workbook does.
KINDS: Mapping[str, NatureKind] = {
    "labor": "labour",
    "non_labor": "disbursement",
    "provision": "provision",
}
KIND_ORDER = {"labour": 0, "disbursement": 1, "provision": 2}
_NOT_IN_A_NAME = re.compile(r"[^A-Za-z0-9._-]+")
# What a task falls under: the order item or the work package it is read by, none outside any lot.
POSTE = "poste"
LOT = "lot"
OUTSIDE = "outside"

type Under = tuple[str, UUID | None]


@dataclass(frozen=True, slots=True)
class _RoleInfo:
    code: str
    label: str
    department: str
    category_id: UUID
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class _CategoryInfo:
    code: str  # the accounting code, which designates the category in the workbook (#2688)
    label: str
    nature: str
    kind: NatureKind
    is_active: bool


@dataclass(frozen=True, slots=True)
class Reference:
    """The roles and the categories a revision is read on, by identifier, and the rates it holds."""

    roles: dict[UUID, _RoleInfo]
    categories: dict[UUID, _CategoryInfo]
    rates: dict[UUID, Decimal]


@dataclass(frozen=True, slots=True)
class _Numbering:
    """The number and the label of each work package and order item, and the lot of each item."""

    numbers: dict[UUID, str]
    labels: dict[UUID, str]
    lots: dict[UUID, UUID | None]


def _slug(text: str) -> str:
    """Give a text as a part of a file name: its accents dropped, the rest of its signs folded."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return _NOT_IN_A_NAME.sub("_", plain).strip("_")


def file_name(
    code: str | None, label: str, version: tuple[str | None, UUID], kind: str = "devis"
) -> str:
    """Name the file of an export: ``<code or label of the project>-<version>-<kind>.xlsx``.

    ``kind`` is ``devis`` for the estimate, ``reste-a-engager`` for the remaining to commit.

    ``version`` is the name of the version of the revision, none if it is the current one, and the
    identifier of the revision: a version whose name leaves nothing in a file name, or reads as the
    current revision's, is named by the identifier, so that no two revisions share a file name.
    """
    project = _slug(code or "") or _slug(label) or "projet"
    name, revision_id = version
    if name is None:
        part = IN_PROGRESS_FILE
    else:
        part = _slug(name)
        if not part or part.casefold() == IN_PROGRESS_FILE:
            part = str(revision_id)
    return f"{project}-{part}-{kind}.xlsx"


def _category(
    nature: str, kind: str, names: tuple[str, str], *, active: bool = True
) -> _CategoryInfo:
    """Give a category as it is read: its accounting code, its label, its nature, if active."""
    code, label = names
    return _CategoryInfo(code, label, nature, KINDS[kind], active)


def _categories_of(session: Session, category_ids: Iterable[UUID]) -> dict[UUID, _CategoryInfo]:
    """Read categories of the reference by identifier, active or not."""
    return {
        each.cost_category_id: _category(
            each.cost_type_label,
            each.cost_type_kind,
            (each.accounting_code, each.label),
            active=each.is_active,
        )
        for each in read_cost_categories(session, list(category_ids))
    }


def read_reference(session: Session, order: ExportOrder, year: int, *, marked: bool) -> Reference:
    """Read the roles, the categories and the rates the revision of the order is read on."""
    project_id, revision_id = order.project_id, order.revision_id
    kept = kept_reference(session, project_id, revision_id) if marked else None
    if kept is not None and (kept.resource_roles or kept.cost_categories):
        roles = {
            role.resource_role_id: _RoleInfo(
                role.code, role.label, role.org_node_label, role.cost_category_id
            )
            for role in kept.resource_roles
        }
        categories = {
            each.cost_category_id: _category(
                each.cost_type_label, each.cost_type_kind, (each.accounting_code, each.label)
            )
            for each in kept.cost_categories
        }
        missing = {role.category_id for role in roles.values()} - categories.keys()
        categories.update(_categories_of(session, missing))
    else:
        held = reference_of(session, project_id)
        roles = {
            key: _RoleInfo(
                each.code, each.label, each.org_node_label, each.cost_category_id, each.is_active
            )
            for key, each in held.roles_by_id.items()
        }
        categories = {
            each.cost_category_id: _category(
                each.cost_type_label,
                each.cost_type_kind,
                (each.accounting_code, each.label),
                active=each.is_active,
            )
            for each in held.categories.values()
        }
    labour = [key for key, each in categories.items() if each.kind == "labour"]
    rates = held_rates(session, (project_id, revision_id, year), labour)
    return Reference(roles, categories, rates)


def _numbering(session: Session, project_id: UUID, borne: Collection[UUID]) -> _Numbering:
    """Give the number of each element of the work breakdown, those only a marked one bears last."""
    read = read_work_breakdown(session, project_id, WorkBreakdownFilters())
    numbers: dict[UUID, str] = {}
    labels: dict[UUID, str] = {}
    lots: dict[UUID, UUID | None] = {}
    counts: dict[UUID, int] = {}
    for rank, package in enumerate(read.work_packages, start=1):
        key = package.work_package_id
        numbers[key], labels[key], lots[key] = str(rank), package.label, None
        counts[key] = len(package.order_items)
        for count, item in enumerate(package.order_items, start=1):
            numbers[item.order_item_id] = f"{rank}.{count}"
            labels[item.order_item_id] = item.label
            lots[item.order_item_id] = key
    every = work_breakdown_items(session, project_id)
    # An element is read when a task bears it, or bears one of its order items: a poste deleted
    # with its lot keeps the lot it was numbered under.
    wanted = {*borne, *(every[key].work_package_id for key in borne if key in every)} - {None}
    gone = {key: each for key, each in every.items() if key in wanted and key not in numbers}
    last = len(read.work_packages)
    for key, each in gone.items():
        labels[key], lots[key] = each.label, each.work_package_id
        if each.work_package_id is None:
            last += 1
            counts[key], numbers[key] = 0, str(last)
    for key, each in gone.items():
        if each.work_package_id is not None:
            counts[each.work_package_id] = counts.get(each.work_package_id, 0) + 1
            parent = numbers.get(each.work_package_id, "")
            numbers[key] = f"{parent}.{counts[each.work_package_id]}".lstrip(".")
    return _Numbering(numbers, labels, lots)


def outline(items: list[NodeView]) -> dict[UUID, str]:
    """Give the number of each task by its place in the outline, « 1 », « 1.2 »…, in plan order."""
    numbers: dict[UUID, str] = {}
    counts: dict[UUID | None, int] = {}
    for item in items:
        counts[item.parent_id] = counts.get(item.parent_id, 0) + 1
        parent = None if item.parent_id is None else numbers.get(item.parent_id)
        rank = counts[item.parent_id]
        numbers[item.node_id] = str(rank) if parent is None else f"{parent}.{rank}"
    return numbers


def _placed(items: list[NodeView]) -> dict[UUID, Under]:
    """Give what each task falls under: the nearest order item or work package at or above it."""
    by_id = {item.node_id: item for item in items}
    placed: dict[UUID, Under] = {}
    for item in items:
        found: Under = (OUTSIDE, None)
        node: NodeView | None = item
        while node is not None and node.task is not None:
            if node.task.order_item_id is not None:
                found = (POSTE, node.task.order_item_id)
                break
            if node.task.work_package_id is not None:
                found = (LOT, node.task.work_package_id)
                break
            node = None if node.parent_id is None else by_id.get(node.parent_id)
        placed[item.node_id] = found
    return placed


def _line(
    row: EstimateLine, lineage: UUID, reference: Reference, subprojects: Mapping[UUID, str]
) -> Line:
    """Give a line of the structure as the workbook says it."""
    role = None if row.resource_role_id is None else reference.roles[row.resource_role_id].code
    category = None if role is not None else reference.categories[row.cost_category_id].code
    return Line(
        lineage=str(lineage),
        role=role,
        category=category,
        label=row.label,
        quantity=row.quantity,
        hours=row.hours,
        disbursement=row.unit_disbursement,
        payment_delay=row.payment_delay_days,
        subproject=None if row.subproject_id is None else subprojects[row.subproject_id],
        amount=row.reestimated_amount,
    )


def _parts(number: str) -> tuple[int, ...]:
    """Order the numbers « 1.2 » by their parts, as integers."""
    return tuple(int(part) if part.isdigit() else 0 for part in number.split(".") if part)


def _tabs(
    items: list[NodeView], tasks: Mapping[UUID, Task], numbering: _Numbering
) -> tuple[tuple[Lot, ...], Tab | None]:
    """Group the tasks into the tabs of the postes and of the lots, and the tab outside any lot."""
    placed = _placed(items)
    held: dict[Under, list[Task]] = {}
    for item in items:
        held.setdefault(placed[item.node_id], []).append(tasks[item.node_id])
    postes: dict[UUID, list[Tab]] = {}
    for (kind, key), group in held.items():
        if kind == POSTE and key is not None:
            number, label = numbering.numbers.get(key, ""), numbering.labels.get(key, "")
            tab = Tab(number, label, label, tuple(group))
            postes.setdefault(numbering.lots.get(key) or key, []).append(tab)
    lots: list[Lot] = []
    for key in {*postes, *(k for kind, k in held if kind == LOT and k is not None)}:
        number, label = numbering.numbers.get(key, ""), numbering.labels.get(key, "")
        tabs = sorted(postes.get(key, []), key=lambda tab: _parts(tab.number))
        if (LOT, key) in held:
            own = Tab(number, label, f"{label}, hors postes", tuple(held[LOT, key]))
            tabs.append(own)
        lots.append(Lot(number, label, tuple(tabs)))
    lots.sort(key=lambda lot: _parts(lot.number))
    outside = held.get((OUTSIDE, None))
    return tuple(lots), None if not outside else Tab("", NO_LOT, NO_LOT, tuple(outside))


@dataclass(frozen=True, slots=True)
class Referential:
    """The reference a workbook writes: its natures, its categories with their rates, its roles."""

    natures: tuple[Nature, ...]
    categories: tuple[Category, ...]
    roles: tuple[Role, ...]


def referential(reference: Reference, rows: Iterable[EstimateLine]) -> Referential:
    """Give the reference a revision is exported on: what its lines employ and what is active.

    ``reference`` as ``read_reference`` reads it, ``rows`` the lines of the structure exported; the
    rate of a category of labour is the revision's.
    """
    rows = list(rows)
    employed_roles = {row.resource_role_id for row in rows} - {None}
    employed = {row.cost_category_id for row in rows}
    roles = {
        key: each
        for key, each in reference.roles.items()
        if key in employed_roles or each.is_active
    }
    categories = {
        key: each
        for key, each in reference.categories.items()
        if key in employed or each.is_active or key in {role.category_id for role in roles.values()}
    }
    natures = sorted(
        {Nature(each.nature, each.kind) for each in categories.values()},
        key=lambda nature: (KIND_ORDER[nature.kind], nature.name),
    )
    return Referential(
        natures=tuple(natures),
        categories=tuple(
            Category(
                each.code,
                each.label,
                each.nature,
                reference.rates.get(key) if each.kind == "labour" else None,
            )
            for key, each in sorted(categories.items(), key=lambda pair: pair[1].code)
        ),
        roles=tuple(
            Role(
                each.code, each.label, each.department, reference.categories[each.category_id].code
            )
            for each in sorted(roles.values(), key=lambda role: role.code)
        ),
    )


def estimate_of(
    session: Session, order: ExportOrder, *, now: datetime | None = None
) -> tuple[Estimate, str]:
    """Give the estimate of the structure of an order, and the name of its file.

    Read in the transaction of the task; ``now`` is the instant of the export, the clock's if none.
    """
    project_id, revision_id, structure_id = order.project_id, order.revision_id, order.structure_id
    viewer = Viewer(NOBODY, frozenset())
    project = read_project(session, project_id, viewer)
    revision = read_revision(session, project_id, revision_id, viewer)
    structure = structure_facts(session, project_id, structure_id, lock=False)
    settings = read_reference_settings(session)
    reference = read_reference(
        session, order, revision.reference_year, marked=revision.status == "marked"
    )
    subprojects = list_subprojects(
        session, project_id, viewer, SubprojectFilters(), SubprojectSort()
    )
    codes = {each.subproject_id: each.code for each in subprojects}

    read = list_nodes(
        session, Place(project_id, revision_id, structure_id), NodeFilters(kinds=(TASK,))
    )
    items = [item for item in read.items if item.task is not None]
    bearing = lines_of(session, project_id, [item.node_id for item in items])
    rows = {
        row.node_id: row
        for row in rows_of(
            session, project_id, [node for held in bearing.values() for node in held]
        )
    }
    lineages = lineages_of(session, project_id, list(rows))
    numbers = outline(items)
    tasks = {
        item.node_id: Task(
            lineage=str(item.lineage_id),
            number=numbers[item.node_id],
            label=item.task.label,
            start=item.task.start.day,
            end=item.task.finish.day,
            description=item.task.description or "",
            lines=tuple(
                _line(rows[node], lineages[node], reference, codes)
                for node in bearing.get(item.node_id, ())
                if node in rows
            ),
        )
        for item in items
        if item.task is not None
    }
    borne = {
        key
        for item in items
        if item.task is not None
        for key in (item.task.order_item_id, item.task.work_package_id)
        if key is not None
    }
    lots, outside = _tabs(items, tasks, _numbering(session, project_id, borne))
    held = referential(reference, rows.values())
    name = file_name(project.code, project.label, (revision.version_name, revision_id))
    estimate = Estimate(
        company=settings.company_name,
        client=project.client or "",
        project=project.label,
        revision=revision.version_name or IN_PROGRESS_VERSION,
        structure=structure.label,
        reference_year=revision.reference_year,
        currency=settings.currency_code,
        exported_at=now or utc_now(),
        natures=held.natures,
        categories=held.categories,
        roles=held.roles,
        subprojects=tuple(Subproject(each.code, each.label) for each in subprojects),
        lots=lots,
        outside_lot=outside,
    )
    return estimate, name
