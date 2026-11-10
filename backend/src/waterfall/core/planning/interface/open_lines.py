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
"""

from typing import TYPE_CHECKING

from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

# What tells, of the tasks of a project given with the lines each bears, those a line holds open.
type OpenLines = Callable[[Session, UUID, Mapping[UUID, Sequence[UUID]]], frozenset[UUID]]

_OPEN_LINES: Registry[OpenLines] = Registry("planning.open_lines")


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
