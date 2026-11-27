# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts of the tests of the back and the order each runs them in (#5155, back.yml)."""

from sharding import in_order, part_of

# A test is its name: on the witness when it starts with "w" or "hw", heavy when it starts with "h".
WITNESSED = ("w1", "hw2", "w3", "hw4")
OFF = ("a", "ha", "b")


def on_the_witness(name: str) -> bool:
    return name.startswith(("w", "hw"))


def heavy(name: str) -> bool:
    return name.startswith("h")


def test_the_parts_are_one_test_in_n_and_hold_every_test_once() -> None:
    items = [f"t{number}" for number in range(11)]
    taken = [part_of(items, part, 4) for part in range(1, 5)]
    assert taken[1][0] == ["t1", "t5", "t9"]
    assert sorted(name for kept, _ in taken for name in kept) == sorted(items)
    assert all(sorted(kept + left) == sorted(items) for kept, left in taken)


def test_the_heavy_tests_off_the_witness_come_first_then_the_others_then_the_witness() -> None:
    items = ["w1", "a", "hw2", "ha", "b", "hw4", "w3"]
    assert in_order(items, on_the_witness, heavy) == ["ha", "a", "b", "hw2", "hw4", "w1", "w3"]


def test_the_order_loses_and_adds_no_test() -> None:
    items = [*OFF, *WITNESSED]
    assert sorted(in_order(items, on_the_witness, heavy)) == sorted(items)
    assert in_order([], on_the_witness, heavy) == []
