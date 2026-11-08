# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the planning share (EP-06, "Les tests du back"): rows, structures, tasks.

The rows of the planning written around the service — a node and its facet task, a link —, each
valid unless a test changes it, as ``project_rows`` writes those of the projects; and a task given
to a revision, the planning's part of what its designation asks. The stories of EP-06 add here the
structures with their tasks written through the interface of the planning, and the sessions that
write them; a story that needs another helper writes it in its own file.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from project_rows import STAMP
from sqlalchemy import func, insert, select

from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql import Executable

# The day a task of a test starts and finishes on, a Monday, and its eight hours.
DAY = date(2026, 11, 2)


def node_row(
    project_id: UUID, revision_id: UUID, structure_id: UUID, **overrides: object
) -> dict[str, object]:
    """Give the columns of a root task of a structure, first among its siblings, with changes."""
    node_id = uuid4()
    return {
        "project_id": project_id,
        "id": node_id,
        "revision_id": revision_id,
        "structure_id": structure_id,
        "lineage_id": node_id,
        "kind": "task",
        "parent_id": None,
        "rank": 1,
        **STAMP,
        **overrides,
    }


def task_row(
    project_id: UUID, node_id: UUID, structure_id: UUID, **overrides: object
) -> dict[str, object]:
    """Give the columns of the facet of a task: an automatic leaf of a day not started."""
    return {
        "project_id": project_id,
        "node_id": node_id,
        "structure_id": structure_id,
        "kind": "task",
        "label": "Conception",
        "scheduling_mode": "automatic",
        "duration_value": Decimal(1),
        "duration_unit": "d",
        "start_date": DAY,
        "start_hours": Decimal(0),
        "finish_date": DAY,
        "finish_hours": Decimal(8),
        "progress": "not_started",
        "total_float_days": Decimal(0),
        "is_critical": True,
        **overrides,
    }


def link_row(
    project_id: UUID,
    revision_id: UUID,
    structure_id: UUID,
    predecessor_id: UUID,
    successor_id: UUID,
    **overrides: object,
) -> dict[str, object]:
    """Give the columns of a link finish to start without lag between two tasks."""
    return {
        "project_id": project_id,
        "id": uuid4(),
        "revision_id": revision_id,
        "structure_id": structure_id,
        "predecessor_id": predecessor_id,
        "successor_id": successor_id,
        "link_type": "finish_to_start",
        "lag_value": Decimal(0),
        "lag_unit": "d",
        "in_conflict": False,
        **overrides,
    }


def insert_task(
    connection: Connection,
    project_id: UUID,
    revision_id: UUID,
    structure_id: UUID,
    *,
    rank: int = 1,
    **facet: object,
) -> UUID:
    """Write a root task of a structure, its node and its facet; give its node."""
    node = node_row(project_id, revision_id, structure_id, rank=rank)
    node_id = node["id"]
    assert isinstance(node_id, UUID)
    connection.execute(insert(Node).values(**node))
    connection.execute(insert(Task).values(**task_row(project_id, node_id, structure_id, **facet)))
    return node_id


def insert_link(
    project_id: UUID,
    revision_id: UUID,
    structure_id: UUID,
    predecessor_id: UUID,
    successor_id: UUID,
) -> Executable:
    """Give the insertion of a link between two tasks of a structure."""
    return insert(TaskLink).values(
        **link_row(project_id, revision_id, structure_id, predecessor_id, successor_id)
    )


def main_structure(connection: Connection, revision_id: UUID) -> tuple[UUID, UUID]:
    """Give the project of a revision and its main structure."""
    found = connection.execute(
        select(CostStructure.project_id, CostStructure.id).where(
            CostStructure.revision_id == revision_id, CostStructure.kind == "main"
        )
    ).one()
    return found[0], found[1]


def give_a_task(connection: Connection, revision_id: UUID) -> UUID:
    """Give a current revision a task in its main structure, around the service; give its node.

    What the designation of the reference asks of the planning (``revision_has_tasks``). Last of
    the roots: a revision opened from a marked one holds the tasks its copy brought (US-1380/L2).
    """
    project_id, structure_id = main_structure(connection, revision_id)
    last = connection.scalar(
        select(func.max(Node.rank)).where(
            Node.structure_id == structure_id, Node.parent_id.is_(None), Node.kind == "task"
        )
    )
    return insert_task(connection, project_id, revision_id, structure_id, rank=(last or 0) + 1)
