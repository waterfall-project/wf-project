# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts of the tests of the back and the order each runs them in (#5155, back.yml).

No requirement of the specification speaks of how the chain cuts its tests or how long they take:
these tests cite none.
"""

import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from sharding import in_order, part_of

BACK = Path(__file__).parent.parent
PARTS = 6


class Item(NamedTuple):
    """A test as the order sees it: its name, whether it is heavy, whether it is on the witness."""

    name: str
    heavy: bool = False
    witnessed: bool = False


def on_the_witness(item: Item) -> bool:
    return item.witnessed


def heavy(item: Item) -> bool:
    return item.heavy


def names(items: list[Item]) -> list[str]:
    return [item.name for item in items]


def test_the_parts_are_one_test_in_n_and_hold_every_test_once() -> None:
    items = [f"t{number}" for number in range(11)]
    taken = [part_of(items, part, 4) for part in range(1, 5)]
    assert taken[1][0] == ["t1", "t5", "t9"]
    assert sorted(name for kept, _ in taken for name in kept) == sorted(items)
    assert all(sorted(kept + left) == sorted(items) for kept, left in taken)
    assert part_of([], 1, 4) == ([], [])


def test_the_heavy_tests_are_counted_apart_and_spread_to_within_one() -> None:
    items = [Item(f"t{number}", heavy=number in {0, 1, 2, 3, 4, 5, 6}) for number in range(20)]
    taken = [part_of(items, part, 3, heavy)[0] for part in range(1, 4)]
    assert [sum(item.heavy for item in kept) for kept in taken] == [3, 2, 2]
    assert sorted(names([item for kept in taken for item in kept])) == sorted(names(items))
    assert names(taken[0]) == sorted(names(taken[0]), key=lambda name: int(name[1:]))


def test_the_heavy_tests_take_the_heads_of_the_slices_of_the_processes() -> None:
    items = [Item(f"t{number}") for number in range(12)]
    items[5] = Item("h1", heavy=True)
    items[11] = Item("h2", heavy=True, witnessed=True)
    items[7] = Item("h3", heavy=True)
    ordered = names(in_order(items, on_the_witness, heavy, 3))
    # Three processes, slices of four tests: the heavy tests off the witness first, in the order of
    # the collection, then the one on it, at the heads of the slices 0, 1 and 2.
    assert [ordered[0], ordered[4], ordered[8]] == ["h1", "h3", "h2"]


def test_the_other_tests_keep_their_order_those_on_the_witness_last() -> None:
    items = [
        Item("w1", witnessed=True),
        Item("a"),
        Item("hw", heavy=True, witnessed=True),
        Item("b"),
    ]
    assert names(in_order(items, on_the_witness, heavy, 1)) == ["hw", "a", "b", "w1"]


def test_the_order_loses_and_adds_no_test_whatever_the_processes() -> None:
    items = [
        Item(f"t{number}", heavy=number % 3 == 0, witnessed=number % 4 == 0) for number in range(23)
    ]
    for workers in (0, 1, 2, 5, 23, 40):
        assert sorted(names(in_order(items, on_the_witness, heavy, workers))) == sorted(
            names(items)
        )
    assert in_order([], on_the_witness, heavy, 3) == []


def test_more_heavy_tests_than_places_still_lose_none() -> None:
    items = [Item(f"h{number}", heavy=True) for number in range(5)]
    assert sorted(names(in_order(items, on_the_witness, heavy, 4))) == sorted(names(items))


def collected(*arguments: str) -> subprocess.Popen[str]:
    """Start the collection of the tests of the back, one id a line."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *arguments,
        ],
        cwd=BACK,
        stdout=subprocess.PIPE,
        text=True,
    )


def identifiers(process: subprocess.Popen[str]) -> list[str]:
    out, _ = process.communicate()
    return [line for line in out.splitlines() if "::" in line]


def test_the_parts_of_the_real_list_hold_every_test_once_the_heavy_ones_ahead_and_even() -> None:
    """Collect the real tests: the full list, the heavy ones, and the six parts as they run."""
    everything = collected()
    marked = collected("-m", "heavy")
    parts = [collected("--shard", f"{part}/{PARTS}") for part in range(1, PARTS + 1)]
    complete = identifiers(everything)
    heavy_ones = set(identifiers(marked))
    played = [identifiers(process) for process in parts]
    union = [name for part in played for name in part]
    assert len(union) == len(set(union))
    assert sorted(union) == sorted(complete)
    counts = [sum(name in heavy_ones for name in part) for part in played]
    assert sum(counts) == len(heavy_ones) > 0
    assert max(counts) - min(counts) <= 1
    # One process: the heavy tests of a part are its first ones.
    for part, count in zip(played, counts, strict=True):
        assert all(name in heavy_ones for name in part[:count])
