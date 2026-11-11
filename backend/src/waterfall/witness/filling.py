# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the fillers of a revision of the witness — its tasks, its lines — read alike.

The files they read (``witness_tasks.json``, ``witness_lines.json``) are read by strict models, and
name the revision they belong to by an identifier that ends with its number; the node of a task or
a line in a revision other than the one in progress is derived from the file's (US-1570/L2, #2701).
"""

from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict


class Strict(BaseModel):
    """A part of a file of the witness: every key it holds is read, none is missing."""

    model_config = ConfigDict(extra="forbid", frozen=True)


def number_of(revision_id: UUID) -> int | None:
    """Give the number an identifier of the witness ends with, ``None`` if it is not a number."""
    last = str(revision_id).rsplit("-", 1)[1]
    return int(last) if last.isdecimal() else None


def node_identifier(namespace: UUID, revision: int, file_node: UUID, current: int) -> UUID:
    """Give the identifier of a node in its revision: the file's in the one in progress.

    In another revision it is derived from the file's, in the namespace of the slice, so that two
    loadings give the same one.
    """
    if revision == current:
        return file_node
    return uuid5(namespace, f"{revision}/{file_node}")
