# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value on given lines and dates (US-1520), pure, then through the service.

The pure part gives the lines of the reference; their tasks run on a calendar of eight hours from
Monday to Friday. In 2026, March and April hold 22 working days each. The service part reads the
reference of a project made through the API (``workload_support``): ``planned_value`` of the
interface of the estimate.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from workload_support import NOVEMBER, Site, make_site

from waterfall.core.estimate.spreading import Placement, PlannedLine, planned_value
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import WorkInstant, weekly_calendar
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

EIGHT = Decimal(8)
ZERO = Decimal(0)
EIGHT_HOURS = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))


def line(amount: int, start: date, finish: date) -> PlannedLine:
    """Return a line of a task from the first hour of its first day to the end of its last."""
    return PlannedLine(
        Decimal(amount), Placement(EIGHT_HOURS, WorkInstant(start), WorkInstant(finish, EIGHT))
    )


TWO_MONTHS = line(1000, date(2026, 3, 1), date(2026, 4, 30))


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_task_of_two_equal_months_counts_for_half_at_the_end_of_the_first() -> None:
    # « Une ligne portée par une tâche de deux mois comptant autant d’heures travaillées
    # contribue pour moitié à la fin du premier mois. »
    assert planned_value([TWO_MONTHS], date(2026, 3, 31)) == Decimal(500)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_grows_with_the_hours_worked_and_stops_at_the_amount() -> None:
    # The amount is spread over the task in proportion to the hours worked (body).
    week_one = date(2026, 3, 6)
    values = [
        planned_value([TWO_MONTHS], at) for at in (date(2026, 2, 28), week_one, date(2026, 4, 30))
    ]
    assert values == [Decimal(0), Decimal("113.64"), Decimal(1000)]
    assert planned_value([TWO_MONTHS], date(2030, 1, 1)) == Decimal(1000)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_line_of_a_milestone_counts_whole_on_its_date_and_not_before() -> None:
    # A line of a milestone is counted whole on the date of the milestone (body of the requirement).
    milestone = WorkInstant(date(2026, 3, 20))
    lines = [PlannedLine(Decimal(300), Placement(EIGHT_HOURS, milestone, milestone))]
    assert planned_value(lines, date(2026, 3, 19)) == Decimal(0)
    assert planned_value(lines, date(2026, 3, 20)) == Decimal(300)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_lines_add_up_and_the_sum_is_rounded_once_to_the_cent() -> None:
    # The planned value totals the budget exactly at the end (reason of the requirement).
    lines = [line(1, date(2026, 3, 2), date(2026, 3, 6))] * 3
    assert planned_value(lines, date(2026, 3, 4)) == Decimal("1.80")
    assert planned_value(
        [line(10, date(2026, 3, 2), date(2026, 3, 4))] * 3, date(2026, 3, 2)
    ) == Decimal(10)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_delaying_a_task_of_the_current_revision_leaves_the_planned_value_of_the_reference() -> (
    None
):
    # « Retarder une tâche dans la révision courante ne change pas la valeur planifiée. »
    # Here the reference is given to the function, so that the delay of the other revision cannot
    # reach it; the criterion closes fully with US-1520/L2, which chooses the lines, on
    # ``planned_value`` of the interface of ``estimate`` (the reference revision, not the current).
    reference = [line(400, date(2026, 3, 2), date(2026, 3, 13))]
    delayed = line(400, date(2026, 3, 30), date(2026, 4, 10))
    before = planned_value(reference, date(2026, 3, 13))
    assert planned_value([delayed], date(2026, 3, 13)) == Decimal(0)
    assert planned_value(reference, date(2026, 3, 13)) == before == Decimal(400)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_without_lines_the_planned_value_is_nil() -> None:
    assert planned_value([], date(2026, 3, 13)) == Decimal(0)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_sum_is_rounded_once_from_the_exact_total_not_from_a_quotient() -> None:
    # Just under a cent and a half, past the 28 digits of a quotient: rounded in two steps it would
    # reach 0.015 and then the even 0.02; rounded once it is 0.01.
    just_under = Decimal("0.014999999999999999999999999999999")
    day = WorkInstant(date(2026, 3, 2))
    lines = [PlannedLine(just_under, Placement(EIGHT_HOURS, day, day))]
    assert planned_value(lines, date(2026, 3, 2)) == Decimal("0.01")
    third = [line(1, date(2026, 3, 2), date(2026, 3, 4))] * 3
    assert planned_value(third, date(2026, 3, 2)) == Decimal(1)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_task_over_a_weekend_counts_whole_at_its_end_not_at_its_start() -> None:
    # The choice (the design is silent): no hour worked, the line counts whole at the end.
    weekend = PlannedLine(
        Decimal(80),
        Placement(EIGHT_HOURS, WorkInstant(date(2026, 3, 7)), WorkInstant(date(2026, 3, 9))),
    )
    assert planned_value([weekend], date(2026, 3, 7)) == Decimal(0)
    assert planned_value([weekend], date(2026, 3, 9)) == Decimal(80)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_keeps_the_two_decimals_of_the_cent() -> None:
    """The value serialises with its cents: ``80.00``, ``1.80`` and ``0.00``, not ``80``."""
    weekend = line(80, date(2026, 3, 7), date(2026, 3, 8))
    assert str(planned_value([weekend], date(2026, 3, 9))) == "80.00"
    assert str(planned_value([TWO_MONTHS], date(2026, 3, 31))) == "500.00"
    assert str(planned_value([], date(2026, 3, 13))) == "0.00"


# --- Through the service -------------------------------------------------------------------------


@pytest.fixture
def site(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Site:
    """Give a platform, a project its manager made, its revision opened, and a role to load."""
    return make_site(api, owner, database, realm)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_of_a_budget_of_1000_is_nought_before_and_1000_at_the_end(
    site: Site,
) -> None:
    # « Sur un projet dont le budget de référence est de 1 000, la valeur planifiée vaut 1 000 à la
    # date de fin de la dernière tâche de la référence, et 0 avant le début de la première. »
    site.material(site.task("Câblage", NOVEMBER), "600")
    site.material(site.task("Essais", ("2026-12-01", "2026-12-31")), "400")
    site.referenced()
    assert site.value(date(2026, 11, 1)) == Decimal(0)
    assert site.value(date(2026, 12, 31)) == Decimal(1000)
    assert site.value(date(2031, 1, 1)) == Decimal(1000)
    assert site.value(date(2026, 11, 30)) == Decimal(600)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_line_of_a_task_of_two_months_worth_as_much_counts_for_half_at_the_end_of_the_first(
    site: Site,
) -> None:
    # « Une ligne portée par une tâche de deux mois comptant autant d’heures travaillées
    # contribue pour moitié à la fin du premier mois. » (March and April 2026: 22 days each.)
    site.material(site.task("Câblage", ("2026-03-02", "2026-04-30")), "1000")
    site.referenced()
    assert site.value(date(2026, 3, 31)) == Decimal(500)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_provision_is_not_part_of_the_planned_value(site: Site) -> None:
    # « calculée sur les lignes de la révision de référence hors provision » (corps du critère).
    task = site.task("Câblage", NOVEMBER)
    site.material(task, "600")
    provision = site.material(task, "250")
    with site.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(provision))
            .values(cost_category_id=site.costs.provision)
        )
    site.referenced()
    assert site.value(date(2026, 11, 30)) == Decimal(600)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_delaying_a_task_of_the_current_revision_leaves_the_reference_planned_value_in_the_service(
    site: Site,
) -> None:
    # « Retarder une tâche dans la révision courante ne change pas la valeur planifiée. »
    site.material(site.task("Câblage", NOVEMBER), "800")
    current = site.referenced()
    days = (date(2026, 11, 6), date(2026, 11, 20), date(2026, 11, 30))
    before = [site.value(day) for day in days]
    task = next(each for each in current.items() if each["kind"] == "task")
    delay = {"start": {"date": "2027-03-01"}, "finish": {"date": "2027-03-31"}}
    current.changed(task, scheduling_mode="manual", **delay)
    moved = next(each for each in current.items() if each["kind"] == "task")
    assert moved["task"]["start"]["date"] == "2027-03-01"
    assert [site.value(day) for day in days] == before
    assert before[-1] == Decimal(800)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_line_of_a_milestone_counts_whole_on_its_date_and_not_the_day_before(site: Site) -> None:
    # « calculée sur les lignes de la révision de référence » : a line borne by a milestone is
    # counted whole on the date of the milestone, nothing the day before.
    milestone = site.tree.made("Réception", task={"duration": {"value": "0", "unit": "d"}})
    day = date.fromisoformat(milestone["task"]["start"]["date"])
    assert milestone["task"]["is_milestone"] is True
    site.lines.made(
        milestone, quantity="1", cost_category_id=str(site.costs.material), unit_disbursement="700"
    )
    site.referenced()
    assert site.value(day - timedelta(days=1)) == Decimal(0)
    assert site.value(day) == Decimal(700)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_revision_that_is_not_the_reference_of_the_project_is_refused(site: Site) -> None:
    # « valeur planifiée … sur la révision de référence » : the revision in progress, or one the
    # project does not know, is not the baseline; its value is refused, not silently computed.
    site.material(site.task("Câblage", NOVEMBER), "600")
    current = site.referenced()
    for revision in (current.revision["revision_id"], str(uuid4())):
        with pytest.raises(UnprocessableError) as refused:
            site.value(date(2026, 11, 30), UUID(revision))
        assert refused.value.code == "VALIDATION_FAILED"
        assert [each.pointer for each in refused.value.fields] == ["/reference"]
    assert site.value(date(2026, 11, 30)) == Decimal(600)
