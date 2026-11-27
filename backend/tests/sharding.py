# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the chain spreads the tests of the back over its parts, and the order each part runs them in.

A part is the i-th of N of the tests, one in N in the order of their collection (``--shard i/N``,
back.yml): the files that load the witness, the longest, are spread over all the parts. Within a
part, the tests given a copy of the template of the witness run last, while it loads, and the ones
marked ``heavy`` — each loads a platform of its own, one to two minutes — run first of their
group: the heavy ones that need no copy before everything, the others first of the tests on the
witness. Left where their files put them, they ended a part, two minutes alone with the other
processes idle (#5155); first, they play beside the hundreds of tests that follow.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def part_of[T](items: Sequence[T], part: int, parts: int) -> tuple[list[T], list[T]]:
    """Split the items into those of the part ``part`` of ``parts``, and the rest."""
    kept: list[T] = []
    left: list[T] = []
    for index, item in enumerate(items):
        (kept if index % parts == part - 1 else left).append(item)
    return kept, left


def in_order[T](
    items: Sequence[T], on_the_witness: Callable[[T], bool], heavy: Callable[[T], bool]
) -> list[T]:
    """Give the heavy tests off the witness, the others off it, then those on it, heavy first.

    Each group keeps the order of the collection.
    """
    ahead = [item for item in items if heavy(item) and not on_the_witness(item)]
    others = [item for item in items if not heavy(item) and not on_the_witness(item)]
    witnessed = [item for item in items if on_the_witness(item)]
    return (
        ahead
        + others
        + [item for item in witnessed if heavy(item)]
        + [item for item in witnessed if not heavy(item)]
    )
