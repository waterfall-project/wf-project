# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the indicators of the day share (US-1660/L3): a project priced task by task.

Beside ``indicators_support``, which writes one project under way, the projects these tests need
to hold the amounts of a sentence of the document: a reference of tasks, each bearing a line of
material at the amount said, on the subproject said and for the days said, all starting on the
Monday of ``DAY``; the project In progress, its current revision opened from the reference. A task
completed, a line re-estimated, a line of cost dated, then the reading of the indicators, all
through the service.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any
from uuid import UUID

from costs_support import cost
from estimate_support import Costing, Lines, costing
from indicators_support import progressed, zeroed
from projects_support import PROJECTS
from remaining_support import Review, in_progress, line_named, task_named

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from nodes_support import Tree
    from projects_support import Scene
    from support import ContractClient

    from waterfall.core.costs.interface import CostLineLoad


@dataclass(frozen=True)
class Planned:
    """A task of the reference: its label, the amount of its line, its subproject, its days."""

    label: str
    amount: str
    subproject_id: str | None = None
    days: str = "1"
    payment_delay_days: int = 0


@dataclass(frozen=True)
class Priced:
    """A project In progress priced task by task: its review, and the categories of its lines."""

    review: Review
    costs: Costing

    @property
    def tree(self) -> Tree:
        """Give the main structure of the current revision."""
        return self.review.tree

    @property
    def reference_id(self) -> UUID:
        """Give the reference of the project."""
        return UUID(self.review.reference["revision_id"])


def material(
    costs: Costing, label: str, amount: str, subproject_id: str | None, payment_delay_days: int = 0
) -> dict[str, Any]:
    """Give a line of material at the amount said, borne by a subproject or by none."""
    return {
        **({} if payment_delay_days == 0 else {"payment_delay_days": payment_delay_days}),
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
        **({} if subproject_id is None else {"subproject_id": subproject_id}),
    }


def line_of(label: str) -> str:
    """Give the label of the line a task of a label bears."""
    return f"Matériel {label}"


def priced(api: ContractClient, stage: Scene, tasks: Sequence[Planned]) -> Priced:
    """Write a reference of the tasks given, move its project In progress, open its successor."""
    costs = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        for each in tasks:
            task = tree.made(each.label, task={"duration": {"value": each.days, "unit": "d"}})
            line = material(
                costs, line_of(each.label), each.amount, each.subproject_id, each.payment_delay_days
            )
            lines.made(task, **line)

    return Priced(in_progress(api, stage, build), costs)


def completed(tree: Tree, label: str, on: date) -> None:
    """Start the task of a label, then complete it on a day, its line set to nought."""
    progressed(tree, task_named(tree, label), "started", on)
    zeroed(tree, line_named(tree, line_of(label)), on)


def reestimated(tree: Tree, label: str, amount: str) -> None:
    """Re-estimate the line of the task of a label at the amount said, as the manager does."""
    line = line_named(tree, line_of(label))
    sent = {
        "reestimated_amount_basis": {"unit_disbursement": amount},
        "lock_version": line["lock_version"],
    }
    path = f"{tree.path}/nodes/{line['node_id']}/remaining"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def dated(number: str, code: str | None, amount: str, day: date) -> CostLineLoad:
    """Give a line of cost of a document dated the day said."""
    return replace(cost(number, code, amount), document_date=day)


def subproject(api: ContractClient, stage: Scene, code: str, label: str) -> str:
    """Create a subproject of the project of the stage; give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["subproject_id"]


def indicators_answer(api: ContractClient, stage: Scene, query: str = "") -> Any:
    """Ask for the indicators of the project of the stage, the query said; give the answer."""
    return api.get(
        f"{PROJECTS}/{stage.project['project_id']}/indicators{query}",
        headers=stage.manager.headers,
    )


def indicators(api: ContractClient, stage: Scene, query: str = "") -> dict[str, Any]:
    """Read the indicators of the project of the stage, which must be served."""
    answer = indicators_answer(api, stage, query)
    assert answer.status_code == 200, answer.text
    return answer.json()
