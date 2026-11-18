# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the indicators share (EP-10, "Les tests du back"): a project under way.

A document of indicators written around the service, valid unless a test changes it; the clock
set, which the routes of the indicators read as the instant of their computation and the worker
marks at; and a project In progress written through the interfaces of EP-04 to EP-09 — its
reference designated, its tasks and their lines, a task completed and another started in its
current revision, lines of cost loaded; the thresholds of the indices set, as the reference
settings set them. The stories of EP-10 read it; a story that needs another helper writes it in
its own file, and a helper that several test modules read lives here, never in one of them (#3619).

The day of the clock is the one of the time zone of the installation (``current_day``, US-2200):
in universal time unless a test sets the zone, at nine in the morning, which every zone of the
world puts on the same day.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from costs_support import cost, load_import
from estimate_support import Costing, Lines, costing
from planning_support import DAY
from project_rows import AT
from remaining_support import Review, in_progress, line_named, task_named
from sqlalchemy.orm import Session

from waterfall.core.cost_settings.interface import (
    IndexThresholds,
    SettingsChange,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.core.revisions.interface import mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest
    from nodes_support import Tree
    from projects_support import Scene
    from support import ContractClient

# --- A document kept, around the service ---------------------------------------------------------


def indicator_row(project_id: UUID, revision_id: UUID, **overrides: object) -> dict[str, object]:
    """Give the columns of a document a marking keeps: the indicators of the estimate, at ``AT``."""
    return {
        "project_id": project_id,
        "id": uuid4(),
        "revision_id": revision_id,
        "kind": "estimate",
        "scope": "project",
        "document": {"context": {"revision_id": str(revision_id), "is_stored": True}},
        "computed_at": AT,
        "created_at": AT,
        "created_by": None,
        **overrides,
    }


# --- The clock -----------------------------------------------------------------------------------

# The routes of the indicators that read the instant of their computation (``utc_now``): the clock
# is set in each, and a route that stops reading it under that name fails the setting.
READING_ROUTES = (
    "waterfall.api.project_indicators",
    "waterfall.api.estimate_indicators",
    "waterfall.api.remaining_indicators",
)
# Those a later story serves (US-1690, US-1700, US-1710): set whether they read it yet or not.
ROUTES = (
    "waterfall.api.indicator_curves",
    "waterfall.api.index_history",
    "waterfall.api.milestone_tracking",
)

type Clock = Callable[[date], datetime]


def clock_setter(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the routes of the indicators read as today; give its instant.

    The instant is nine in the morning in universal time; the marking of ``marked`` takes it too.
    """

    def set_day(day: date) -> datetime:
        instant = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC)
        for route in READING_ROUTES:
            monkeypatch.setattr(f"{route}.utc_now", lambda: instant)
        for route in ROUTES:
            monkeypatch.setattr(f"{route}.utc_now", lambda: instant, raising=False)
        monkeypatch.setattr(f"{__name__}.now", lambda: instant)
        return instant

    return set_day


def now() -> datetime:
    """Give the instant the clock is set at: the real one until a test sets it."""
    return datetime.now(UTC)


def marked(stage: Scene, revision: dict[str, Any], version_name: str) -> datetime:
    """Mark a revision by the transaction of the worker, at the instant of the clock; give it."""
    at = now()
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        marking = (UUID(revision["revision_id"]), version_name, None)
        mark_revision(session, *marking, Act(None, at))
    return at


# --- The thresholds of the indices ---------------------------------------------------------------


def thresholds(stage: Scene, watch: str, alert: str) -> None:
    """Set the watch and alert thresholds of both indices, as ``updateReferenceSettings`` does."""
    held = IndexThresholds(Decimal(watch), Decimal(alert), Decimal(watch), Decimal(alert))
    with stage.database.transaction() as session:
        counter = read_reference_settings(session).lock_version
        change = SettingsChange(index_thresholds=held)
        write_reference_settings(session, change, counter, Act(None, utc_now()))


# --- A project under way, through the interfaces -------------------------------------------------

# The two tasks of the project and the amount of the line of material each bears: the studies,
# completed, and the wiring, started.
STUDIES, WIRING = "Études", "Câblage"
AMOUNTS = {STUDIES: "1000", WIRING: "3000"}
# The days the studies started and completed, and the wiring started, in the week its planning
# starts (a Monday); the day the clock is set at, the Friday of the week after.
STARTED_ON = DAY
COMPLETED_ON = DAY + timedelta(days=3)
TODAY = DAY + timedelta(days=11)
# The lines of cost loaded, imputed to the project alone: their document and their amount.
COSTS = (("FA-1001", "800.00"), ("FA-1002", "450.00"))


@dataclass(frozen=True)
class UnderWay:
    """A project In progress: its reference and current revision, its tasks, its costs, its day.

    ``studies`` is completed on ``COMPLETED_ON`` and ``wiring`` started on ``STARTED_ON``, in the
    current revision, as the reading of its structure gives them — the studies by the entry of the
    remaining to commit of their line, set to nought, which completes a task that bears lines
    (WF-RAE-0030) —; ``now`` the instant of the clock.
    """

    stage: Scene
    review: Review
    costs: Costing
    studies: dict[str, Any]
    wiring: dict[str, Any]
    cost_import_id: UUID
    now: datetime

    @property
    def project_id(self) -> UUID:
        """Give the identifier of the project."""
        return UUID(self.stage.project["project_id"])

    @property
    def tree(self) -> Tree:
        """Give the main structure of the current revision."""
        return self.review.tree


def progressed(tree: Tree, node: dict[str, Any], state: str, on: date) -> dict[str, Any]:
    """Move a task of the current revision to a state, at a day, as its manager does; give it."""
    sent = {"progress": state, "lock_version": node["lock_version"], "occurred_on": on.isoformat()}
    path = f"{tree.path}/nodes/{node['node_id']}/progress"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
    return answer.json()["nodes"][0]


def zeroed(tree: Tree, line: dict[str, Any], on: date) -> None:
    """Set the remaining to commit of the last open line of a task to nought, completing it."""
    sent = {
        "lock_version": line["lock_version"],
        "reestimated_amount_basis": {"quantity": "0"},
        "completed_on": on.isoformat(),
    }
    path = f"{tree.path}/nodes/{line['node_id']}/remaining"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def under_way(api: ContractClient, stage: Scene, clock: Clock) -> UnderWay:
    """Write a project In progress through the interfaces, its tasks moved, its costs loaded.

    Two tasks, each with a line of material, priced in a first revision, marked and designated as
    the reference; the code entered moves the project In progress, and its current revision is
    opened from the reference. There, the studies are completed and the wiring started; two lines
    of cost are loaded; the clock is set at ``TODAY``.
    """
    costs = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        for label, amount in AMOUNTS.items():
            task = tree.made(label)
            lines.made(
                task,
                label=f"Matériel {label}",
                quantity="1",
                cost_category_id=str(costs.material),
                unit_disbursement=amount,
            )

    review = in_progress(api, stage, build)
    tree = review.tree
    progressed(tree, task_named(tree, STUDIES), "started", STARTED_ON)
    zeroed(tree, line_named(tree, f"Matériel {STUDIES}"), COMPLETED_ON)
    wiring = progressed(tree, task_named(tree, WIRING), "started", STARTED_ON)
    studies = task_named(tree, STUDIES)
    assert (studies["task"]["progress"], studies["task"]["completed_on"]) == (
        "completed",
        COMPLETED_ON.isoformat(),
    )
    project_id = UUID(stage.project["project_id"])
    loaded = load_import(
        stage, project_id, [cost(number, None, amount) for number, amount in COSTS]
    )
    at = clock(TODAY)
    return UnderWay(stage, review, costs, studies, wiring, loaded, at)
