# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An ordered registry, private to the module: what the later epics add to the revisions.

The copy of a revision, the question of its tasks and lines and its indicators are each a
registry, which the interface offers to fill (``register_copy``, ``register_tasks_and_lines``,
``register_indicators``): a later module registers its part without this one importing it.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class Registry[T]:
    """Entries kept in the order of their registration, each at most once."""

    def __init__(self) -> None:
        """Hold no entry yet."""
        self._entries: list[T] = []

    def register(self, entry: T) -> Callable[[], None]:
        """Add an entry after the others, and give what withdraws it; refused if held already.

        An entry registered twice would act twice — a copy, two rows for one —: it is refused.
        """
        if entry in self._entries:
            msg = f"{entry!r} is registered already"
            raise ValueError(msg)
        self._entries.append(entry)
        return lambda: self._entries.remove(entry)

    def entries(self) -> tuple[T, ...]:
        """Give the entries, in the order of their registration."""
        return tuple(self._entries)
