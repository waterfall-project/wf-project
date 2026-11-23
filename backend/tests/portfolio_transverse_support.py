# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the transverse tests of the portfolio share (US-2670/L4): the eight views and their writes.

The views, by the segment of their path and their operation; the permissions they are read under;
the clock the tests pin; and the writes the tests do around the fabrics (``portfolio_support``): a
review opened and marked at an instant, a project taken out of its cycle, the risks a marking kept.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from portfolio_listing_support import kept_changed
from portfolio_support import OFFER_PROBABILITY, OFFERS_OPENED, Portfolio, revision_opened
from projects_support import MANAGING

from waterfall.core.projects.interface import (
    ExitRequest,
    ProjectChange,
    Viewer,
    exit_project,
    stored_lock_version,
    update_project,
)
from waterfall.core.revisions.interface import mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    import pytest
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.core.projects.interface import ExitState

# The eight views, by the segment of their path under ``/api/v1/portfolio``, and the operation of
# each.
VIEWS = {
    "projects": "getPortfolioProjects",
    "value": "getPortfolioValue",
    "workload": "getPortfolioWorkload",
    "performance": "getPortfolioPerformance",
    "cost-structure": "getPortfolioCostStructure",
    "risks": "getPortfolioRisks",
    "cost-curve": "getPortfolioCostCurve",
    "pilot-health": "getPortfolioPilotHealth",
}
# The permissions of the eight views, each that of its function in the catalogue: the value is read
# under that of the list (``asked_portfolio_*``).
READS = (
    "portfolio_projects.read",
    "portfolio_workload.read",
    "portfolio_performance.read",
    "portfolio_cost_structure.read",
    "portfolio_risks.read",
    "portfolio_cost_curve.read",
    "portfolio_pilot_health.read",
)
# The views that retain a period, and those that take a node, as the contract says.
PERIODIC = ("projects", "value", "performance", "cost-structure", "risks", "cost-curve")
NODAL = ("projects", "value", "workload", "performance", "cost-structure")
# The current day of the tests of the day, after the whole chronology of the fabrics.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
# Every state a view counts somewhere, that a project of the fabrics holds.
COUNTED = "in_progress,pricing,completed"
CENT = Decimal("0.01")


def now_is(monkeypatch: pytest.MonkeyPatch, instant: datetime = NOW) -> None:
    """Pin the clock of the eight views, and of the indicators of a project, to an instant."""
    views = (f"portfolio_{name.replace('-', '_')}" for name in VIEWS)
    for route in (*views, "project_indicators", "estimate_indicators", "remaining_indicators"):
        monkeypatch.setattr(f"waterfall.api.{route}.utc_now", lambda: instant)


def weighted(amount: str | Decimal) -> Decimal:
    """Give an amount weighted by the probability of winning of the offer of the fabrics."""
    return (OFFER_PROBABILITY * Decimal(amount)).quantize(CENT)


def without_can_open(found: Any) -> Any:
    """Give an answer without the ``can_open`` of its rows, which a reader's rights alone change."""
    if isinstance(found, dict):
        rows = cast("dict[str, Any]", found)
        return {key: without_can_open(each) for key, each in rows.items() if key != "can_open"}
    if isinstance(found, list):
        return [without_can_open(each) for each in cast("list[Any]", found)]
    return found


def risk(number: int, label: str, provision: str) -> dict[str, Any]:
    """Give a risk identified as the document of a marking keeps it, its identifier its number."""
    return {
        "risk_id": str(UUID(int=number)),
        "label": label,
        "probability": "0.5000",
        "severity": "500.00",
        "provision_amount": provision,
        "state": "identified",
        "occurrence_cost": None,
        "occurred_reestimated_amount": None,
    }


def plant_risks(owner: Engine, risks: list[tuple[UUID, str, str]]) -> None:
    """Keep a risk identified in the document of each revision marked: its label, its provision."""
    for number, (revision_id, label, provision) in enumerate(risks, start=1):
        document = {"base": "1000.00", "risks": [risk(number, label, provision)]}
        kept_changed(owner, revision_id, "portfolio_risks", lambda _, kept=document: kept)


def marked_on(
    api: ContractClient, fabrics: Portfolio, project_id: UUID, name: str, instant: datetime
) -> None:
    """Open a revision of a project In progress and mark it at an instant, as its manager does."""
    revision_id = revision_opened(api, fabrics, project_id, instant)
    act = Act(fabrics.stage.manager.user_id, instant)
    with logging_context(correlation_id="marking"), fabrics.stage.database.transaction() as s:
        mark_revision(s, revision_id, name, None, act)


def exited(fabrics: Portfolio, project_id: UUID, to_state: ExitState, instant: datetime) -> None:
    """Take a project In progress, without a current revision, out of its cycle at an instant."""
    manager = fabrics.stage.manager.user_id
    with logging_context(correlation_id="exit"), fabrics.stage.database.transaction() as session:
        request = ExitRequest(to_state, None, stored_lock_version(session, project_id))
        exit_project(session, project_id, request, Act(manager, instant), Viewer(manager, MANAGING))


def probability_written(fabrics: Portfolio, project_id: UUID, probability: Decimal) -> None:
    """Write the probability of winning of a project In pricing, as its manager does."""
    manager = fabrics.stage.manager.user_id
    with logging_context(correlation_id="probability"), fabrics.stage.database.transaction() as s:
        change = ProjectChange({"win_probability": probability}, stored_lock_version(s, project_id))
        update_project(
            s, project_id, change, Act(manager, OFFERS_OPENED), Viewer(manager, MANAGING)
        )
