# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The history of PRJ-001 in the reference set, and its check (US-2950/L2; WF-QUA-0040-A).

The plan of the history first, without a base: the months, their names, the lines they import, read
in the witness. Then the command, on a copy of the witness, on a history of a few months — a month
marks a revision of a thousand tasks and takes seconds, the full history, a hundred and
seventy-eight
months, most of an hour: its volumes are those of ``make service-reference-check``, which counts
them on the platform that holds the set (the guide, "Le jeu de données de référence") — : one step
is one transaction, a command stopped between two steps is taken up at the next, and the check finds
the volumes, the identifiers and the sums of the portfolio on the platform it reads, and the faults
on one that lacks a part.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select
from support import WITNESS
from test_witness_reference import count, identifying, settings
from witness_template import TEMPLATE, cloned

from waterfall.core.costs.tables import CostLine
from waterfall.core.revisions.interface import current_revision, marked_revisions
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.witness import reference_check, reference_history, reference_load
from waterfall.witness.description import Witness
from waterfall.witness.main import main
from waterfall.witness.reference_history import (
    COST_LINES,
    MARKED,
    History,
    HistoryError,
    Plan,
    name_of,
    review_of,
    revision_id_of,
)
from waterfall.witness.reference_projects import numbers_of

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from support import Logs

REQUIREMENT = "WF-QUA-0040-A"
STORY = "US-2950"
# The witness's last event is on 2026-06-03: the history starts the month after.
WITNESS_LAST_EVENT = datetime(2026, 6, 3, 9, 0, tzinfo=UTC)
# The projects of the portfolio the command is tried with, the witness's alone: the history is
# the object of these tests, the projects drawn are those of ``test_witness_reference``.
WITNESS_PORTFOLIO = 8
NONE = History(0, 0)


def described() -> Witness:
    return Witness(WITNESS, Act(None, utc_now()))


def short(months: int, lines: int) -> History:
    """Give a history of ``months`` more than the witness holds of PRJ-001, ``lines`` more."""
    plan = Plan.read(described(), History())
    return History(plan.marked + months, COST_LINES - plan.added + lines)


@pytest.mark.requirement(REQUIREMENT)
def test_the_history_of_prj_001_reaches_the_volumes_of_a_hundred_and_eighty_revisions() -> None:
    # « … un projet portant mille tâches, quinze ans de révisions mensuelles marquées et dix-huit
    # mille lignes de coût » : the plan, read in the witness, writes the months that bring PRJ-001
    # to the volumes of §4.6.2, each month a revision marked, each with its import.
    witness = described()
    plan = Plan.read(witness, History())
    assert (MARKED, COST_LINES) == (180, 18_000)
    assert plan.marked + plan.steps == MARKED
    held = COST_LINES - plan.added
    assert 0 < held < 100  # the lines of the witness, which the history completes
    months = [review_of(step) for step in range(1, plan.steps + 1)]
    assert months[0] > WITNESS_LAST_EVENT
    assert months == sorted(months)
    # One review a month, on a Monday, from the month after the witness's: fifteen years of them.
    assert len({(each.year, each.month) for each in months}) == plan.steps
    assert all(each.weekday() == 0 and each.day <= 7 for each in months)
    assert (months[-1].year - months[0].year) * 12 + months[-1].month - months[0].month == (
        plan.steps - 1
    )
    assert 14 <= (months[-1] - datetime(2026, 3, 1, tzinfo=UTC)).days / 365.25 <= 16
    assert sum(plan.lines_of(step) for step in range(1, plan.steps + 1)) == plan.added
    assert {plan.lines_of(step) for step in range(1, plan.steps + 1)} <= {100, 101}
    names = [name_of(step) for step in range(1, plan.steps + 1)]
    assert len(set(names)) == plan.steps  # a name of version is unique among a project's marked
    assert names[0] == "Revue de juillet 2026"
    assert len({revision_id_of(step) for step in range(1, plan.steps + 1)}) == plan.steps


@pytest.mark.requirement(REQUIREMENT)
def test_a_history_that_asks_lines_and_no_revision_to_mark_them_with_is_refused() -> None:
    # The lines of a month come with its marking: lines asked beyond the witness's, no month.
    with pytest.raises(HistoryError):
        Plan.read(described(), History(marked=2, cost_lines=COST_LINES))
    nothing = Plan.read(described(), NONE)
    assert (nothing.steps, nothing.added) == (0, 0)


@pytest.mark.requirement(REQUIREMENT)
def test_two_draws_of_a_month_of_the_history_give_the_same_lines_and_none_repeats_another() -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. » : the lines of
    # a month are drawn from the seed and its number alone, and identify themselves.
    plan = Plan.read(described(), History())
    first = reference_history.month_lines(plan, 7, review_of(7))
    again = reference_history.month_lines(plan, 7, review_of(7))
    other = reference_history.month_lines(plan, 8, review_of(8))
    assert first == again
    assert {each.cost_line_id for each in first}.isdisjoint(each.cost_line_id for each in other)
    assert {(each.document_number, each.document_item) for each in first}.isdisjoint(
        (each.document_number, each.document_item) for each in other
    )
    assert all(each.amount > 0 and each.subproject_code is None for each in first)


def marked_of(database: Database) -> list[str]:
    """Give the names of the revisions of the history the platform holds, in the order marked."""
    with database.transaction() as session:
        names = session.scalars(
            select(Revision.version_name)
            .where(Revision.version_name.like("Revue de % 20__"))
            .order_by(Revision.marked_at)
        )
        return [each for each in names if each is not None]


@pytest.mark.requirement(REQUIREMENT)
def test_the_history_marks_each_month_and_opens_the_next_by_the_rules_and_the_check_finds_the_set(
    witness: Database, service_database_url: str, logs: Logs
) -> None:
    # « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes annoncés. » :
    # on a history of three months, the command goes through the interfaces of the modules — the
    # rules of the marking and of the opening accept each month —, and the check counts what the
    # seed and the witness announce: the projects, the marked revisions, the lines of cost, the
    # identifiers, and the sums of the portfolio.
    history = short(3, 250)
    assert reference_load.load_reference(settings(service_database_url), 8, history) == 0
    assert marked_of(witness) == [name_of(1), name_of(2), name_of(3)]
    assert [record["step"] for record in logs.named("reference.history_step")] == [1, 2, 3]
    assert [record["history"] for record in logs.named("reference.loaded")] == [3]
    plan = Plan.read(described(), history)
    assert (plan.steps, plan.added) == (3, 250)
    with witness.transaction() as session:
        # The month that ends opens the next: PRJ-001 holds one revision in progress.
        assert current_revision(session, plan.project_id) == revision_id_of(3)
        assert len(marked_revisions(session, plan.project_id)) == plan.marked + 3
        lines = session.scalar(select(func.count()).select_from(CostLine))
    assert lines is not None
    with witness.transaction() as session:
        report = reference_check.check(session, described(), 8, history)
    assert report.faults == []
    assert report.held == report.expected
    assert report.held.cost_lines == lines
    # The sums of a portfolio are those of its projects: the budgets summed are not an empty sum.
    assert report.compared > 0
    # What a platform lacks of the history it is asked, the check names, and the command says so.
    asked = History(history.marked + 2, history.cost_lines + 40)
    with witness.transaction() as session:
        lacking = reference_check.check(session, described(), 8, asked)
    assert [each.split(":")[0] for each in lacking.faults][:2] == ["marked_revisions", "cost_lines"]
    assert sorted(each for each in lacking.faults if "of the history: absent" in each) == sorted(
        f"revision {revision_id_of(step)} of the history: absent" for step in (4, 5)
    )


@pytest.mark.requirement(REQUIREMENT)
@pytest.mark.usefixtures("witness")
def test_the_command_checks_the_set_and_ends_one_on_a_fault_two_on_a_setting_that_lacks(
    service_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The reference loaded, PRJ-001 as the witness leaves it: the check finds the set whole, and
    # ends zero, naming the volumes it counted.
    assert reference_load.load_reference(settings(service_database_url), 8, NONE) == 0
    monkeypatch.setenv("WATERFALL_DATABASE_URL", service_database_url)
    monkeypatch.setenv("WATERFALL_WITNESS_PATH", str(WITNESS))
    assert (
        main(["check-reference", "--projects", "8", "--revisions", "0", "--cost-lines", "0"]) == 0
    )
    said = capsys.readouterr().out
    assert "projects: 12 (expected 12)" in said
    assert "order book: the budgets of" in said
    assert "fault:" not in said
    # Asked more than it holds — four projects, a history — it ends one and says what lacks.
    assert (
        main(["check-reference", "--projects", "12", "--revisions", "4", "--cost-lines", "0"]) == 1
    )
    said = capsys.readouterr().out
    assert f"fault: projects: 12 held, {12 + len(numbers_of(4))} expected" in said
    assert "fault: marked_revisions:" in said
    assert "of the history: absent" in said
    # Lines asked and no month to import them in: refused before anything is read (2).
    assert main(["check-reference", "--revisions", "0", "--cost-lines", "1000000"]) == 2
    assert "lines of cost are asked" in capsys.readouterr().err
    monkeypatch.delenv("WATERFALL_DATABASE_URL")
    assert main(["check-reference"]) == 2


@pytest.mark.requirement(REQUIREMENT)
def test_a_history_stopped_between_two_months_is_taken_up_at_the_next_and_gives_the_same_set(
    witness: Database,
    service_database_url: str,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
    logs: Logs,
) -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. » : loaded at
    # once on one copy of the witness; on the other, stopped at its second month — the first kept,
    # its own transaction, none half written — then taken up where it stopped.
    history = short(2, 150)
    plan = Plan.read(described(), history)
    assert reference_load.load_reference(settings(service_database_url), 8, history) == 0
    first = identifying(witness)
    template = request.config.stash[TEMPLATE]
    written = reference_load.write_step

    def failing(session: Session, plan: Plan, step: int, act: Act) -> None:
        if step == 2:
            message = "the machine stopped"
            raise RuntimeError(message)
        written(session, plan, step, act)

    with cloned(template, request.getfixturevalue("process_database_url")) as url:
        other = template.as_service(url)
        monkeypatch.setattr(reference_load, "write_step", failing)
        assert reference_load.load_reference(settings(other), 8, history) == 1
        assert [record["project"] for record in logs.named("reference.failed")] == ["PRJ-001"]
        second = Database(create_database_engine(other))
        try:
            assert marked_of(second) == [name_of(1)]
            with second.transaction() as session:
                assert current_revision(session, plan.project_id) == revision_id_of(1)
            monkeypatch.setattr(reference_load, "write_step", written)
            logs.clear()
            assert reference_load.load_reference(settings(other), 8, history) == 0
            assert [each["step"] for each in logs.named("reference.history_step")] == [2]
            assert identifying(second) == first
            assert count(second, CostLine) == count(witness, CostLine)
        finally:
            second.dispose()
