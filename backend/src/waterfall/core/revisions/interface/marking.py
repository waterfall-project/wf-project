# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The marking of a revision, in the background task ``revision_mark`` (WF-REV-0020, WF-REV-0090).

In one transaction, under the lock of the revision: still current, its name of version free, its
indicators computed and kept (``compute_indicators``, EP-10), marked with its moment and its name,
the project without a current revision, ``revision_mark`` inscribed in the journal.

Declared by US-0910/L1, without effect: US-0970 fills the marking, EP-10 the indicators;
``load_marking`` marks a revision of the witness at the instant it imposes, by the same
transaction as the worker.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def mark_revision(
    session: Session, revision_id: UUID, version_name: str, description: str | None, act: Act
) -> None:
    """Mark the current revision of a project, in the transaction of the task."""


def compute_indicators(session: Session, revision_id: UUID) -> None:
    """Compute and keep the indicators of a revision being marked: nothing, until EP-10."""


def load_marking(session: Session, revision_id: UUID, version_name: str, act: Act) -> None:
    """Mark a revision of the witness, at the instant it imposes."""
