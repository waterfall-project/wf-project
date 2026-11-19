# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the occurrence of a risk share (US-2620): a risk ready to occur.

The project costed at 1 000 (``risks_support.costed``), a risk of severity 200 at 30 % declared in
its first revision, whose provision of 60 is borne by ``Étude``, the first task of the first level;
that revision marked and designated the reference, and the second opened, which copies the risk
identified (WF-RIS-0060 asks for a reference). The own estimate, its planning started on a Monday:

- ``Diagnostic des défauts``, two days, no predecessor, bearing ``Recherche des défauts``, 120;
- ``Reprise du câblage``, a summary, over ``Recâblage des armoires``, three days after the
  diagnostic, bearing ``Fils et borniers``, 80, and ``Essais``, a day after the rewiring.

Written through the service, as its manager does; read in the revision it is asked in.
"""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from estimate_support import add_role
from nodes_support import mark
from projects_support import PROJECTS, designate
from risks_support import Costed, Risks, material
from sqlalchemy import select, update

from waterfall.core.planning.tables import Task
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from support import ContractClient

# The Monday the own estimate starts its planning on, a week after the main structure's.
OWN_START = date(2026, 11, 9)
DIAGNOSTIC, SEARCH = "Diagnostic des défauts", "Recherche des défauts"
REWORK, REWIRING, WIRES, TESTS = (
    "Reprise du câblage",
    "Recâblage des armoires",
    "Fils et borniers",
    "Essais",
)
# The nodes of the own estimate, in the order of its plan, each with its kind.
OWN_PLAN = (
    ("task", DIAGNOSTIC),
    ("estimate_line", SEARCH),
    ("task", REWORK),
    ("task", REWIRING),
    ("estimate_line", WIRES),
    ("task", TESTS),
)


@dataclass(frozen=True)
class Occurring:
    """A risk identified in the second revision of a project, its own estimate filled.

    ``first`` the revision marked and designated, ``revision`` the current one.
    """

    api: ContractClient
    project: Costed
    risks: Risks
    risk: dict[str, Any]
    first: dict[str, Any]
    revision: dict[str, Any]

    @property
    def path(self) -> str:
        """Give the path of the risk."""
        return f"{PROJECTS}/{self.project.project_id}/risks/{self.risk['risk_id']}"

    def read(self) -> dict[str, Any]:
        """Read the risk in the current revision, or the last marked one."""
        return self.risks.risk(self.risk)

    def report(self) -> Any:
        """Ask for the report of the occurrence of the risk; give the answer."""
        return self.api.get(f"{self.path}/occurrence", headers=self.risks.headers)

    def reported(self) -> dict[str, Any]:
        """Read the report of the occurrence of the risk, which must be read."""
        answer = self.report()
        assert answer.status_code == 200, answer.text
        return answer.json()

    def own(self, revision_id: object | None = None) -> list[dict[str, Any]]:
        """Read the nodes of the own estimate of the risk in a revision, the current by default."""
        held = revision_id or self.revision["revision_id"]
        answer = self.api.get(self.risks.own(self.risk, held), headers=self.risks.headers)
        assert answer.status_code == 200, answer.text
        return answer.json()["items"]

    def main(self, revision_id: object | None = None) -> list[dict[str, Any]]:
        """Read the nodes of the main structure of a revision, the current by default."""
        held = revision_id or self.revision["revision_id"]
        base = f"{PROJECTS}/{self.project.project_id}/revisions/{held}/structures"
        listed = self.api.get(base, headers=self.risks.headers)
        assert listed.status_code == 200, listed.text
        main = next(each for each in listed.json() if each["kind"] == "main")
        answer = self.api.get(f"{base}/{main['structure_id']}/nodes", headers=self.risks.headers)
        assert answer.status_code == 200, answer.text
        return answer.json()["items"]

    def main_path(self) -> str:
        """Give the path of the main structure of the current revision."""
        held = self.revision["revision_id"]
        base = f"{PROJECTS}/{self.project.project_id}/revisions/{held}/structures"
        return f"{base}/{self.main_structure()['structure_id']}"

    def main_structure(self, revision_id: object | None = None) -> dict[str, Any]:
        """Read the main structure of a revision, the current by default, as the list gives it."""
        held = revision_id or self.revision["revision_id"]
        base = f"{PROJECTS}/{self.project.project_id}/revisions/{held}/structures"
        listed = self.api.get(base, headers=self.risks.headers)
        assert listed.status_code == 200, listed.text
        return next(each for each in listed.json() if each["kind"] == "main")


def _task(risks: Risks, path: str, label: str, parent: str | None, days: str) -> dict[str, Any]:
    """Create a task of an own estimate lasting some days; give it."""
    task = {"label": label, "duration": {"value": days, "unit": "d"}}
    return risks.made(path, {"kind": "task", "parent_id": parent, "task": task})


def _line(risks: Risks, path: str, task: dict[str, Any], line: dict[str, Any]) -> None:
    """Create a line under a task of an own estimate."""
    sent = {"kind": "estimate_line", "parent_id": task["node_id"], "estimate_line": line}
    risks.made(path, sent)


def follows(risks: Risks, path: str, task: dict[str, Any], before: dict[str, Any]) -> None:
    """Make a task of an own estimate follow another, finish to start, at the counter read."""
    held = next(
        each
        for each in risks.api.get(path, headers=risks.headers).json()["items"]
        if each["node_id"] == task["node_id"]
    )
    body = {
        "predecessors": [
            {
                "predecessor_node_id": before["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": held["lock_version"],
    }
    answer = risks.api.put(
        f"{path}/{task['node_id']}/predecessors", headers=risks.headers, json=body
    )
    assert answer.status_code == 200, answer.text


def fill_own_estimate(risks: Risks, risk: dict[str, Any], revision_id: object) -> None:
    """Write the own estimate of the risk in a revision: the diagnostic, the rework under it."""
    held = risks.risk(risk, revision_id)
    with risks.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(held["structure_id"]))
            .values(planning_start_on=OWN_START)
        )
    path = risks.own(risk, revision_id)
    costs = risks.project.costs
    diagnostic = _task(risks, path, DIAGNOSTIC, None, "2")
    _line(risks, path, diagnostic, material(costs, SEARCH, "120.00"))
    rework = _task(risks, path, REWORK, None, "1")
    rewiring = _task(risks, path, REWIRING, rework["node_id"], "3")
    _line(risks, path, rewiring, material(costs, WIRES, "80.00"))
    tests = _task(risks, path, TESTS, rework["node_id"], "1")
    follows(risks, path, rewiring, diagnostic)
    follows(risks, path, tests, rewiring)


def occurring(api: ContractClient, project: Costed) -> Occurring:
    """Declare the risk and fill its own estimate, mark and designate, open the next revision."""
    risks = Risks(api, project)
    risk = risks.declared()
    fill_own_estimate(risks, risk, project.revision_id)
    revision = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    mark(project.stage, {"revision_id": str(project.revision_id)})
    first = api.get(revision, headers=risks.headers).json()
    designate(api, project.stage, first)
    second = risks.revision()
    return Occurring(api, project, risks, risks.risk(risk), first, second)


def idle_diagnostic(ready: Occurring) -> tuple[UUID, UUID, UUID]:
    """Leave the diagnostic of the current revision without an hour; give its roles and its node.

    It bears two labour lines, a welder and a fitter both on weekdays; the fitter's calendar then
    moved to the weekend around the service, as a change of the reference after the revision was
    opened would (WF-PLA-0010).
    """
    stage = ready.project.stage
    welder = add_role(stage.database, "SOUD", (8, 8, 8, 8, 8, 0, 0))
    fitter = add_role(stage.database, "MONT", (8, 8, 8, 8, 8, 0, 0))
    path = ready.risks.own(ready.risk, ready.revision["revision_id"])
    diagnostic = next(
        each for each in ready.own() if each.get("task", {}).get("label") == DIAGNOSTIC
    )
    for role in (welder, fitter):
        line = {
            "label": "Main-d'œuvre",
            "quantity": "1",
            "resource_role_id": str(role),
            "hours": "4",
        }
        sent = {"kind": "estimate_line", "parent_id": diagnostic["node_id"], "estimate_line": line}
        ready.risks.made(path, sent)
    weekend = {"saturday": 8, "sunday": 8} | dict.fromkeys(
        ("monday", "tuesday", "wednesday", "thursday", "friday"), 0
    )
    with stage.owner.begin() as connection:
        calendar = connection.scalar(
            select(ResourceRole.calendar_id).where(ResourceRole.id == fitter)
        )
        connection.execute(update(Calendar).where(Calendar.id == calendar).values(**weekend))
    return welder, fitter, UUID(diagnostic["node_id"])


def main_task(ready: Occurring, label: str, parent: str | None, days: str) -> dict[str, Any]:
    """Create a task in the main structure of the current revision, last under its parent."""
    task = {"label": label, "duration": {"value": days, "unit": "d"}}
    sent = {"kind": "task", "parent_id": parent, "task": task}
    return ready.risks.made(f"{ready.main_path()}/nodes", sent)


def beyond_horizon(ready: Occurring, label: str) -> UUID:
    """Push a task of the own estimate to the year 2060, past the fifteen years of the horizon.

    Give its node. Around the service, as a change of the reference would leave it: the dates of
    the own estimate are read as they stand.
    """
    node = next(
        each for each in ready.own() if each["kind"] == "task" and each["task"]["label"] == label
    )
    with ready.project.stage.owner.begin() as connection:
        connection.execute(
            update(Task)
            .where(Task.node_id == UUID(node["node_id"]))
            .values(finish_date=date(2060, 1, 1))
        )
    return UUID(node["node_id"])
