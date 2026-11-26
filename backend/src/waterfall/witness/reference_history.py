# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The history of PRJ-001 in the reference set: fifteen years of monthly reviews (US-2950).

The witness holds PRJ-001, the project of a thousand tasks, with the revisions of its chronology:
two marked, the third, the 102, open. The set prolongs it to the volumes of §4.6.2 — a hundred and
eighty revisions marked, eighteen thousand lines of actual cost — by one step a month, the first
Monday of the months that follow the witness's last event (June 2026), whose each:

- applies the import of actual costs of the month, six days before the review: its lines drawn from
  the seed, a hundred a month but for the few that bring the total to the one asked;
- marks the revision in progress, as the worker marks it (``load_marking``), under the name of its
  month, « Revue de juillet 2026 »;
- opens the next by the copy of the one just marked, an hour later (``load_revision``).

Each step goes through the interfaces of the modules, as the witness is written, never by an
``INSERT``, under the platform as author and the instant of its event (``Act.at``); the identifiers
a module draws are drawn in order (``drawn_in_order``), the others derived from the seed. One step
is one transaction, which ``reference_load`` makes: a hundred and eighty markings do not hold in the
single transaction of the witness. A step is a whole or nothing: the platform's marked revisions
say where the history stands, and a command stopped is taken up at the step after the last it
committed (``steps_done``), the same history whatever the run it is written in.

The history is a property of the witness's description (``Plan``): the revisions the witness marks
of PRJ-001 and the lines it holds are read in it, so that the set asks for a total — a hundred and
eighty revisions, eighteen thousand lines — and the plan derives what remains to write. What a
revision holds is what the witness describes of it, copied from one to the next: the history
changes no task and no line of the estimate, and lays no progress — the months are those of a
project whose plan does not move.
"""

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.costs.interface import CostLineLoad
from waterfall.core.projects.interface import projects_present
from waterfall.core.revisions.interface import (
    current_revision,
    load_marking,
    load_revision,
    marked_revisions,
)
from waterfall.witness import costs, revisions
from waterfall.witness.portfolio import project_manager, write_import
from waterfall.witness.projects import PROJECTS_FILE, Projects
from waterfall.witness.reference_draw import Draw, identifier
from waterfall.witness.reference_projects import MONTHS, REOPENED_AFTER

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.witness.description import Witness

# The project the history prolongs, by its code in ``projects.json``.
CODE = "PRJ-001"
# The volumes of table 13 (§4.6.2): the revisions marked and the lines of actual cost of PRJ-001.
MARKED = 180
COST_LINES = 18_000
# The month the first step falls in: the one after the last event of the witness (June 2026).
FIRST_MONTH = (2026, 7)
# The import of a month is applied this long before its review.
IMPORTED_BEFORE = timedelta(days=6)


class HistoryError(ValueError):
    """A history that asks what the steps cannot write: lines, and no revision to mark with."""


@dataclass(frozen=True, slots=True)
class History:
    """The volumes PRJ-001 holds once its history is written: its revisions marked, its cost lines.

    A total, the witness's own counted: a history that asks no more than the witness holds writes
    nothing.
    """

    marked: int = MARKED
    cost_lines: int = COST_LINES


@dataclass(frozen=True, slots=True)
class Plan:
    """What the history of PRJ-001 writes, read in the description of the witness.

    ``project_id`` is PRJ-001's, ``manager`` its project manager; ``marked`` and ``lines`` what the
    witness gives it, ``steps`` the months to write and ``added`` the lines they bring in all.
    """

    project_id: UUID
    manager: UUID
    marked: int
    steps: int
    added: int

    @classmethod
    def read(cls, witness: Witness, history: History) -> Plan:
        """Read the plan in the witness; refuse a history that asks lines no step could bring."""
        code = next(
            each
            for each in witness.read(PROJECTS_FILE, Projects).items
            if each.code is not None and each.code.root == CODE
        )
        project_id = code.project_id.root
        marked = sum(
            each.project_id.root == project_id and each.status.value == "marked"
            for each in witness.read(revisions.REVISIONS_FILE, revisions.Revisions).items
        )
        held = len(costs.Costs.read(witness).costs.lines)
        steps = max(0, history.marked - marked)
        added = max(0, history.cost_lines - held)
        if added > 0 and steps == 0:
            message = (
                f"{added} lines of cost are asked of the history of {CODE}, "
                f"and no revision to mark them with"
            )
            raise HistoryError(message)
        return cls(project_id, project_manager(witness).user_id, marked, steps, added)

    def lines_of(self, step: int) -> int:
        """Count the lines the ``step``-th month imports: an equal share, early months one more."""
        share, rest = divmod(self.added, self.steps)
        return share + (1 if step <= rest else 0)


def review_of(step: int) -> datetime:
    """Give the instant of the ``step``-th review: the first Monday of its month, at nine, UTC."""
    months = FIRST_MONTH[0] * 12 + FIRST_MONTH[1] - 1 + step - 1
    first = date(months // 12, months % 12 + 1, 1)
    return datetime.combine(first + timedelta(days=-first.weekday() % 7), time(9), tzinfo=UTC)


def name_of(step: int) -> str:
    """Give the name of version of the ``step``-th review, which bears its month."""
    month = review_of(step)
    return f"Revue de {MONTHS[month.month - 1]} {month.year}"


def revision_id_of(step: int) -> UUID:
    """Give the identifier of the revision the ``step``-th step opens."""
    return identifier("history_revision", step)


def steps_done(session: Session, plan: Plan) -> int:
    """Count the steps the platform holds: the revisions of PRJ-001 marked beyond the witness's.

    Nothing of PRJ-001 held, none: the witness is loaded before the history is.
    """
    if not projects_present(session, {plan.project_id}):
        message = f"the history of {CODE} is written on a platform that does not hold {CODE}"
        raise ValueError(message)
    return len(marked_revisions(session, plan.project_id)) - plan.marked


def write_step(session: Session, plan: Plan, step: int, act: Act) -> None:
    """Write the ``step``-th month of the history of PRJ-001 in the transaction of ``session``.

    Its import, the marking of the revision in progress, the opening of the next; ``act`` is the
    platform's, its instant replaced by each event's own.
    """
    project_id = plan.project_id
    reviewed = review_of(step)
    in_progress = current_revision(session, project_id)
    if in_progress is None:
        message = f"{CODE} holds no revision in progress to mark at its step {step}"
        raise ValueError(message)
    lines = month_lines(plan, step, reviewed)
    imported = reviewed - IMPORTED_BEFORE
    cost_import_id = identifier("history_import", step)
    write_import(
        session,
        project_id,
        (cost_import_id, lines),
        (plan.manager, replace(act, at=imported)),
    )
    load_marking(session, in_progress, name_of(step), None, replace(act, at=reviewed))
    load_revision(
        session,
        project_id,
        revision_id_of(step),
        replace(act, at=reviewed + REOPENED_AFTER),
    )


def month_lines(plan: Plan, step: int, reviewed: datetime) -> list[CostLineLoad]:
    """Draw the lines of the import of a step, from the seed and its number alone."""
    draw = Draw("history", step)
    imported = (reviewed - IMPORTED_BEFORE).date()
    return [
        CostLineLoad(
            cost_line_id=identifier("history_cost_line", step, item),
            document_number=f"FA-{CODE}-{step:03d}",
            document_item=str(item),
            document_date=imported - timedelta(days=draw.between(1, 28)),
            amount=Decimal(f"{100 * draw.between(5, 200)}.00"),
            subproject_code=None,
        )
        for item in range(1, plan.lines_of(step) + 1)
    ]
