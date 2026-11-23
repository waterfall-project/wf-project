# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The backward pass of the engine on structures drawn at random, and its count of bounds.

US-3300/L2, without a database. Structures without a manual task, drawn by a generator of fixed
seed written here — the back has no library of property tests, and receives none for one test —,
render no negative float and no conflict, and their finish is the latest finish of one task at
least (#3335, #4412). A link between summaries is bounded once, not once per pair of their
subordinates: the engine's count of bounds, not a clock, says so (#4414).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import pytest

from waterfall.core.planning.scheduling import (
    Calendar,
    Duration,
    DurationUnit,
    Lag,
    LagUnit,
    Link,
    LinkType,
    SchedulingRefusalError,
    Structure,
    Task,
    UnitConstants,
    counted_bounds,
    schedule,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

MONDAY = date(2026, 3, 2)
CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))
EIGHT, FOUR, NONE = Decimal(8), Decimal(4), Decimal(0)
EIGHT_HOURS = Calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, NONE, NONE))
CALENDARS = (
    EIGHT_HOURS,
    Calendar((FOUR, FOUR, FOUR, FOUR, FOUR, NONE, NONE)),
    Calendar((EIGHT, EIGHT, NONE, EIGHT, EIGHT, NONE, NONE)),
    Calendar((EIGHT, EIGHT, EIGHT, EIGHT, FOUR, NONE, NONE)),
)
TYPES: tuple[LinkType, ...] = (
    "finish_to_start",
    "start_to_start",
    "finish_to_finish",
    "start_to_finish",
)
# Durations of work and elapsed, each unit with the values drawn from: a milestone among them.
DURATIONS: tuple[tuple[DurationUnit, tuple[int, ...]], ...] = (
    ("d", (0, 1, 2, 3, 5)),
    ("h", (1, 4, 13, 20)),
    ("min", (20, 30, 90)),
    ("ed", (1, 2, 3)),
    ("eh", (1, 2, 10, 30)),
    ("emin", (30, 90)),
)
LAGS: tuple[tuple[LagUnit, tuple[int, ...]], ...] = (
    ("d", (-1, 0, 0, 1, 2)),
    ("h", (-3, 3, 12)),
    ("ed", (-1, 1, 2)),
    ("eh", (-5, 2, 30)),
    ("emin", (45,)),
    ("percent", (-50, 50, 100)),
)
STRUCTURES = 400


def ident(number: int) -> UUID:
    """Return the identifier of the task of a number."""
    return UUID(int=number)


@dataclass
class Drawn:
    """A structure drawn: its tasks in the order of the plan, depth first, and its links."""

    tasks: list[Task] = field(default_factory=list[Task])
    links: list[Link] = field(default_factory=list[Link])

    def structure(self) -> Structure:
        """Return the structure drawn, starting on the Monday of the tests."""
        return Structure(tuple(self.tasks), tuple(self.links), MONDAY, CONSTANTS)


class Draw:
    """A generator of fixed seed: a linear congruential one, the constants of Knuth's MMIX.

    Written here rather than taken from ``random``, whose generators the rules of the lint keep
    from the code, and so that a seed draws the same structures whatever the version of Python.
    """

    MULTIPLIER = 6364136223846793005
    INCREMENT = 1442695040888963407
    MODULUS = 2**64

    def __init__(self, seed: int) -> None:
        self.state = seed % self.MODULUS

    def below(self, bound: int) -> int:
        """Draw a whole number from nought to ``bound`` excluded, from the high bits."""
        self.state = (self.state * self.MULTIPLIER + self.INCREMENT) % self.MODULUS
        return (self.state >> 32) * bound >> 32

    def between(self, low: int, high: int) -> int:
        """Draw a whole number from ``low`` to ``high``, both included."""
        return low + self.below(high - low + 1)

    def chance(self, percent: int) -> bool:
        """Draw whether an event of so many chances in a hundred happens."""
        return self.below(100) < percent

    def choice[T](self, among: Sequence[T]) -> T:
        """Draw one of a sequence."""
        return among[self.below(len(among))]

    def pair[T](self, among: Sequence[T]) -> tuple[T, T]:
        """Draw two different members of a sequence, in the order drawn."""
        first = self.below(len(among))
        second = (first + 1 + self.below(len(among) - 1)) % len(among)
        return among[first], among[second]


def drawn_duration(draw: Draw) -> Duration:
    """Draw a duration, of work or elapsed."""
    unit, values = draw.choice(DURATIONS)
    return Duration(Decimal(draw.choice(values)), unit)


def drawn_lag(draw: Draw) -> Lag:
    """Draw a lag, nil half the time, a lead sometimes."""
    if draw.chance(50):
        return Lag(Decimal(0), "d")
    unit, values = draw.choice(LAGS)
    return Lag(Decimal(draw.choice(values)), unit)


def drawn_tree(draw: Draw, drawn: Drawn, parent: UUID | None, depth: int) -> None:
    """Draw the subordinates of a task, or the roots: summaries down to three levels."""
    for _ in range(draw.between(1, 4) if parent is not None else draw.between(2, 5)):
        task_id = ident(len(drawn.tasks) + 1)
        calendar = draw.choice(CALENDARS)
        drawn.tasks.append(Task(task_id, parent, "automatic", drawn_duration(draw), calendar))
        if depth < 3 and draw.chance(35):
            drawn_tree(draw, drawn, task_id, depth + 1)


def drawn_structure(seed: int) -> Drawn:
    """Draw a structure without a manual task: its tree, then links the engine accepts.

    Links of the four types between any two tasks — subordinates, summaries — each kept when it
    neither ties a summary to its subordinate nor closes a loop.
    """
    draw = Draw(seed)
    drawn = Drawn()
    drawn_tree(draw, drawn, None, 0)
    ids = [each.task_id for each in drawn.tasks]
    for _ in range(draw.between(1, 2 * len(ids))):
        predecessor, successor = draw.pair(ids)
        drawn.links.append(Link(predecessor, successor, draw.choice(TYPES), drawn_lag(draw)))
        try:
            schedule(drawn.structure())
        except SchedulingRefusalError:
            drawn.links.pop()
    return drawn


@pytest.mark.story("US-3300")
def test_a_structure_without_a_manual_task_renders_no_negative_float_nor_conflict() -> None:
    # « un test de propriété tire au sort des structures sans tâche manuelle — récapitulatives sur
    # plusieurs niveaux, liaisons des quatre types entre feuilles, vers une récapitulative et depuis
    # une récapitulative, décalages et durées en temps de travail et en temps écoulé, emin, eh et ej
    # compris — : aucune ne rend de marge négative ni de link_conflicts, et la fin de la structure
    # est la fin au plus tard d'au moins une tâche. »
    drawn_summary_links = 0
    for seed in range(STRUCTURES):
        drawn = drawn_structure(seed)
        dated = schedule(drawn.structure())
        assert dated.link_conflicts == (), seed
        floats = {key: each.total_float for key, each in dated.tasks.items()}
        assert all(each is not None and each >= 0 for each in floats.values()), (seed, floats)
        # The task that finishes last, given a float of nil, may finish no later: the finish of
        # the structure is its latest finish.
        finish = max(each.finish for each in dated.tasks.values())
        assert any(
            each.finish == finish and each.total_float == 0 for each in dated.tasks.values()
        ), seed
        summaries = {each.parent_id for each in drawn.tasks}
        drawn_summary_links += any(
            {each.predecessor_id, each.successor_id} & summaries for each in drawn.links
        )
    # The draw reaches what the property is about: links from and to summaries.
    assert drawn_summary_links > STRUCTURES // 2


def phases(count: int, leaves: int) -> Structure:
    """Return phases of so many subordinates each, each phase finish to start before the next."""
    day = Duration(Decimal(1), "d")
    tasks: list[Task] = []
    links: list[Link] = []
    previous: UUID | None = None
    for _ in range(count):
        summary = ident(len(tasks) + 1)
        tasks.append(Task(summary, None, "automatic", day, EIGHT_HOURS))
        for _ in range(leaves):
            tasks.append(Task(ident(len(tasks) + 1), summary, "automatic", day, EIGHT_HOURS))
        if previous is not None:
            links.append(Link(previous, summary, "finish_to_start", Lag(Decimal(0), "d")))
        previous = summary
    return Structure(tuple(tasks), tuple(links), MONDAY, CONSTANTS)


@pytest.mark.story("US-3300")
@pytest.mark.parametrize(
    ("count", "leaves"),
    [(2, 500), (10, 100)],
    ids=["two-summaries-of-500", "ten-phases-of-100"],
)
def test_a_link_between_summaries_is_bounded_once_not_once_per_pair_of_subordinates(
    count: int, leaves: int
) -> None:
    # « la borne qu'une liaison laisse à son prédécesseur se calcule une fois par liaison, non une
    # fois par paire de feuilles : sur deux récapitulatives de 500 feuilles reliées par une
    # liaison, et sur dix phases de 100 feuilles enchaînées phase à phase, le nombre de bornes
    # calculées croît comme la somme des feuilles, non comme leur produit » — each link reaches
    # the subordinates of its successor once, and bounds those of its predecessor once each.
    structure = phases(count, leaves)
    links = count - 1
    assert len(structure.links) == links
    assert counted_bounds(structure) == links * 2 * leaves
    # Twice the subordinates, twice the bounds: a sum, where a product would be four times.
    assert counted_bounds(phases(count, 2 * leaves)) == 2 * counted_bounds(structure)
    # A structure without dates has no backward pass.
    assert counted_bounds(Structure((), (), MONDAY, CONSTANTS)) == 0
    dated = schedule(structure)
    assert dated.link_conflicts == ()
    assert all(each.total_float == 0 for each in dated.tasks.values())
