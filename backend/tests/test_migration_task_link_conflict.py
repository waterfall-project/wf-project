# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in manual mode the links in conflict already kept name: 0044 (US-3300/L3, #3984).

The table is created empty, then filled, marked revisions included, with what the engine could say
until now: for each link in conflict whose successor is a task in manual mode without a subtask,
that successor. No engine is replayed: a link toward a summary gets its conflicts at the first
replay of its structure (EP-32, "Tables et migrations").
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from planning_support import link_row, node_row, task_row
from project_rows import MARKED, insert_project, insert_revision, insert_structure
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.exc import IntegrityError

from waterfall.core.planning.tables import Node, Task, TaskLink, TaskLinkConflict
from waterfall.core.revisions.tables import Revision
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection


def planned(connection: Connection, project_id: UUID) -> tuple[UUID, set[tuple[UUID, UUID]]]:
    """Write a revision whose structure holds links in conflict of each kind; give what 0044 keeps.

    P → M, M a manual leaf, kept with M; P → S, S a summary above a manual task, and Q → A, A an
    automatic leaf, both in conflict and neither kept; Q → M, not in conflict, not kept.
    """
    revision_id, structure_id = uuid4(), uuid4()
    connection.execute(insert_revision(project_id, id=revision_id))
    connection.execute(insert_structure(project_id, revision_id, id=structure_id))
    nodes: dict[str, UUID] = {}
    for rank, label in enumerate(("P", "Q", "A", "M", "S"), start=1):
        row = node_row(project_id, revision_id, structure_id, rank=rank)
        nodes[label] = UUID(str(row["id"]))
        connection.execute(insert(Node).values(**row))
    under = node_row(project_id, revision_id, structure_id, parent_id=nodes["S"])
    nodes["U"] = UUID(str(under["id"]))
    connection.execute(insert(Node).values(**under))
    for label, node_id in nodes.items():
        mode = "manual" if label in {"M", "U"} else "automatic"
        facet = task_row(project_id, node_id, structure_id, scheduling_mode=mode)
        connection.execute(insert(Task).values(**facet))
    kept: set[tuple[UUID, UUID]] = set()
    for predecessor, successor, conflicting in (
        ("P", "M", True),
        ("P", "S", True),
        ("Q", "A", True),
        ("Q", "M", False),
    ):
        row = link_row(
            project_id,
            revision_id,
            structure_id,
            nodes[predecessor],
            nodes[successor],
            in_conflict=conflicting,
        )
        connection.execute(insert(TaskLink).values(**row))
        if (predecessor, successor) == ("P", "M"):
            kept.add((UUID(str(row["id"])), nodes["M"]))
    return revision_id, kept


def conflicts(engine: Engine) -> set[tuple[UUID, UUID]]:
    """Give the rows of the table: each link and the task it names."""
    with engine.connect() as connection:
        rows = connection.execute(select(TaskLinkConflict.link_id, TaskLinkConflict.node_id))
        return {(link_id, node_id) for link_id, node_id in rows}


def aimed(engine: Engine) -> bool:
    """Tell whether ``task_link`` bears the unique constraint the key of a conflict aims at."""
    query = text(
        "SELECT count(*) FROM pg_constraint"
        " WHERE conrelid = 'task_link'::regclass AND contype = 'u'"
        " AND conname = 'uq_task_link_project_id'"
    )
    with engine.connect() as connection:
        return connection.scalar(query) == 1


@pytest.mark.story("US-3300")
def test_the_migration_keeps_the_manual_successor_of_each_link_in_conflict_marked_included(
    empty_engine: Engine,
) -> None:
    # Propre à l'US (« Tables et migrations ») : « la migration la crée vide et la remplit, pour
    # chaque liaison in_conflict dont le successeur est une feuille manuelle, de ce successeur » —
    # a marked revision's too, which its guard then holds read only; the descent drops the table,
    # the links keeping in_conflict.
    upgrade(empty_engine, "0043")
    project_id = uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project_id))
        connection.execute(select(func.create_project_partitions(project_id)))
        marked, frozen = planned(connection, project_id)
        connection.execute(update(Revision).where(Revision.id == marked).values(**MARKED))
        current, kept = planned(connection, project_id)
    upgrade(empty_engine, "0044")
    assert conflicts(empty_engine) == kept | frozen
    with empty_engine.connect() as connection:
        revisions = connection.scalars(select(TaskLinkConflict.revision_id)).all()
    assert sorted(revisions) == sorted([current, marked])
    with pytest.raises(IntegrityError, match="never written"), empty_engine.begin() as connection:
        connection.execute(delete(TaskLinkConflict).where(TaskLinkConflict.revision_id == marked))
    assert aimed(empty_engine)
    downgrade(empty_engine, "0043")
    with empty_engine.connect() as connection:
        assert connection.scalar(text("SELECT to_regclass('task_link_conflict')")) is None
        assert connection.scalar(select(func.count()).where(TaskLink.in_conflict)) == 6
    # The unique constraint the key of a conflict aims at goes with it, by the name the convention
    # gives it in the tables (#4780).
    assert not aimed(empty_engine)
