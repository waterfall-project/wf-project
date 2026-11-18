# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the time/time diagram share (US-1710): a project In progress and its reviews.

A project In progress whose reference holds two milestones and a task; its current revision follows
the reference. A review is the current revision marked at a day of the clock, then the next one
opened (``review``): the lines of ``task`` of a marked revision do not change, which is what the
diagram reads. The dates of a milestone are written around the service, as the engine will when it
dates one from its predecessors (``date``).
"""

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from day_indicators_support import material
from estimate_support import Lines, costing
from indicators_support import marked, progressed
from nodes_support import Tree, opened, put_facts
from projects_support import PROJECTS
from remaining_support import in_progress, task_named

if TYPE_CHECKING:
    from indicators_support import Clock
    from projects_support import Scene
    from support import ContractClient

MILESTONE = {"duration": {"value": "0", "unit": "d"}}
TIME_TIME: dict[str, Any] = {"kind": "milestone_tracking"}
STUDIES, DELIVERY, TESTS = "Réception des études", "Livraison", "Essais"
# The day the clock stands on first, and a date a milestone is forecast at.
START = date(2027, 1, 11)
JUNE_30 = date(2027, 6, 30)
JULY_31 = date(2027, 7, 31)


class Project:
    """A project In progress, its current revision, and the means to review it and to read."""

    def __init__(self, api: ContractClient, stage: Scene, clock: Clock) -> None:
        """Write the reference — two milestones and a task —, move the project In progress."""
        self.api, self.stage, self.clock = api, stage, clock

        costs = costing(stage.database)

        def build(tree: Tree, lines: Lines) -> None:
            tree.made(STUDIES, task=MILESTONE)
            tree.made(DELIVERY, task=MILESTONE)
            work = tree.made(TESTS, task={"duration": {"value": "5", "unit": "d"}})
            lines.made(work, **material(costs, "Matériel essais", "1000", None))

        self.tree = in_progress(api, stage, build).tree

    @property
    def project_id(self) -> UUID:
        """Give the identifier of the project."""
        return UUID(self.stage.project["project_id"])

    def node(self, label: str) -> dict[str, Any]:
        """Read the task of a label in the current revision."""
        return task_named(self.tree, label)

    def track(self, label: str, *sent: dict[str, Any]) -> dict[str, Any]:
        """Replace the inscriptions of a task of the current revision; give the node written."""
        node = self.node(label)
        body = {"entries": list(sent), "lock_version": node["lock_version"]}
        path = f"{self.tree.path}/nodes/{node['node_id']}/tracking"
        answer = self.api.put(path, headers=self.stage.manager.headers, json=body)
        assert answer.status_code == 200, answer.text
        return answer.json()["nodes"][0]

    def date(self, label: str, day: date) -> None:
        """Forecast a task of the current revision on a day, as the engine writes its dates."""
        put_facts(self.stage, self.node(label)["node_id"], start_date=day, finish_date=day)

    def progress(self, label: str, state: str, day: date) -> None:
        """Move a task of the current revision to a state, at a day."""
        progressed(self.tree, self.node(label), state, day)

    def review(self, day: date, version_name: str, *, reopen: bool = True) -> None:
        """Mark the current revision at a day of the clock, then open the next one from it."""
        self.clock(day)
        marked(self.stage, self.tree.revision, version_name)
        if reopen:
            self.tree = Tree(self.api, self.stage, opened(self.api, self.stage))

    def answer(self, day: date | None = None) -> Any:
        """Ask for the diagram, the clock set at a day if one is given."""
        if day is not None:
            self.clock(day)
        path = f"{PROJECTS}/{self.project_id}/indicators/milestone-tracking"
        return self.api.get(path, headers=self.stage.manager.headers)

    def diagram(self, day: date | None = None) -> dict[str, Any]:
        """Read the diagram, which must be served."""
        answer = self.answer(day)
        assert answer.status_code == 200, answer.text
        return answer.json()


def months(day: date, count: int) -> date:
    """Give the day ``count`` months later, the same day of the month (the 1st to the 28th)."""
    index = day.month - 1 + count
    return day.replace(year=day.year + index // 12, month=index % 12 + 1)


def points(milestone: dict[str, Any]) -> list[tuple[str, str]]:
    """Give the points of a milestone, each as its marking instant and its forecast date."""
    return [(each["marked_at"], each["forecast_date"]) for each in milestone["points"]]


def milestone(body: dict[str, Any], label: str) -> dict[str, Any]:
    """Give the milestone of a label of the diagram."""
    return next(each for each in body["milestones"] if each["label"] == label)


def at_nine(day: date) -> str:
    """Write the instant the clock gives a day: nine in the morning, in universal time."""
    return f"{day.isoformat()}T09:00:00Z"
