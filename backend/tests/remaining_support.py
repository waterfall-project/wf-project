# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the remaining to commit share (EP-09, "Les tests du back"): a line reviewed.

What a review of the project writes on a line of estimate — its remaining to commit before the
review, the mark of its re-estimation and the reason sent —, valid for a line of labour of
``estimate_support`` unless a test changes it, written around the service. The stories of EP-09
add here a project In progress with its reference, its tasks and its lines written through the
interfaces, and the clock set; a story that needs another helper writes it in its own file.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from estimate_support import Lines
from nodes_support import Tree, mark, opened
from project_rows import AT
from projects_support import PROJECTS
from sqlalchemy.orm import Session

from waterfall.core.revisions.interface import mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from projects_support import Scene
    from support import ContractClient

# The six columns of a line of labour reviewed (migration 0027): its figures and its amount before
# the review — two engineers for twelve hours —, reestimated at ``AT``, and why.
REVIEWED: dict[str, object] = {
    "previous_quantity": Decimal(2),
    "previous_hours": Decimal(12),
    "previous_unit_disbursement": None,
    "previous_reestimated_amount": Decimal("1560.00"),
    "reestimated_at": AT,
    "remaining_reason": "Revue d'avril : essais reportés",
}


def reviewed(**overrides: object) -> dict[str, object]:
    """Give the columns a review writes on a line of labour, with the changes a test asks for."""
    return {**REVIEWED, **overrides}


# --- A project In progress, written through the service (US-1580/L2) ----------------------------


@dataclass(frozen=True)
class Review:
    """A project In progress: its reference, and the main structure of its current revision.

    The reference is the first revision, written by ``build``, marked and designated; the code
    entered moves the project In progress (WF-CYC-0030), the passage recorded at that instant; the
    current revision is opened from the reference, its lines budgeted by it.
    """

    reference: dict[str, Any]
    tree: Tree
    lines: Lines


def in_progress(api: ContractClient, stage: Scene, build: Callable[[Tree, Lines], None]) -> Review:
    """Write a reference through the service, move its project In progress, open its successor."""
    first = Tree(api, stage, opened(api, stage))
    build(first, Lines(first))
    mark(stage, first.revision)
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    sent = {
        "revision_id": first.revision["revision_id"],
        "confirmed": True,
        "lock_version": counter,
    }
    designated = api.put(f"{path}/reference-revision", headers=stage.manager.headers, json=sent)
    assert designated.status_code == 200, designated.text
    counter = designated.json()["lock_version"]
    coded = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-1580", "lock_version": counter}
    )
    assert (coded.status_code, coded.json()["state"]) == (200, "in_progress"), coded.text
    tree = Tree(api, stage, opened(api, stage))
    return Review(first.revision, tree, Lines(tree))


def review_marked(stage: Scene, revision: dict[str, Any], version_name: str) -> None:
    """Mark a revision of the project In progress by the transaction of the worker (a review)."""
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        marking = (UUID(revision["revision_id"]), version_name, None)
        mark_revision(session, *marking, Act(None, utc_now()))


def line_named(tree: Tree, label: str) -> dict[str, Any]:
    """Read the line of a label in a structure, as the reading gives it."""
    return next(
        item
        for item in tree.items()
        if item["kind"] == "estimate_line" and item["estimate_line"]["label"] == label
    )


def task_named(tree: Tree, label: str) -> dict[str, Any]:
    """Read the task of a label in a structure, as the reading gives it."""
    return next(
        item for item in tree.items() if item["kind"] == "task" and item["task"]["label"] == label
    )
