# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``waterfall-api check-reference``: what the platform holds of the reference set (US-2950).

The set is checked on the platform, never against the examples of the contract at three hundred
projects (``fixtures/api/volume/``): the witness stays the oracle of the values, and the set the
oracle of the volumes. Three things are read, each by the interfaces of the modules:

- the volumes: the projects, the marked revisions and the lines of cost the platform counts, as a
  backup counts them (``waterfall.worker.inventory``), against what the seed and the witness give
  — the witness's own, the projects drawn, the history of PRJ-001 (``reference_history``) — ; and
  the nodes, the roles and the accounts drawn, each present under its identifier and its label;
- the reproducibility: the identifiers of everything the seed derives are present, the revisions of
  the history of PRJ-001 included, and the portfolio holds the projects of the draw and no other —
  a set engendered twice, or restored, is the same set (WF-QUA-0040);
- the invariants of the portfolio: its count is the projects it holds in pricing and in progress,
  and its order book, the sum of the reference budgets of its projects in progress, is the sum of
  the budgets that the estimate (``portfolio_totals``) reads of each of them, one by one, on the
  reference of the project.

``check`` gives the faults, one sentence each; none, the set is whole. The command prints each
volume it counted, then the faults, and ends 0, or 1 on any fault, or 2 on a setting that lacks.
"""

import argparse
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall import schema
from waterfall.core.costs.interface import count_cost_lines
from waterfall.core.estimate.interface import portfolio_totals
from waterfall.core.portfolio.interface import (
    PortfolioListing,
    read_portfolio_projects,
    read_portfolio_value,
)
from waterfall.core.portfolio.interface.scope import PortfolioAsked, PortfolioReading
from waterfall.core.projects.interface import Viewer, count_projects, projects_present
from waterfall.core.resource_settings.interface import node_labels, roles_present
from waterfall.core.revisions.interface import (
    count_marked_revisions,
    read_revision_for,
    revisions_present,
)
from waterfall.core.users.interface import read_account_labels
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.settings import SettingsError, load_witness_settings
from waterfall.witness import costs, portfolio_slice, revisions
from waterfall.witness.description import Witness
from waterfall.witness.portfolio import project_manager
from waterfall.witness.reference_draw import PROJECTS, Base, Reference, draw_reference
from waterfall.witness.reference_history import (
    COST_LINES,
    MARKED,
    History,
    HistoryError,
    Plan,
    revision_id_of,
)
from waterfall.witness.reference_load import read_base
from waterfall.witness.reference_projects import draw_project, numbers_of, project_id_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

COMMAND = "check-reference"
IN_PROGRESS = "in_progress"
# The page of the portfolio the invariants read: all of it.
EVERYTHING = 100_000


@dataclass(frozen=True, slots=True)
class Volumes:
    """What a platform counts: its projects, its marked revisions, its lines of actual cost."""

    projects: int
    marked_revisions: int
    cost_lines: int


@dataclass(slots=True)
class Report:
    """What the check found: the volumes counted, those expected, and the faults."""

    held: Volumes
    expected: Volumes
    faults: list[str] = field(default_factory=list[str])
    compared: int = 0
    warnings: list[str] = field(default_factory=list[str])


def expected_volumes(
    witness: Witness, base: Base, reference: Reference, volumes: tuple[int, Plan]
) -> Volumes:
    """Give the volumes the set holds for ``wanted`` projects in the portfolio, from the seed alone.

    The witness's — its revisions marked, its lines of cost, the projects of its slice with theirs
    —,
    the projects the draw adds with theirs, and the history of PRJ-001.
    """
    wanted, plan = volumes
    sliced = portfolio_slice.read(witness)
    drawn = [
        draw_project(number, base, reference) for number in numbers_of(wanted - base.portfolio)
    ]
    # ``revisions.json`` holds the revisions of the witness's own projects; the ten projects of the
    # slice (``PRJ-30n``) hold theirs in their files, counted through ``sliced``: none is in both.
    marked = sum(
        each.status.value == "marked"
        for each in witness.read(revisions.REVISIONS_FILE, revisions.Revisions).items
    )
    lines = len(costs.Costs.read(witness).costs.lines)
    return Volumes(
        projects=base.projects + len(drawn),
        marked_revisions=marked
        + sum(rev.marked_at is not None for each in (*sliced, *drawn) for rev in each.revisions)
        + plan.steps,
        cost_lines=lines
        + sum(len(imported.lines) for each in (*sliced, *drawn) for imported in each.imports)
        + plan.added,
    )


def check(session: Session, witness: Witness, wanted: int, history: History) -> Report:
    """Check the platform ``session`` reads holds ``wanted`` projects, and the ``history``."""
    base = read_base(witness)
    reference = draw_reference(base)
    plan = Plan.read(witness, history)
    expected = expected_volumes(witness, base, reference, (wanted, plan))
    held = Volumes(
        count_projects(session), count_marked_revisions(session), count_cost_lines(session)
    )
    report = Report(held, expected, warnings=list(plan.short))
    for name in ("projects", "marked_revisions", "cost_lines"):
        if getattr(held, name) != getattr(expected, name):
            report.faults.append(
                f"{name}: {getattr(held, name)} held, {getattr(expected, name)} expected"
            )
    _check_identifiers(session, (base, reference, plan, wanted), report.faults)
    report.compared = _check_portfolio(session, project_manager(witness), report.faults)
    return report


def _check_identifiers(
    session: Session, drawn: tuple[Base, Reference, Plan, int], faults: list[str]
) -> None:
    """Hold that every identifier and label the seed derives is on the platform."""
    base, reference, plan, wanted = drawn
    nodes = {each.node_id: each.label for each in reference.nodes}
    labels = node_labels(session, set(nodes))
    faults.extend(
        f"node {each}: absent or relabelled" for each in nodes if labels.get(each) != nodes[each]
    )
    roles = {each.role_id for each in reference.roles}
    faults.extend(f"role {each}: absent" for each in sorted(roles - roles_present(session, roles)))
    accounts = {each.user_id for each in reference.accounts}
    held = read_account_labels(session, accounts)
    faults.extend(f"account {each}: absent" for each in sorted(accounts - held.keys()))
    ids = {project_id_of(number) for number in numbers_of(wanted - base.portfolio)}
    faults.extend(
        f"project {each}: absent" for each in sorted(ids - projects_present(session, ids))
    )
    history = {revision_id_of(step) for step in range(1, plan.steps + 1)}
    faults.extend(
        f"revision {each} of the history: absent"
        for each in sorted(history - revisions_present(session, history))
    )


def _check_portfolio(session: Session, manager: Viewer, faults: list[str]) -> int:
    """Hold the sums of the portfolio: its count, its rows and its order book are its projects'.

    Each reference budget a row shows is the one the estimate reads of the project; the order book
    is their sum. Give how many budgets of projects in progress it was compared with.
    """
    reading = PortfolioReading(at=utc_now())
    asked = PortfolioAsked()
    listed = read_portfolio_projects(
        session, asked, PortfolioListing(limit=EVERYTHING, offset=0), reading, manager
    )
    value = read_portfolio_value(session, asked, reading)
    rows = listed["items"]
    if listed["meta"]["total"] != len(rows) or listed["scope"]["project_count"] != len(rows):
        faults.append(
            f"portfolio: {len(rows)} projects listed, {listed['meta']['total']} counted, "
            f"{listed['scope']['project_count']} in its scope"
        )
    budgets: list[Decimal] = []
    for each in rows:
        if each["state"] != IN_PROGRESS or each["reference_budget"] is None:
            continue
        shown = Decimal(each["reference_budget"])
        budgets.append(shown)
        read = _budget_of(session, UUID(str(each["project_id"])))
        if read != shown:
            faults.append(
                f"portfolio: project {each['project_id']} shows a reference budget {shown}, "
                f"the estimate reads {read}"
            )
    if Decimal(value["order_book"]) != sum(budgets, Decimal(0)):
        faults.append(
            f"portfolio: order book {value['order_book']}, "
            f"the sum of its {len(budgets)} projects' budgets {sum(budgets, Decimal(0))}"
        )
    return len(budgets)


def _budget_of(session: Session, project_id: UUID) -> Decimal:
    """Read the reference budget of a project on the estimate, as its own module gives it."""
    revision_id = read_revision_for(session, project_id, None).revision_id
    totals = portfolio_totals(session, project_id, revision_id)
    return sum(totals.budget_by_cost_type.values(), Decimal(0))


def main(arguments: Sequence[str]) -> int:
    """Run ``check-reference``: print the volumes, then the faults; give the status."""
    parser = argparse.ArgumentParser(
        prog=f"waterfall-api {COMMAND}",
        description="Check the platform holds the reference set of WF-QUA-0040, whole.",
    )
    parser.add_argument("--projects", type=int, default=PROJECTS)
    parser.add_argument("--revisions", type=int, default=MARKED)
    parser.add_argument("--cost-lines", type=int, default=COST_LINES)
    parsed = parser.parse_args(arguments)
    try:
        settings = load_witness_settings()
    except SettingsError as error:
        sys.stderr.write(f"waterfall-api {COMMAND}: {error}\n")
        return 2
    schema.declared()
    witness = Witness(Path(settings.witness_path), Act(None, utc_now()))
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    try:
        with TIME_ZONE.reading_from(stored_in(database)), database.transaction() as session:
            report = check(
                session, witness, parsed.projects, History(parsed.revisions, parsed.cost_lines)
            )
    except HistoryError as refused:
        sys.stderr.write(f"waterfall-api {COMMAND}: {refused}\n")
        return 2
    finally:
        database.dispose()
    for name in ("projects", "marked_revisions", "cost_lines"):
        sys.stdout.write(
            f"{name}: {getattr(report.held, name)} (expected {getattr(report.expected, name)})\n"
        )
    sys.stdout.write(f"order book: the budgets of {report.compared} projects in progress summed\n")
    for warning in report.warnings:
        sys.stderr.write(f"waterfall-api {COMMAND}: warning: {warning}\n")
    for fault in report.faults:
        sys.stdout.write(f"fault: {fault}\n")
    return 1 if report.faults else 0
