# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the state of a summary and of its own lines (US-2780/L1), without a base.

A summary whose subordinates are all completed (WF-PLA-0040), derived from a tree built in memory
(``Tree`` of rows, ``derived_states``, ``awaits``), from the fixture ``summary_own_lines.json``.
Which summaries an own line holds open (``Tree.held``) is what the estimate tells when a tree is
read, from the remaining of the lines: here it is given, as the reading would give it, and the
remaining of the example is the premise that puts a summary in it. What the reading of a tree
does with the lines on a database is replayed by ``test_open_lines.py``.
"""

from datetime import date
from decimal import Decimal
from functools import partial
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest

from waterfall.core.planning.tree import LINE, TASK, NodeRow, TaskRow, Tree
from waterfall.core.planning.views import State, awaits, derived_states, own_lines

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
DAY = date(2026, 3, 2)


def _node(node_id: UUID, kind: str, parent: UUID | None, rank: int) -> NodeRow:
    return NodeRow(node_id, uuid4(), uuid4(), kind, parent, rank, None, 1)


def _row(label: str, progress: str, started: date | None, completed: date | None) -> TaskRow:
    return TaskRow(
        label,
        None,
        "automatic",
        Decimal(1),
        "d",
        DAY,
        Decimal(0),
        DAY,
        Decimal(8),
        progress,
        started,
        completed,
        None,
        None,
        None,
        None,
        is_critical=False,
    )


def _summary_and_one_line(
    data: Example, *, own: bool
) -> tuple[Tree[NodeRow, TaskRow], UUID, list[State]]:
    """Build a summary of two completed subordinates and one line: an own one, or a provision."""
    below = cast("dict[str, str]", data["subordinates"])
    started = date.fromisoformat(below["started_on"])
    completed = date.fromisoformat(below["completed_on"])
    summary, first, second, line = uuid4(), uuid4(), uuid4(), uuid4()
    nodes = {
        summary: _node(summary, TASK, None, 1),
        first: _node(first, TASK, summary, 1),
        second: _node(second, TASK, summary, 2),
        line: _node(line, LINE, summary, 1),
    }
    tasks = {
        summary: _row("Étude", "started", started, None),
        first: _row("Schémas", below["progress"], started, completed),
        second: _row("Relecture", below["progress"], started, completed),
    }
    # An own line of a remaining to commit holds the summary open; a provision never does.
    tree = Tree(
        nodes,
        tasks,
        held=frozenset({summary}) if own else frozenset(),
        provisions=frozenset() if own else frozenset({line}),
    )
    states = derived_states(tree, partial(own_lines, tree))
    return tree, summary, [states[first], states[second]]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_of_completed_subordinates_held_by_an_own_line_of_500_is_started_and_flagged(
    example: Callable[[str], Example],
) -> None:
    # « Une récapitulative dont toutes les subordonnées sont terminées et dont une ligne propre
    # porte un reste à engager de 500 est démarrée et signalée ; la saisie d'un reste nul sur
    # cette ligne la termine. » The first clause only: the entry of a nought remaining, which
    # completes it, writes the estimate and its facet and takes a database (it is replayed by
    # ``test_open_lines.py``; its declaration out of the harness is the lot L2).
    data = example("WF-PLA-0040-A#4b10e3009332")
    assert Decimal(cast("str", data["own_line_remaining"])) != 0
    tree, summary, below = _summary_and_one_line(data, own=True)
    assert all(each.progress == "completed" for each in below)
    state = derived_states(tree, partial(own_lines, tree))[summary]
    assert (state.progress, state.started_on, state.completed_on) == ("started", DAY, None)
    assert awaits(tree, summary, below)


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_of_completed_subordinates_whose_only_line_is_a_provision_of_40_is_completed(
    example: Callable[[str], Example],
) -> None:
    # « Une récapitulative dont toutes les subordonnées sont terminées et dont la seule ligne propre
    # est une provision de 40 est terminée et n'est pas signalée. »
    data = example("WF-PLA-0040-A#017bc131bcfa")
    assert Decimal(cast("str", data["provision"])) == 40
    tree, summary, below = _summary_and_one_line(data, own=False)
    assert all(each.progress == "completed" for each in below)
    state = derived_states(tree, partial(own_lines, tree))[summary]
    completed = date.fromisoformat(cast("dict[str, str]", data["subordinates"])["completed_on"])
    assert (state.progress, state.completed_on) == ("completed", completed)
    assert not awaits(tree, summary, below)
