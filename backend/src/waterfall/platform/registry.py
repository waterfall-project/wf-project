# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An ordered registry: what a module above adds to a module below, without being imported by it.

The copy of a revision, the question of its tasks and lines, its indicators (EP-04), the closing of
a revision, the guard and the recalculation of the reference, the attachments of the work
breakdown, the facets of a node, the formats and the exporters of the exchanges, the fillers of the
witness (EP-06): each is a registry that the module which offers it holds, and that its interface
offers to fill. A later module registers its part at the import of its interface, without the
first importing it (EP-06, "Les points d'extension").

A registry is filled only in a process that imported the module which registers: every registry is
named, and ``registries()`` gives them all with their entries, so that a test can say, for each
process — the API, the worker, the loader of the witness —, that none lacks its extensions (#2180).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# What gives the entries of every registry of the process, by its name, in the order of their
# creation.
_REGISTRIES: dict[str, Callable[[], tuple[object, ...]]] = {}


class Registry[T]:
    """Entries kept in the order of their registration, each at most once."""

    def __init__(self, name: str | None = None) -> None:
        """Hold no entry yet, under a name no other registry of the process bears.

        A registry without a name — a test's — is not listed by ``registries()``.
        """
        self._entries: list[T] = []
        if name is None:
            return
        if name in _REGISTRIES:
            msg = f"a registry {name} exists already"
            raise ValueError(msg)
        _REGISTRIES[name] = self.entries

    def register(self, entry: T) -> Callable[[], None]:
        """Add an entry after the others, and give what withdraws it; refused if held already.

        An entry registered twice would act twice — a copy, two rows for one —: it is refused. The
        withdrawal withdraws this registration once, and does nothing after: called again, it
        never withdraws the same entry registered anew since.
        """
        if entry in self._entries:
            msg = f"{entry!r} is registered already"
            raise ValueError(msg)
        self._entries.append(entry)
        withdrawn = False

        def withdraw() -> None:
            nonlocal withdrawn
            if not withdrawn:
                withdrawn = True
                self._entries.remove(entry)

        return withdraw

    def entries(self) -> tuple[T, ...]:
        """Give the entries, in the order of their registration."""
        return tuple(self._entries)


def registries() -> Mapping[str, tuple[object, ...]]:
    """Give the entries of every registry of the process, by the name of the registry."""
    return {name: entries() for name, entries in _REGISTRIES.items()}
