# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""How the chain spreads the tests of the back over its parts, and the order each part runs them in.

A part is the i-th of N of the tests, one in N in the order of their collection, the heavy ones
counted apart (``--shard i/N``, back.yml): the files that load the witness, the longest, are spread
over all the parts, and so are the heavy tests, to within one. In a part, the tests marked
``heavy`` — each loads a platform of its own, one to two minutes — head the slices of the
processes: pytest-xdist (``--dist worksteal``) hands each of its W processes a contiguous slice of
the part and steals from the tail of a slice, never its head; the k-th heavy test takes the head of
the slice of the process k modulo W, the next ones the places that follow the head. So the heavy
tests start together, one per process, as long as there are no more than W of them, and none waits
behind another. W is the count each process of pytest-xdist is handed (``processes``), once
``--maxprocesses`` is applied. Which test a process runs after its heavy one depends on what the
others steal; the order fixes the starts, not the ends. The other tests keep the order of the
collection, those that need a copy of the template of the witness last, while it loads. Left where
their files put them, the heavy tests ended a part, two minutes alone with the other processes idle
(#5155).
"""

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def part_of[T](
    items: Sequence[T], part: int, parts: int, heavy: Callable[[T], bool] = lambda _: False
) -> tuple[list[T], list[T]]:
    """Split the items into those of the part ``part`` of ``parts``, and the rest.

    One item in N of the heavy ones, and one in N of the others, each in the order of the
    collection: the heavy ones, few, are spread evenly over the parts, which one in N of all the
    items would not do. Both lists keep the order of the collection.
    """
    seen = {True: 0, False: 0}
    kept: list[T] = []
    left: list[T] = []
    for item in items:
        kind = heavy(item)
        (kept if seen[kind] % parts == part - 1 else left).append(item)
        seen[kind] += 1
    return kept, left


def processes(config: object) -> int:
    """Count the processes of pytest-xdist this run spreads its tests over: 1 without it.

    Only its processes collect, and each reads the count the controller handed it
    (``workerinput["workercount"]``), once ``--maxprocesses`` and ``auto`` are applied: ``-n`` is
    reset to nothing in them, so it says nothing there. Every process computes the same order.
    """
    given = cast("dict[str, object] | None", getattr(config, "workerinput", None))
    count = given.get("workercount") if given is not None else None
    return count if isinstance(count, int) and count > 0 else 1


def in_order[T](
    items: Sequence[T],
    on_the_witness: Callable[[T], bool],
    heavy: Callable[[T], bool],
    workers: int = 1,
) -> list[T]:
    """Put the heavy tests at the heads of the slices of ``workers`` processes, the others around.

    The heavy tests off the witness take the heads first, then those on it. The others keep the
    order of the collection, those off the witness before those on it. The result depends on the
    items and ``workers`` alone: every process of pytest-xdist computes the same one.
    """
    workers = max(1, workers)
    heavies = [item for item in items if heavy(item) and not on_the_witness(item)] + [
        item for item in items if heavy(item) and on_the_witness(item)
    ]
    light = [item for item in items if not heavy(item)]
    ordered = [item for item in light if not on_the_witness(item)] + [
        item for item in light if on_the_witness(item)
    ]
    size = len(items) // workers
    placed: dict[int, T] = {}
    for rank, item in enumerate(heavies):
        position = (rank % workers) * size + rank // workers
        while position in placed or position >= len(items):
            position = (position + 1) % len(items)
        placed[position] = item
    rest = iter(ordered)
    return [placed[index] if index in placed else next(rest) for index in range(len(items))]
