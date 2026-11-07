# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the history does before a revision is marked or abandoned: its stacks and plans removed.

Registered at the import of the interface in the closing of the revisions (``register_closing``),
under the stage ``history``, which runs first: the planning deletes its nodes after it, under the
stage ``content`` (EP-06, "Les points d'extension"). The entries and the plans of the revision are
deleted, as no write of it will be undone any more (WF-IHM-0110).

Declared by US-1380/L1, without effect until US-1450/L1 keeps entries and plans.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from waterfall.core.revisions.interface import RevisionClosing


def close_history(closing: RevisionClosing) -> None:
    """Delete the entries and the plans of a revision about to be marked or abandoned.

    Nothing is kept before US-1450/L1.
    """
    del closing
