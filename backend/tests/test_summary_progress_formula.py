# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of a summary task, as the pure formula computes it (US-1680), no database.

Beside the numeric examples of WF-IND-0060 (``examples/test_indicators_examples``), what the story
adds to them: the own lines of a summary counted in its total and earned when it is completed, a
subtree within another, a subtree without budgeted amount not computable, the one rounding to four
decimals, half to even, and only the summaries asked answered.
"""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from waterfall.core.indicators.formulas import (
    NO_BUDGETED_AMOUNT,
    Computable,
    SummaryTask,
    summary_progress,
)

D = Decimal


def task(parent: UUID | None, amount: str, *, completed: bool = False) -> SummaryTask:
    """Give a task under a parent, bearing an amount of its own lines, completed or not."""
    return SummaryTask(parent, completed, D(amount))


@pytest.mark.requirement("WF-IND-0060-A")
def test_the_own_lines_of_a_summary_count_in_its_total_and_are_earned_once_it_is_completed() -> (
    None
):
    # « … ses lignes propres comprises … » A summary bearing 100 of its own over subordinates of
    # 100, completed, and 200: 100 earned of 400; completed with all its subordinates, the whole.
    summary, first, second = uuid4(), uuid4(), uuid4()
    open_ = {
        summary: task(None, "100.00"),
        first: task(summary, "100.00", completed=True),
        second: task(summary, "200.00"),
    }
    assert summary_progress(open_, [summary]) == {summary: Computable.of(D("0.2500"))}
    done = {
        each: task(held.parent_id, str(held.earnable), completed=True)
        for each, held in open_.items()
    }
    assert summary_progress(done, [summary]) == {summary: Computable.of(D("1.0000"))}


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_summary_weighs_its_whole_subtree_and_a_summary_within_it_its_own() -> None:
    # A phase over a lot of two leaves, 300 completed and 100 not, and a leaf of 600 completed: the
    # phase earns 900 of 1 000, the lot 300 of 400.
    phase, lot = uuid4(), uuid4()
    tasks = {
        phase: task(None, "0"),
        lot: task(phase, "0"),
        uuid4(): task(lot, "300.00", completed=True),
        uuid4(): task(lot, "100.00"),
        uuid4(): task(phase, "600.00", completed=True),
    }
    assert summary_progress(tasks, [phase, lot]) == {
        phase: Computable.of(D("0.9000")),
        lot: Computable.of(D("0.7500")),
    }


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_summary_whose_subtree_bears_no_budgeted_amount_is_not_computable() -> None:
    # Not computable, never nought (WF-IND-0010): ``no_budgeted_amount``, though a task is
    # completed.
    summary = uuid4()
    tasks = {summary: task(None, "0"), uuid4(): task(summary, "0", completed=True)}
    found = summary_progress(tasks, [summary])[summary]
    assert (found.value, found.reason) == (None, NO_BUDGETED_AMOUNT)


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.parametrize(
    ("earned", "total", "shown"),
    [("1.00", "3.00", "0.3333"), ("1.00", "20000.00", "0.0000"), ("3.00", "20000.00", "0.0002")],
)
def test_the_progress_of_a_summary_is_rounded_once_to_four_decimals_half_to_even(
    earned: str, total: str, shown: str
) -> None:
    # A ratio to four decimals (README of the contract, "A share…"); 0.00005 to the even 0, and
    # 0.00015 to the even 2.
    summary = uuid4()
    rest = str(D(total) - D(earned))
    tasks = {
        summary: task(None, "0"),
        uuid4(): task(summary, earned, completed=True),
        uuid4(): task(summary, rest),
    }
    assert summary_progress(tasks, [summary])[summary].value == D(shown)


@pytest.mark.requirement("WF-IND-0060-A")
def test_only_the_summaries_asked_are_answered() -> None:
    # The leaves and a summary not asked are left out: the planning asks for those it gives.
    asked, other = uuid4(), uuid4()
    leaf = uuid4()
    tasks = {
        asked: task(None, "0"),
        other: task(asked, "0"),
        leaf: task(other, "50.00", completed=True),
    }
    assert summary_progress(tasks, [asked]) == {asked: Computable.of(D("1.0000"))}
