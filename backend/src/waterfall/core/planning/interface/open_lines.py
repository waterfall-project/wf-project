# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own lines that hold a summary task open: what the planning asks the lines (US-1590/L1).

A registry of this module (EP-09, "Les points d'extension"), filled by the estimate at the import of
its interface. A summary task is completed when all its subordinates are and the remaining to
commit of its own lines, the provisions left out, is nought (WF-PLA-0040): which of the tasks named
bear a line — of those given for each, the provisions left out already by their risk — whose
remaining is not nought, the planning cannot tell, the lines being the estimate's. It asks at the
reading of a tree, for the summaries whose subordinates are all completed: their state and their
signal (``TaskFacet.awaiting_own_lines``), and the leaf one of them becomes, which stays started
while a line holds it.

A second question, of the same module and filled by the same: the instant the own lines of a task
were set to nought, when none keeps a remaining (``zeroed_at``). A summary reopened by a
subordinate created under it, then completed again by the deletion of that subordinate, reads its
day there: the day its facet kept was cleared at the reopening, and its completion date is the
latest of its subordinates' and of the zeroing of its own lines (WF-PLA-0130, option B of #2803).
"""

from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

# What tells, of the tasks of a project given with the lines each bears, those a line holds open.
type OpenLines = Callable[[Session, UUID, Mapping[UUID, Sequence[UUID]]], frozenset[UUID]]

_OPEN_LINES: Registry[OpenLines] = Registry("planning.open_lines")

# What tells, of the tasks of a project given with the lines each bears, the instant their lines
# were last set to nought, for those none of whose lines keeps a remaining.
type ZeroedAt = Callable[[Session, UUID, Mapping[UUID, Sequence[UUID]]], Mapping[UUID, datetime]]

_ZEROED_AT: Registry[ZeroedAt] = Registry("planning.zeroed_at")


def register_open_lines(question: OpenLines) -> Callable[[], None]:
    """Add what tells which tasks an own line holds open; give its withdrawal.

    It answers for the tasks it is given at once, each with the lines it bears in their order, so
    that a reading asks the lines in one statement and not one a task.
    """
    return _OPEN_LINES.register(question)


def held_open(
    session: Session, project_id: UUID, lines_by_task: Mapping[UUID, Sequence[UUID]]
) -> frozenset[UUID]:
    """Tell which of these tasks a line holds open, by any module; none while nothing answers."""
    if not lines_by_task:
        return frozenset()
    found: set[UUID] = set()
    for question in _OPEN_LINES.entries():
        found |= question(session, project_id, lines_by_task)
    return frozenset(found)


def register_zeroed_at(question: ZeroedAt) -> Callable[[], None]:
    """Add what tells when the lines of tasks were last set to nought; give its withdrawal.

    It answers for the tasks it is given at once, as ``register_open_lines``: a task none of whose
    lines, the provisions left out, keeps a remaining and one of which was re-estimated, with the
    latest instant one was; the others are left out.
    """
    return _ZEROED_AT.register(question)


def zeroed_at(
    session: Session, project_id: UUID, lines_by_task: Mapping[UUID, Sequence[UUID]]
) -> dict[UUID, datetime]:
    """Tell when the lines of these tasks were last set to nought, by any module; none answering."""
    if not lines_by_task:
        return {}
    found: dict[UUID, datetime] = {}
    for question in _ZEROED_AT.entries():
        for task, instant in question(session, project_id, lines_by_task).items():
            found[task] = max(instant, found.get(task, instant))
    return found
