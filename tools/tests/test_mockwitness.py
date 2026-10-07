# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the witness project said once, and of the hours of work of its calendars."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcore, mockwitness
from wftools.mockcalendar import (
    ORIGIN,
    START_TO_START,
    Calendar,
    Instant,
    Predecessor,
    applicable,
    follow,
    to_hours,
)
from wftools.mockwitness import PREFIX


def hours(*values: int) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


STANDARD = Calendar("standard", hours(8, 8, 8, 8, 8, 0, 0))
FOUR_DAYS = Calendar("four", hours(10, 10, 10, 10, 0, 0, 0))


def at(day: int, worked: int | str = 0) -> Instant:
    """Return an instant of June 2026."""
    return Instant(date(2026, 6, day), Decimal(worked))


def test_today_is_the_instant_every_first_example_describes() -> None:
    assert datetime(2026, 6, 3, 14, 5, tzinfo=UTC) == mockwitness.TODAY
    days = [event.on for event in mockwitness.CHRONOLOGY]
    assert days == sorted(days)
    assert days[0] == date(2025, 9, 1)
    assert days[-1] == mockwitness.TODAY.date()
    # The project is created before its offer is opened (#287, C11).
    assert mockwitness.CREATED.on < mockwitness.OFFER_OPENED.on < mockwitness.OFFER_MARKED.on


def test_the_families_of_identifiers_lie_on_disjoint_ranges() -> None:
    generated = sorted(family.generated for family in mockwitness.IDENTIFIERS if family.generated)
    assert generated == [1, 2, 3, 4, 5]
    tails = {f"{n:012d}" for n in range(1_000)} | {f"{n:012x}" for n in range(0x1000)}
    for tail in sorted(tails):
        held = [family.what for family in mockwitness.IDENTIFIERS if family.holds(PREFIX + tail)]
        assert len(held) <= 1, (tail, held)
    # A number of the other writing is not of a family, and says so without failing.
    assert not any(family.holds(f"{PREFIX}00000000052a") for family in mockwitness.IDENTIFIERS)


def test_an_identifier_belongs_to_one_family() -> None:
    node = mockwitness.universe(521)
    assert node == "01926f3a-7c00-7000-8000-000000000521"
    assert [family.what for family in mockwitness.IDENTIFIERS if family.holds(node)] == [
        "nœuds de la structure"
    ]
    drawn = mockwitness.identifier(mockwitness.NODES, 4)
    assert drawn == "01926f3a-7c00-7000-8000-000100000004"
    assert [family.what for family in mockwitness.IDENTIFIERS if family.holds(drawn)] == [
        "nœuds engendrés"
    ]
    assert not any(family.holds("an identifier") for family in mockwitness.IDENTIFIERS)


def _core(task: mockwitness.Task) -> list[mockwitness.Task | mockwitness.Line]:
    return [task, *task.lines, *(each for child in task.children for each in _core(child))]


def test_the_core_has_one_identifier_a_node_and_its_lineage_apart() -> None:
    numbers = [each.number for root in mockwitness.CORE for each in _core(root)]
    assert len(numbers) == len(set(numbers)) == 24
    nodes = next(family for family in mockwitness.IDENTIFIERS if family.what.startswith("nœuds de"))
    lineages = next(family for family in mockwitness.IDENTIFIERS if family.first == 600)
    assert all(nodes.holds(mockwitness.universe(number)) for number in numbers)
    assert all(lineages.holds(mockwitness.universe(number + 100)) for number in numbers)


def test_the_witness_employs_three_active_roles_on_two_calendars() -> None:
    roles = {role["resource_role_id"]: role for role in mockwitness.fixture("resource_roles")}
    fitter = roles[mockwitness.CABLE_FITTER]
    assert (fitter["label"], fitter["is_active"]) == ("Monteur câbleur", True)
    assert fitter["cost_category_id"] == mockwitness.ELECTRICAL_ENGINEERING
    calendars = mockwitness.role_calendars()
    assert {role: calendar.calendar_id for role, calendar in calendars.items()} == {
        mockwitness.ENGINEER: mockwitness.STANDARD_WEEK,
        mockwitness.COMMISSIONING_TECHNICIAN: mockwitness.STANDARD_WEEK,
        mockwitness.CABLE_FITTER: mockwitness.FOUR_DAY_WEEK,
    }
    assert calendars[mockwitness.CABLE_FITTER].week == FOUR_DAYS.week
    assert mockwitness.default_calendar().week == STANDARD.week


@pytest.mark.parametrize(
    ("instant", "count"),
    [
        (Instant(ORIGIN), 0),
        (at(1), 8 * 5 * 21),
        (at(1, 3), 8 * 5 * 21 + 3),
        # Hours past those of the day count as its end; a Saturday, as the Friday before it.
        (at(1, 12), 8 * 5 * 21 + 8),
        (at(6, 4), 8 * 5 * 22),
        (Instant(date(2026, 1, 2), Decimal(8)), 0),
    ],
)
def test_an_instant_counts_its_hours_of_work_from_a_monday(instant: Instant, count: int) -> None:
    assert STANDARD.elapsed(instant) == count


def test_a_count_on_a_day_boundary_is_a_finish_or_a_start() -> None:
    friday_end = STANDARD.elapsed(at(5, 8))
    assert STANDARD.instant(friday_end, finish=True) == at(5, 8)
    assert STANDARD.instant(friday_end, finish=False) == at(8)
    # Before the Monday hours are counted from, a count falls in its own week.
    assert STANDARD.instant(Decimal(-16), finish=False) == Instant(date(2026, 1, 1))
    assert STANDARD.instant(Decimal(-8), finish=True) == Instant(date(2026, 1, 1), Decimal(8))


def test_a_duration_is_placed_hour_after_hour_on_its_calendar() -> None:
    # Five days of eight hours: a week of the standard calendar, four days of ten hours.
    forty = Decimal(40)
    assert STANDARD.finish_after(at(1), forty) == at(5, 8)
    assert FOUR_DAYS.finish_after(at(1), forty) == at(4, 10)
    assert FOUR_DAYS.finish_after(at(4, 6), Decimal(8)) == at(8, 4)
    assert FOUR_DAYS.start_at(at(5)) == at(8)
    assert FOUR_DAYS.start_before(at(8, 4), Decimal(8)) == at(4, 6)
    assert FOUR_DAYS.work_between(at(4, 6), at(8, 4)) == 8


def test_the_calendar_of_a_task_grants_each_day_the_fewest_hours_of_its_roles() -> None:
    # WF-PLA-0010: the standard week and the week of four days of ten hours leave four days of
    # eight hours; one calendar is itself, none the default.
    both = applicable([STANDARD, FOUR_DAYS, STANDARD], STANDARD)
    assert both.week == hours(8, 8, 8, 8, 0, 0, 0)
    assert applicable([FOUR_DAYS, FOUR_DAYS], STANDARD) is FOUR_DAYS
    assert applicable([], STANDARD) is STANDARD


def test_a_duration_or_a_lag_of_work_is_converted_into_hours() -> None:
    # WF-PLA-0160: by the installation's constants, 8 hours a day, 40 a week, 20 days a month.
    assert to_hours(2, "d") == 16
    assert to_hours(-2, "d") == -16
    assert to_hours(1, "w") == 40
    assert to_hours(1, "mo") == 160
    assert to_hours(30, "min") == Decimal("0.5")
    with pytest.raises(ValueError, match="ed is not a unit of work"):
        to_hours(1, "ed")


@pytest.mark.parametrize("start", [at(1), at(4, 10), at(5, 8), at(6), at(8, 3)])
@pytest.mark.parametrize("worked", ["0", "0.5", "8", "10", "40"])
def test_a_task_never_finishes_before_it_starts(start: Instant, worked: str) -> None:
    for calendar in (STANDARD, FOUR_DAYS):
        duration = Decimal(worked)
        assert calendar.elapsed(calendar.finish_after(start, duration)) >= calendar.elapsed(start)
        assert calendar.elapsed(calendar.start_before(start, duration)) <= calendar.elapsed(start)


def test_a_milestone_sits_where_its_predecessor_finishes() -> None:
    # A task finished on the Friday at 8 hours: a milestone it leads to starts and finishes
    # there, not on the Monday after (WF-PLA-0050); a task, on the Monday at the first hour.
    friday = Predecessor(at(1), at(5, 8))
    assert follow(STANDARD, [friday], Decimal(0), at(1)) == (at(5, 8), at(5, 8))
    assert follow(STANDARD, [friday], Decimal(8), at(1)) == (at(8), at(8, 8))
    # Backwards on a day boundary, a start is the first hour of the next working day.
    assert STANDARD.start_before(at(8, 8), Decimal(8)) == at(8)
    assert FOUR_DAYS.start_before(at(4, 10), Decimal(40)) == at(1)


def test_a_start_to_start_lag_is_placed_on_the_successor_calendar() -> None:
    # A week of lag is forty hours: on the week of four days of ten hours, from Monday to
    # Thursday, so that the successor starts the next Monday (WF-PLA-0010).
    monday = Predecessor(at(1), at(5, 8), START_TO_START, to_hours(1, "w"))
    start, finish = follow(FOUR_DAYS, [monday], to_hours(1, "d"), at(1))
    assert (start, finish) == (at(8), at(8, 8))
    assert FOUR_DAYS.work_between(at(1), start) == 40


def test_a_calendar_skips_the_days_it_does_not_work() -> None:
    from_tuesday = Calendar("from-tuesday", hours(0, 8, 8, 8, 8, 0, 0))
    assert from_tuesday.instant(Decimal(0), finish=False) == Instant(date(2026, 1, 6))
    assert from_tuesday.instant(Decimal(8), finish=True) == Instant(date(2026, 1, 6), Decimal(8))
    assert from_tuesday.instant(Decimal(32), finish=False) == Instant(date(2026, 1, 13))


def test_a_calendar_without_any_hour_cannot_date_a_task() -> None:
    weekend = Calendar("weekend", hours(0, 0, 0, 0, 0, 8, 8))
    none = applicable([STANDARD, weekend], STANDARD)
    with pytest.raises(ValueError, match="standard∩weekend grants no hour"):
        none.finish_after(at(1), Decimal(8))


def _dates() -> dict[int, tuple[Instant, Instant]]:
    """Date the tasks of the core from their links alone, by number of task."""
    return {number: (each.start, each.finish) for number, each in mockcore.schedule().items()}


def _on(month: int, day: int, worked: int = 0) -> Instant:
    return Instant(date(2026, month, day), Decimal(worked))


def test_the_core_is_dated_by_its_links() -> None:
    dates = _dates()
    assert dates[522] == (_on(3, 2), _on(4, 10, 8))
    assert dates[524] == (_on(4, 13), _on(4, 24, 8))
    assert dates[525] == (_on(4, 24, 8), _on(4, 24, 8))
    # Two days of lead from the finish of the detailed studies, on the Friday at 8 hours.
    assert dates[526] == (_on(4, 9), _on(4, 15, 8))
    # A week after the reception of the studies; the factory acceptance at the end of the wiring.
    assert dates[552] == (_on(5, 4), _on(6, 30, 8))
    assert dates[542] == (_on(5, 4), _on(5, 8, 8))
    assert dates[544] == (_on(5, 11), _on(5, 15, 8))
    assert dates[556] == (_on(6, 30, 8), _on(6, 30, 8))


def test_the_figures_of_the_core_are_those_of_the_other_examples() -> None:
    risks = {risk["risk_id"]: risk for risk in mockwitness.fixture("risks")["items"]}
    delay, rework = risks[mockwitness.universe(752)], risks[mockwitness.universe(751)]
    lines = {
        line.number: line
        for root in mockwitness.CORE
        for task in _core(root)
        if isinstance(task, mockwitness.Task)
        for line in task.lines
    }
    # The lines merged by the occurrence of 752 are budgeted nothing — the occurrence does not
    # move the reference (WF-RIS-0060) —, and reestimated at their own estimate, 200 in all;
    # the occurrence merged into the current revision, opened on 2 February, before the studies.
    merged = [lines[543], lines[545]]
    assert [line.budgeted for line in merged] == [Decimal(0), Decimal(0)]
    assert sum(line.unit or 0 for line in merged) == Decimal(delay["severity"])
    assert mockwitness.RISK_751_REVIEWED.on < mockwitness.RISK_752_OCCURRED.on
    assert mockwitness.RISK_752_OCCURRED.on < mockwitness.STUDIES_STARTED.on
    # The provision of 751, its severity at its probability; the wiring at the rate of 2026.
    assert lines[555].unit == Decimal(rework["severity"]) * Decimal(rework["probability"])
    rates = mockwitness.fixture("volume/hourly_rates")
    [rate] = [entry for entry in rates if entry["year"] == 2026]
    assert (lines[553].hours or 0) * Decimal(rate["amount"]) == Decimal("1000.00")


_STRUCTURE = ("nœuds de la structure", "nœuds engendrés")
_KEYS = {
    "node_id": _STRUCTURE,
    "predecessor_node_id": _STRUCTURE,
    "provision_node_id": _STRUCTURE,
    "parent_id": (*_STRUCTURE, "nœuds d'organisation"),
    "lineage_id": ("lignées, celle du nœud 5nn en 6nn", "lignées engendrées"),
    "project_id": ("projets", "projets du portefeuille"),
    "revision_id": ("révisions",),
    "current_revision_id": ("révisions",),
    "reference_revision_id": ("révisions",),
    "from_revision_id": ("révisions",),
    "to_revision_id": ("révisions",),
    "structure_id": ("structures",),
    "user_id": ("comptes",),
    "cost_category_id": ("catégories de coût", "catégories de la grille des taux"),
    "resource_role_id": ("rôles de ressources",),
    "cost_type_id": ("natures de coût",),
    "org_node_id": ("nœuds d'organisation",),
    "calendar_id": ("calendriers",),
    "access_role_id": ("rôles d'habilitation",),
    "access_role_ids": ("rôles d'habilitation",),
    "risk_id": ("risques", "risques du portefeuille"),
    "subproject_id": ("sous-projets",),
    "order_item_id": ("postes et lots du lotissement",),
    "attached_node_id": _STRUCTURE,
    "order_item_node_id": _STRUCTURE,
    "work_package_node_ids": _STRUCTURE,
    "work_package_id": ("postes et lots du lotissement",),
    "scope": ("sous-projets",),
    "key": (
        "natures de coût",
        "sous-projets",
        "postes et lots du lotissement",
        "nœuds d'organisation",
    ),
    "backup_id": ("sauvegardes",),
    "task_id": ("tâches de fond",),
    "paste_id": ("collages et corrélations",),
    "correlation_id": ("collages et corrélations",),
    "upload_id": ("imports et téléversements",),
    "import_id": ("imports et téléversements",),
    "timeline_id": ("chronologies",),
    "cost_line_id": ("lignes de coût réel",),
    "cost_import_id": ("imports de coûts réels",),
}
"""The families an identifier may be of, by the key that carries it."""

_TRESPASSES = {
    *(("task_id", f"00000000090{n}") for n in range(1, 6)),
    ("paste_id", "000000000911"),
    ("paste_id", "000000000912"),
    ("correlation_id", "000000000913"),
    *(("correlation_id", f"00000000092{n}") for n in range(1, 8)),
}
"""The identifiers written by hand off the range of their family (#287, C16): a list that only
shrinks, as their examples are moved onto it."""


def _identifiers(value: Any, key: str = "") -> list[tuple[str, str]]:
    """Return each identifier of a value read from JSON, with the key that carries it."""
    if isinstance(value, str):
        return [(key, value)] if value.startswith(PREFIX) else []
    if isinstance(value, list):
        items = cast("list[Any]", value)
        return [found for item in items for found in _identifiers(item, key)]
    if isinstance(value, dict):
        fields = cast("dict[str, Any]", value)
        return [found for name, item in fields.items() for found in _identifiers(item, name)]
    return []


def test_each_identifier_of_the_examples_is_of_the_family_its_key_names() -> None:
    families = {family.what: family for family in mockwitness.IDENTIFIERS}
    trespasses: set[tuple[str, str]] = set()
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        example = json.loads(path.read_text(encoding="utf-8"))
        for key, value in _identifiers(example["value"]):
            assert key in _KEYS, f"{path.name}: {key} names no family"
            if not any(families[name].holds(value) for name in _KEYS[key]):
                trespasses.add((key, value.removeprefix(PREFIX)))
    assert trespasses == _TRESPASSES
