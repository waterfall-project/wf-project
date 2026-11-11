# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The project of a workload test: its tree, its lines, its reference, the plan asked (US-1520).

Shared by ``test_workload`` and ``test_planned_value``. The roles work on calendars of eight hours
from Monday to Friday; a task a manual scheduling places between two days.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from estimate_support import Costing, Lines, add_role, costing
from nodes_support import Tree, mark, opened
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene

from waterfall.core.estimate.interface import planned_value

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

STATE_FORBIDS = "STATE_FORBIDS_OPERATION"
VALIDATION_FAILED = "VALIDATION_FAILED"
# A task from the first Monday of November to the last day of December 2026.
NOV_DEC = ("2026-11-02", "2026-12-31")
NOVEMBER = ("2026-11-02", "2026-11-30")
WORKED_DAYS = (8, 8, 8, 8, 8, 0, 0)
CENT = Decimal("0.01")
type Clock = Callable[[date], None]


@dataclass
class Site:
    """The project of a scene, its revision opened, a role that works eight hours a weekday."""

    api: ContractClient
    stage: Scene
    tree: Tree
    lines: Lines
    costs: Costing
    worker: UUID

    @property
    def path(self) -> str:
        """Give the path of the project."""
        return f"{PROJECTS}/{self.stage.project['project_id']}"

    def task(self, label: str, dates: tuple[str, str] = NOV_DEC) -> dict[str, Any]:
        """Create a task that a manual scheduling places between two days."""
        start, finish = dates
        manual = {"scheduling_mode": "manual", "start": {"date": start}, "finish": {"date": finish}}
        return self.tree.made(label, task=manual)

    def labour(
        self, task: dict[str, Any], hours: str, role: UUID | None = None, **line: Any
    ) -> str:
        """Give a task a labour line of a role, one person for some hours; give its node."""
        held = {"quantity": "1", "resource_role_id": str(role or self.worker), "hours": hours}
        return self.lines.made(task, **{**held, **line})["nodes"][0]["node_id"]

    def material(self, task: dict[str, Any], amount: str) -> str:
        """Give a task a line of material for an amount; give its node."""
        held = {"quantity": "1", "cost_category_id": str(self.costs.material)}
        return self.lines.made(task, **held, unit_disbursement=amount)["nodes"][0]["node_id"]

    def referenced(self) -> Tree:
        """Mark the revision, designate it the reference; give the revision opened after."""
        mark(self.stage, self.tree.revision)
        headers = self.stage.manager.headers
        counter = self.api.get(self.path, headers=headers).json()["lock_version"]
        sent = {
            "revision_id": self.tree.revision["revision_id"],
            "confirmed": True,
            "lock_version": counter,
        }
        answer = self.api.put(f"{self.path}/reference-revision", headers=headers, json=sent)
        assert answer.status_code == 200, answer.text
        return Tree(self.api, self.stage, opened(self.api, self.stage))

    def asked(self, basis: str, **query: Any) -> Any:
        """Ask for the workload on a basis; give the answer."""
        text = "&".join(f"{name}={value}" for name, value in {"basis": basis, **query}.items())
        return self.api.get(f"{self.path}/workload?{text}", headers=self.stage.manager.headers)

    def plan(self, basis: str, **query: Any) -> dict[str, Any]:
        """Ask for a workload that must be given; give it."""
        answer = self.asked(basis, **query)
        assert answer.status_code == 200, answer.text
        return answer.json()

    def value(self, at: date, revision: UUID | None = None) -> Decimal:
        """Give the planned value, at a day, of the reference of the project, or of a revision."""
        project = UUID(self.stage.project["project_id"])
        asked = revision or UUID(self.tree.revision["revision_id"])
        with self.stage.database.transaction() as session:
            return planned_value(session, project, asked, at)


def make_site(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Site:
    """Give a platform, a project its manager made, its revision opened, and a role to load."""
    stage = make_scene(api, owner, database, realm)
    tree = Tree(api, stage, opened(api, stage))
    worker = add_role(database, "WRK", WORKED_DAYS)
    return Site(api, stage, tree, Lines(tree), costing(database), worker)


def day_setter(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the service reads as today, and the worker marks on."""

    def set_day(day: date) -> None:
        now = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
        monkeypatch.setattr("waterfall.api.workload.utc_now", lambda: now)
        monkeypatch.setattr("nodes_support.utc_now", lambda: now)

    return set_day
