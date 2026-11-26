# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``waterfall-api load-reference``: the reference set of WF-QUA-0040 on a platform (US-2950).

``load-reference [--projects N]``: the witness first, as ``load-witness`` loads it — or nothing,
on a platform that holds it —, then what the seed draws beside it (``reference_draw``,
``reference_projects``): the nodes, the roles and the accounts the witness lacks of table 13, in
one transaction, then the projects until the portfolio holds ``N`` — in pricing and in progress,
three hundred by default, the witness's counted, as table 13 counts them; the closed ones — lost,
abandoned, completed — come in addition —, each in a transaction of its own. Everything is
written through the interfaces of the modules, as the witness is, never by an ``INSERT``, as the
platform, under the identifiers the seed derives; those a module draws are drawn in order
(``drawn_in_order``), under an instant of each transaction's own, so that two engenderings give the
same ones whatever the run they are made in.

Stopped — a failure, a deadline, a machine down —, it is taken up where it stopped: a project the
platform holds is passed over, a transaction never half written. ``N`` below the witness's projects
of the portfolio stops it at start (2), after the witness; a rule of a module that refuses an
object, or any failure, ends it (1), said in the structured logs, the transactions committed
before kept.
"""

import argparse
import sys
import time
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall import schema
from waterfall.api.contract.models import CostTypeKind, HourlyRateGrid, ProjectState
from waterfall.api.resource_role_admission import category_admission
from waterfall.core.projects.interface import Viewer, projects_present
from waterfall.core.resource_settings.interface import (
    NodeWrite,
    RoleDraft,
    create_node,
    create_role,
    node_labels,
    roles_present,
)
from waterfall.core.revisions.interface import create_project_partitions
from waterfall.core.users.interface import Identity, create_local_account, read_account_labels
from waterfall.platform.audit import Act
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import ServiceError
from waterfall.platform.identifiers import drawn_in_order
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.logs import PLATFORM, get_logger, logging_context
from waterfall.platform.settings import load_witness_settings
from waterfall.witness import (
    calendars,
    cost_categories,
    hourly_rates,
    org_nodes,
    portfolio_slice,
    projects,
    resource_roles,
    timeline,
)
from waterfall.witness.description import Witness, is_loaded
from waterfall.witness.portfolio import default_week, write_project
from waterfall.witness.reference_draw import PROJECTS, Base, Reference, draw_reference
from waterfall.witness.reference_history import (
    CODE,
    COST_LINES,
    MARKED,
    History,
    HistoryError,
    Plan,
    steps_done,
    write_step,
)
from waterfall.witness.reference_projects import (
    code_of,
    draw_project,
    manager_of,
    numbers_of,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from sqlalchemy.orm import Session

    from waterfall.platform.settings import WitnessSettings
    from waterfall.witness.portfolio import Week

COMMAND = "load-reference"
# The volumes of table 13 for PRJ-001: the history the command writes unless it is asked less.
FULL = History()
# The states of a project in the portfolio: in pricing, or in progress.
PORTFOLIO = frozenset({ProjectState.pricing.value, ProjectState.in_progress.value})
# The key of the advisory lock each transaction of the reference set holds.
REFERENCE_SET_LOCK = 4_202_950
# The instant the identifiers the set draws bear, a millisecond more for each transaction: the
# reference at nought, the n-th project at n. A day after the witness's, whose they never meet.
DRAWN_AT = datetime(2025, 9, 2, 9, 0, tzinfo=UTC)
# The rank of the transaction of the first step of the history of PRJ-001: beyond the numbers of the
# projects, so that no project and no step draw under the same instant.
HISTORY_RANK = 1_000_000

logger = get_logger(__name__)


def main(arguments: Sequence[str], load_witness: Callable[[], int]) -> int:
    """Run ``load-reference``: the witness by ``load_witness``, its command, then the set.

    The arguments are read first, a fault stopping the command before it writes (2).
    """
    parser = argparse.ArgumentParser(
        prog=f"waterfall-api {COMMAND}",
        description="Load the reference set of WF-QUA-0040: the witness, then what a seed draws.",
    )
    parser.add_argument(
        "--projects",
        type=int,
        default=PROJECTS,
        help=f"the projects of the set in the portfolio, the witness's too (default {PROJECTS})",
    )
    parser.add_argument(
        "--revisions",
        type=int,
        default=MARKED,
        help=f"the revisions of {CODE} marked, the witness's too (default {MARKED}); a smaller "
        "history is for a trial",
    )
    parser.add_argument(
        "--cost-lines",
        type=int,
        default=COST_LINES,
        help=f"the lines of actual cost of {CODE}, the witness's too (default {COST_LINES})",
    )
    parsed = parser.parse_args(arguments)
    status = load_witness()
    if status != 0:
        return status
    return load_reference(
        load_witness_settings(), parsed.projects, History(parsed.revisions, parsed.cost_lines)
    )


def load_reference(settings: WitnessSettings, wanted: int, history: History = FULL) -> int:
    """Load the set, ``wanted`` projects in all, on a platform that holds the witness.

    The history of PRJ-001 is written to ``history``'s volumes, after the projects.

    Under a correlation of its own, as the platform; give the status of the command.
    """
    schema.declared()
    witness = Witness(Path(settings.witness_path), Act(None, utc_now()))
    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        try:
            base = read_base(witness)
        except Exception:
            # A description the witness lacks or that strays: said in the logs, not a trace.
            logger.exception("reference.failed", project=None)
            return 1
        if wanted < base.portfolio:
            sys.stderr.write(
                f"waterfall-api {COMMAND}: --projects: {wanted} is fewer than the "
                f"{base.portfolio} projects of the witness in the portfolio\n"
            )
            return 2
        try:
            plan = Plan.read(witness, history)
        except HistoryError as refused:
            sys.stderr.write(f"waterfall-api {COMMAND}: {refused}\n")
            return 2
        database = Database(create_database_engine(settings.database_url.get_secret_value()))
        try:
            TIME_ZONE.read_from(stored_in(database))
            return _load(database, witness, (base, plan), wanted)
        finally:
            database.dispose()


def read_base(witness: Witness) -> Base:
    """Read in the description of the witness what the draw attaches to, and what it counts."""
    grid = witness.read(hourly_rates.FILE, HourlyRateGrid)
    categories = witness.read(cost_categories.FILE, cost_categories.CostCategories).items
    active = [each for each in categories if each.is_active]
    provisions = [each for each in active if each.cost_type_kind == CostTypeKind.provision]
    if len(provisions) != 1:
        message = f"{cost_categories.FILE} names {len(provisions)} active provisions, not one"
        raise ValueError(message)
    held = witness.read(calendars.FILE, calendars.Calendars).items
    listed = witness.read(projects.PROJECTS_FILE, projects.Projects).items
    sliced = portfolio_slice.read(witness)
    # The chronology moves PRJ-001 alone: PRJ-002 is held in ``created``, whatever its file says.
    moved = {
        write.project: write.to_state
        for _, write in timeline.read(witness).writes()
        if isinstance(write, timeline.StateTransition)
    }
    states = [
        str(moved.get(each.code.root if each.code else "", ProjectState.created)) for each in listed
    ] + [str(each.transitions[-1].to_state.value) for each in sliced]
    return Base(
        rated=tuple(
            row.cost_category_id.root
            for row in grid.rows
            if row.is_active and all(cell is not None for cell in row.cells)
        ),
        non_labour=tuple(
            each.cost_category_id.root
            for each in active
            if each.cost_type_kind == CostTypeKind.non_labor
        ),
        provision=provisions[0].cost_category_id.root,
        calendars=tuple(each.calendar_id.root for each in held if each.is_active),
        nodes=len(witness.read(org_nodes.FILE, org_nodes.OrgNodes).root),
        roles=len(witness.read(resource_roles.FILE, resource_roles.ResourceRoles).items),
        accounts=len(projects.described_accounts(witness)),
        projects=len(listed) + len(sliced),
        portfolio=sum(each in PORTFOLIO for each in states),
    )


def _load(database: Database, witness: Witness, volumes: tuple[Base, Plan], wanted: int) -> int:
    base, plan = volumes
    reference = draw_reference(base)
    week = default_week(witness)
    written: list[str] = []
    code: str | None = None
    try:
        wrote = _in_transaction(
            database, 0, lambda session: write_reference(session, witness, reference)
        )
        numbers = numbers_of(wanted - base.portfolio)
        for number in numbers:
            code = code_of(number)
            project = draw_project(number, base, reference)
            who = (Viewer(manager_of(number, reference), ()), week)
            if _in_transaction(
                database, number, partial(write_drawn_project, witness, project, who)
            ):
                written.append(code)
                logger.info("reference.project_loaded", project=code)
        code = CODE
        steps = _write_history(database, witness, plan)
    except ServiceError as refused:
        # A rule of a module refused an object of the set: a state to correct, not a trace.
        refusal = (refused.code, dict(refused.params))
    except Exception:
        logger.exception("reference.failed", project=code)
        return 1
    else:
        held = max(0, len(numbers) - len(written))
        logger.info(
            "reference.loaded",
            reference=wrote,
            projects=len(written),
            held=held,
            history=steps,
        )
        return 0
    logger.error("reference.refused", project=code, code=refusal[0], params=refusal[1])
    return 1


def _write_history(database: Database, witness: Witness, plan: Plan) -> int:
    """Write the months of the history of PRJ-001 the platform lacks, one transaction each.

    Take up at the step after the last the platform holds; give the steps written. A failure says
    its step in the logs (``reference.failed``, ``project`` ``PRJ-001``): the steps committed stay.
    """
    with database.transaction() as session:
        done = steps_done(session, plan)
    written = 0
    for step in range(done + 1, plan.steps + 1):
        began = time.monotonic()
        _in_transaction(
            database,
            HISTORY_RANK + step,
            lambda session, step=step: _step(session, witness, plan, step),
        )
        written += 1
        seconds = round(time.monotonic() - began, 1)
        logger.info(
            "reference.history_step", project=CODE, step=step, of=plan.steps, seconds=seconds
        )
    return written


def _step(session: Session, witness: Witness, plan: Plan, step: int) -> bool:
    write_step(session, plan, step, witness.act)
    return True


def _in_transaction(database: Database, rank: int, write: Callable[[Session], bool]) -> bool:
    """Run a write of the set in a transaction of its own, under the lock of the set.

    Its identifiers drawn in order under the instant of its rank, the lock taken first of all,
    before the partitions a project creates.
    """
    with database.transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(REFERENCE_SET_LOCK)))
        with drawn_in_order(DRAWN_AT + timedelta(milliseconds=rank)):
            return write(session)


def write_reference(session: Session, witness: Witness, reference: Reference) -> bool:
    """Write the nodes, the roles and the accounts the set draws, unless the platform holds them."""
    act = witness.act
    nodes = {each.node_id for each in reference.nodes}
    roles = {each.role_id for each in reference.roles}
    accounts = {each.user_id for each in reference.accounts}
    present = (
        set(node_labels(session, nodes))
        | roles_present(session, roles)
        | set(read_account_labels(session, accounts))
    )
    if is_loaded(nodes | roles | accounts, present):
        return False
    for node in reference.nodes:
        create_node(session, NodeWrite(node.code, node.label, node.parent_id), act, node.node_id)
    for role in reference.roles:
        draft = RoleDraft(
            role.code,
            role.label,
            role.node_id,
            role.category_id,
            category_admission(session, role.category_id),
            role.calendar_id,
            role.headcount,
        )
        create_role(session, draft, act, identifier=role.role_id)
    for account in reference.accounts:
        identity = Identity(account.last_name, account.first_name, account.email, account.node_id)
        create_local_account(
            session, identity, f"reference-{account.user_id}", act, account.user_id
        )
    return True


def write_drawn_project(
    witness: Witness, project: portfolio_slice.Project, who: tuple[Viewer, Week], session: Session
) -> bool:
    """Write a project of the set, its partitions first, unless the platform holds it."""
    if projects_present(session, {project.project_id}):
        return False
    create_project_partitions(session, project.project_id)
    write_project(session, witness.act, project, who)
    return True
