# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the tree of the tasks share (US-1380/L2): a structure, its writes, refusals.

The main structure of the current revision of a project, its planning started on a Monday, read
and written through the service as its manager does by default; the refusals read back, a
contributor whose token carries a session of sign-in, the entries of the history, a state put
around the service as US-1410 will, a revision marked as the worker marks it.
"""

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from access_rows import role
from planning_support import DAY
from project_rows import STAMP
from projects_support import MANAGING, PROJECTS, Person, Scene, contribute
from realm import KEY
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from support import bearer, raw_account

from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.history.tables import UndoEntry
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.tables import OrderItem, WorkPackage
from waterfall.core.revisions.interface import mark_revision
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient


CONSULT = "planning.read"
CHANGE = "planning.write"
# The Friday after the Monday the structures of these tests start their planning on, a Saturday,
# and the following Monday.
FRIDAY = DAY + timedelta(days=4)
SATURDAY = DAY + timedelta(days=5)
NEXT_MONDAY = DAY + timedelta(days=7)
SESSION = "office"


class Tree:
    """The main structure of the current revision of the project of a stage, and its writes."""

    def __init__(self, api: ContractClient, stage: Scene, revision: dict[str, Any]) -> None:
        """Read the main structure of the revision, and start its planning on a Monday."""
        self.api = api
        self.stage = stage
        self.revision = revision
        base = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}"
        listed = api.get(f"{base}/structures", headers=stage.manager.headers)
        assert listed.status_code == 200, listed.text
        self.structure_id = listed.json()[0]["structure_id"]
        self.path = f"{base}/structures/{self.structure_id}"
        with stage.owner.begin() as connection:
            connection.execute(
                update(CostStructure)
                .where(CostStructure.id == UUID(self.structure_id))
                .values(planning_start_on=DAY)
            )
        self.created_at = scheduled_at(self)

    def create(self, label: str, who: Person | None = None, **body: Any) -> Any:
        """Ask for a task, as the manager does by default; give the answer."""
        task = {"label": label, **body.pop("task", {})}
        sent = {"kind": "task", "parent_id": None, "task": task, **body}
        headers = (who or self.stage.manager).headers
        return self.api.post(f"{self.path}/nodes", headers=headers, json=sent)

    def made(self, label: str, **body: Any) -> dict[str, Any]:
        """Create a task that must be created; give the node created."""
        answer = self.create(label, **body)
        assert answer.status_code == 201, answer.text
        return answer.json()["nodes"][0]

    def change(self, node: dict[str, Any], who: Person | None = None, **body: Any) -> Any:
        """Change the facet of a task at the counter read; give the answer."""
        sent = {"lock_version": node["lock_version"], **body}
        headers = (who or self.stage.manager).headers
        path = f"{self.path}/nodes/{node['node_id']}/task"
        return self.api.patch(path, headers=headers, json=sent)

    def changed(self, node: dict[str, Any], **body: Any) -> dict[str, Any]:
        """Change a task that must be changed; give what is answered."""
        answer = self.change(node, **body)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def read(self, query: str = "", who: Person | None = None) -> Any:
        """Read the structure with a query; give the answer."""
        headers = (who or self.stage.manager).headers
        return self.api.get(f"{self.path}/nodes{query}", headers=headers)

    def items(self, query: str = "") -> list[dict[str, Any]]:
        """Read the nodes the query retains, in their order."""
        answer = self.read(query)
        assert answer.status_code == 200, answer.text
        return answer.json()["items"]

    def labels(self, query: str = "") -> list[str]:
        """Read the labels of the tasks the query retains, in their order."""
        return [item["task"]["label"] for item in self.items(query)]

    def node(self, node_id: str) -> dict[str, Any]:
        """Read a node of the structure as the reading gives it."""
        return next(item for item in self.items() if item["node_id"] == node_id)


def scheduled_at(tree: Tree) -> datetime:
    """Read the instant the dates of the structure were last computed."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.scheduled_at).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


def opened(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    answer = api.post(path, headers=stage.manager.headers, json={})
    assert answer.status_code == 201, answer.text
    return answer.json()


def refusal(answer: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = answer.json()
    return answer.status_code, body["code"], body.get("params", {})


def faults(answer: Any) -> list[tuple[str, str, dict[str, Any]]]:
    """Give the fields a refusal of 422 names, each with its code and its parameters."""
    assert answer.status_code == 422, answer.text
    return [
        (each["pointer"], each["code"], each.get("params", {})) for each in answer.json()["fields"]
    ]


def instant(day: date, hours: str) -> dict[str, str]:
    """Write an instant of work as the contract reads it."""
    return {"date": day.isoformat(), "hours": hours}


def signed_in(stage: Scene, realm: TestRealm) -> Person:
    """Write a contributor of the project whose token carries a session of sign-in (``sid``)."""
    account = raw_account(email=f"{uuid4().hex}@example.org", first_name="Léa")
    held = role(stage.database, f"Rôle {uuid4().hex}", permissions=MANAGING)
    with stage.database.transaction() as session:
        session.execute(insert(UserAccount).values(**account))
        session.execute(
            insert(UserAccessRole).values(user_account_id=account["id"], access_role_id=held)
        )
    token = realm.token(str(account["idp_subject"]), KEY, claims={"sid": SESSION})
    who = Person(bearer(token), UUID(str(account["id"])))
    contribute(stage.database, stage.project["project_id"], who, "contributor")
    return who


def entries(stage: Scene) -> list[UndoEntry]:
    """Read the entries of the history, in the order of their stack."""
    with stage.database.transaction() as session:
        found = session.scalars(select(UndoEntry).order_by(UndoEntry.rank)).all()
        session.expunge_all()
        return list(found)


def set_progress(stage: Scene, node_id: str, progress: str, on: date) -> None:
    """Put a task in a state around the service, as US-1410 will."""
    completed = on if progress == "completed" else None
    with stage.owner.begin() as connection:
        connection.execute(
            update(Task)
            .where(Task.node_id == UUID(node_id))
            .values(progress=progress, started_on=on, completed_on=completed)
        )


def mark(stage: Scene, revision: dict[str, Any]) -> None:
    """Mark a revision by the transaction of the worker (US-0970)."""
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        marked = UUID(revision["revision_id"])
        mark_revision(session, marked, "v1.0", None, Act(None, utc_now()))


def put_facts(stage: Scene, node_id: str, **facts: object) -> None:
    """Put columns of the facet of a task around the service, as the engine and US-1410 will."""
    with stage.owner.begin() as connection:
        connection.execute(update(Task).where(Task.node_id == UUID(node_id)).values(**facts))


def put_risk(stage: Scene, node_id: str, risk_id: UUID) -> None:
    """Make a task come from a risk, around the service, as EP-08 will."""
    with stage.owner.begin() as connection:
        connection.execute(
            update(Node).where(Node.id == UUID(node_id)).values(origin_risk_id=risk_id)
        )


def work_breakdown(stage: Scene) -> tuple[UUID, UUID]:
    """Write a work package and an order item of the project of a stage; give their identifiers."""
    package, item = uuid4(), uuid4()
    element = {"project_id": UUID(stage.project["project_id"]), **STAMP}
    with stage.owner.begin() as connection:
        # The project holds a bare work package at the position 0 already.
        connection.execute(
            insert(WorkPackage).values(id=package, label="Lot", position=1, **element)
        )
        connection.execute(
            insert(OrderItem).values(
                id=item, work_package_id=package, label="Poste", position=0, **element
            )
        )
    return package, item
