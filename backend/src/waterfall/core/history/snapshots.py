# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The snapshots the history keeps, private to the module but for the types its interface offers.

A snapshot is what the planning gives of the objects a write touches (EP-06, "L'historique
annulable"): for each, its identifier, its version (``lock_version``), its label — the name of a
conflict — and its rows, in JSON, which the history keeps without reading them. It is kept in
JSONB, one object per item in its order, and read back the same.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast
from uuid import UUID

if TYPE_CHECKING:
    from collections.abc import Mapping

# A value JSON can hold: what a row of a snapshot is made of.
type JsonValue = bool | int | float | str | list[JsonValue] | dict[str, JsonValue] | None


@dataclass(frozen=True, slots=True)
class ObjectState:
    """An object of the planning as a snapshot holds it, at a version.

    ``rows`` are its rows — of ``node``, ``task``, ``task_link``, ``tracking_entry``, as the
    planning writes them —, which only the planning reads; ``label`` names it in a conflict.
    """

    object_id: UUID
    lock_version: int
    label: str
    rows: Mapping[str, JsonValue]


# The objects a write touches, as they were before it or as they are after it: an object a write
# creates is absent from the first, one it deletes from the second.
type Snapshot = tuple[ObjectState, ...]


def encoded(snapshot: Snapshot) -> list[JsonValue]:
    """Give a snapshot as JSONB keeps it: one object per item, in its order."""
    return [
        {
            "object_id": str(state.object_id),
            "lock_version": state.lock_version,
            "label": state.label,
            "rows": dict(state.rows),
        }
        for state in snapshot
    ]


def decoded(kept: object) -> Snapshot:
    """Give back the snapshot a column of JSONB keeps, in its order."""
    items = cast("list[Mapping[str, JsonValue]]", kept)
    return tuple(
        ObjectState(
            object_id=UUID(cast("str", item["object_id"])),
            lock_version=cast("int", item["lock_version"]),
            label=cast("str", item["label"]),
            rows=cast("Mapping[str, JsonValue]", item["rows"]),
        )
        for item in items
    )


def with_versions(snapshot: Snapshot, versions: Mapping[UUID, int]) -> Snapshot:
    """Give a snapshot whose objects named in ``versions`` are at the version given there."""
    return tuple(
        replace(state, lock_version=versions[state.object_id])
        if state.object_id in versions
        else state
        for state in snapshot
    )
