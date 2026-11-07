# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work breakdown of the project of the witness.

``work_breakdown.json``: work packages, order items, deliverables, each under the identifier the
example gives it, and the counter of the example (``WorkBreakdownReading.lock_version``). The
project is born with a work package and an order item that bear its label; this slice replaces
them, through the interface of the projects, at the instant the chronology creates the project.
The tasks that bear a work package or an order item (``attached_task``) are those of EP-06.
"""

from typing import TYPE_CHECKING

from waterfall.api.contract.models import Project, WorkBreakdownReading
from waterfall.core.projects.interface import (
    DeliverableEntry,
    OrderItemEntry,
    WorkBreakdownLoad,
    WorkPackageEntry,
    load_work_breakdown,
    work_breakdown_present,
)
from waterfall.witness import timeline
from waterfall.witness.description import is_loaded

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.witness.description import Witness

WORK_BREAKDOWN_FILE = "work_breakdown.json"
PROJECT_FILE = "project.json"


def load(session: Session, witness: Witness) -> bool:
    """Write this slice of the witness unless the platform holds it; tell whether it wrote."""
    project = witness.read(PROJECT_FILE, Project)
    project_id = project.project_id.root
    described = witness.read(WORK_BREAKDOWN_FILE, WorkBreakdownReading)
    entries = tuple(
        WorkPackageEntry(
            package.label,
            tuple(
                OrderItemEntry(
                    item.label,
                    tuple(
                        DeliverableEntry(deliverable.label, deliverable.deliverable_id.root)
                        for deliverable in item.deliverables
                    ),
                    item.order_item_id.root,
                )
                for item in package.order_items
            ),
            package.work_package_id.root,
        )
        for package in described.work_packages
    )
    imposed = {
        identifier
        for package in described.work_packages
        for identifier in (
            package.work_package_id.root,
            *(item.order_item_id.root for item in package.order_items),
            *(
                deliverable.deliverable_id.root
                for item in package.order_items
                for deliverable in item.deliverables
            ),
        )
    }
    if is_loaded(imposed, work_breakdown_present(session, imposed)):
        return False
    counter = 0 if described.lock_version is None else described.lock_version.root
    load_work_breakdown(
        session,
        WorkBreakdownLoad(project_id, entries, counter),
        timeline.created(witness, project),
    )
    return True
