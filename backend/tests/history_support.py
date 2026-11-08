# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the undoing and of the paste share (US-1450/L2): their routes and their steps.

The routes of the history, read back — the undoing and the redoing of a revision, the preview and
the confirmation of a paste —, and the writes the stories before this one serve that a test of the
history makes, as a contributor whose token carries a session of sign-in does: a deletion, a
predecessor, a start date. The fixtures stay in the test files, which pytest reads them from.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from project_rows import STAMP
from sqlalchemy import insert, select, update

from waterfall.core.history.tables import PastePlan
from waterfall.core.planning.tables import TrackingEntry
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from nodes_support import Tree
    from projects_support import Person, Scene


def revision_path(tree: Tree) -> str:
    """Give the path of the revision of a structure."""
    return tree.path.split("/structures/")[0]


def undo(tree: Tree, who: Person) -> Any:
    """Undo the last change of an account in the revision; give the answer."""
    return tree.api.post(f"{revision_path(tree)}/undo", headers=who.headers)


def redo(tree: Tree, who: Person) -> Any:
    """Redo the last undoing of an account in the revision; give the answer."""
    return tree.api.post(f"{revision_path(tree)}/redo", headers=who.headers)


def undone(tree: Tree, who: Person) -> dict[str, Any]:
    """Undo a change that must be undone; give what is answered."""
    answer = undo(tree, who)
    assert answer.status_code == 200, answer.text
    return answer.json()


def redone(tree: Tree, who: Person) -> dict[str, Any]:
    """Redo an undoing that must be redone; give what is answered."""
    answer = redo(tree, who)
    assert answer.status_code == 200, answer.text
    return answer.json()


def delete(tree: Tree, node: dict[str, Any], who: Person) -> Any:
    """Delete a node at the counter read; give the answer."""
    path = f"{tree.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}"
    return tree.api.delete(path, headers=who.headers)


def link(tree: Tree, node: dict[str, Any], who: Person, *predecessors: dict[str, Any]) -> Any:
    """Replace the predecessors of a task, finish to start, at its counter read; give the answer."""
    sent = [
        {
            "predecessor_node_id": each["node_id"],
            "link_type": "finish_to_start",
            "lag": {"value": "0", "unit": "d"},
        }
        for each in predecessors
    ]
    body = {"predecessors": sent, "lock_version": node["lock_version"]}
    return tree.api.put(
        f"{tree.path}/nodes/{node['node_id']}/predecessors", headers=who.headers, json=body
    )


def inscribe(stage: Scene, lineage_id: str) -> None:
    """Inscribe a lineage to the time/time tracking around the service, as US-1400 will."""
    with stage.owner.begin() as connection:
        connection.execute(
            insert(TrackingEntry).values(
                id=uuid4(),
                project_id=UUID(stage.project["project_id"]),
                lineage_id=UUID(lineage_id),
                kind="milestone_tracking",
                timeline_id=None,
                **STAMP,
            )
        )


def counter(tree: Tree) -> int:
    """Read the counter of the structure, which every write of its tree advances."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


def plans(stage: Scene) -> list[PastePlan]:
    """Read the plans of a paste the base keeps."""
    with stage.database.transaction() as session:
        found = session.scalars(select(PastePlan).order_by(PastePlan.created_at)).all()
        session.expunge_all()
        return list(found)


def put_column(stage: Scene, table: Any, key: Any, **values: object) -> None:
    """Write columns of a row around the service."""
    with stage.owner.begin() as connection:
        connection.execute(update(table).where(table.id == key).values(**values))
