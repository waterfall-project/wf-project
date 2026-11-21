# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rules of the four signals of the health of the control, without a database (US-2750).

The interval a project's risks and costs are judged over, the weeks of a late review, the milestones
overdue and the zone of a signal: pure functions of what the view read (WF-PTF-0110, WF-REF-0180).
"""

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from waterfall.core.portfolio.signalling import (
    ReviewInterval,
    overdue_milestones,
    review_interval,
    signal,
    weeks_overdue,
)

FIRST, SECOND, THIRD = UUID(int=1), UUID(int=2), UUID(int=3)
JANUARY, MARCH, MAY = (datetime(2026, month, 2, 9, tzinfo=UTC) for month in (1, 3, 5))
ENTERED = datetime(2026, 1, 19, 9, tzinfo=UTC)


@pytest.mark.requirement("WF-PTF-0110-A")
def test_the_interval_runs_from_the_marking_before_the_last_to_the_last_marking() -> None:
    # « …entre l'avant-dernière et la dernière révision marquée »
    markings = [(FIRST, JANUARY), (SECOND, MARCH), (THIRD, MAY)]
    assert review_interval(markings, MAY, ENTERED) == ReviewInterval(THIRD, MARCH, MAY)


@pytest.mark.requirement("WF-PTF-0110-A")
def test_without_a_marking_before_the_last_the_interval_starts_at_the_passage_in_progress() -> None:
    # « …ou, à défaut d'avant-dernière, depuis le passage à En cours »
    assert review_interval([(FIRST, MARCH)], MARCH, ENTERED) == ReviewInterval(
        FIRST, ENTERED, MARCH
    )


@pytest.mark.story("US-2750")
def test_a_marking_after_the_date_of_calculation_is_not_read() -> None:
    # À une date passée : the last marking is that by the end of the day, the later ones are not
    # the project's last, nor its penultimate.
    markings = [(FIRST, JANUARY), (SECOND, MARCH), (THIRD, MAY)]
    assert review_interval(markings, MARCH, ENTERED) == ReviewInterval(SECOND, ENTERED, MARCH)


@pytest.mark.story("US-2750")
def test_a_project_with_no_marking_or_no_passage_in_progress_has_no_interval() -> None:
    # No last marking to judge: none by the date, or a single one and no known passage.
    assert review_interval([], None, ENTERED) is None
    assert review_interval([(FIRST, MAY)], JANUARY, ENTERED) is None
    assert review_interval([(FIRST, JANUARY)], JANUARY, None) is None


@pytest.mark.requirement("WF-PTF-0110-A")
def test_a_marking_at_or_before_the_passage_in_progress_is_the_reference_not_a_review() -> None:
    # « …ou, à défaut d'avant-dernière, depuis le passage à En cours » : the last marking at the
    # very instant of the passage, or before it, is the reference the passage designates, no
    # review; no interval (``docs/api/DECISIONS.md``, #4333). One an instant after is a review.
    assert review_interval([(FIRST, ENTERED)], ENTERED, ENTERED) is None
    assert review_interval([(FIRST, JANUARY)], JANUARY, ENTERED) is None
    later = ENTERED.replace(minute=1)
    assert review_interval([(FIRST, later)], later, ENTERED) == ReviewInterval(
        FIRST, ENTERED, later
    )


@pytest.mark.requirement("WF-REF-0180-A")
def test_a_review_is_late_beyond_the_delay_in_days_and_gives_its_whole_weeks() -> None:
    # « Un projet dont la dernière révision marquée date de plus que ce délai est signalé » : six
    # weeks are 42 days, the 43rd is late, and the weeks are those elapsed.
    marked = datetime(2026, 3, 2, 23, 30, tzinfo=UTC)
    assert weeks_overdue(marked, date(2026, 4, 13), 6) is None
    assert weeks_overdue(marked, date(2026, 4, 14), 6) == 6
    assert weeks_overdue(marked, date(2026, 6, 3), 6) == 13
    assert weeks_overdue(marked, date(2026, 6, 3), 14) is None


@pytest.mark.requirement("WF-PTF-0110-A")
def test_a_milestone_is_overdue_when_its_date_is_passed_and_it_is_not_completed() -> None:
    # « …dont la date de référence est dépassée sans qu'ils soient terminés »
    document = {
        "milestones": [
            {"lineage_id": "a", "label": "A", "reference_date": "2026-05-01", "completed_on": None},
            {"lineage_id": "b", "label": "B", "reference_date": "2026-05-01", "completed_on": "d"},
            {"lineage_id": "c", "label": "C", "reference_date": "2026-06-03", "completed_on": None},
            {"lineage_id": "d", "label": "D", "reference_date": None, "completed_on": None},
        ]
    }
    assert overdue_milestones(document, date(2026, 6, 3)) == [
        {"lineage_id": "a", "milestone_label": "A", "reference_date": "2026-05-01"}
    ]
    assert overdue_milestones(None, date(2026, 6, 3)) == []


@pytest.mark.requirement("WF-PTF-0110-A")
def test_the_milestone_signal_is_in_alert_and_the_three_others_in_watch() -> None:
    # Propre à l'US : the zone follows the code.
    zones = {
        code: signal(FIRST, "Projet", can_open=True, code=code)["zone"]
        for code in (
            "review_overdue",
            "risks_not_reviewed",
            "no_actual_cost_since_last_review",
            "contractual_milestone_overdue",
        )
    }
    assert zones == {
        "review_overdue": "watch",
        "risks_not_reviewed": "watch",
        "no_actual_cost_since_last_review": "watch",
        "contractual_milestone_overdue": "alert",
    }
    assert "params" not in signal(FIRST, "Projet", can_open=False, code="risks_not_reviewed")
