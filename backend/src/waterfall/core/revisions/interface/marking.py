# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The marking of a revision, in the background task ``revision_mark`` (WF-REV-0020, WF-REV-0090).

In one transaction, under the lock of the revision: still current, its name of version free, its
indicators computed and kept (``compute_indicators``, which EP-10 extends by
``register_indicators``), marked with its moment and its name, the project without a current
revision, ``revision_mark`` inscribed in the journal.

Declared by US-0910/L1, without effect: US-0970 fills the marking, EP-10 the indicators;
``load_marking`` marks a revision of the witness at the instant it imposes, by the same
transaction as the worker.
"""

from typing import TYPE_CHECKING

from waterfall.core.revisions.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# What computes and keeps the indicators of a revision being marked, in their order: EP-10's.
_INDICATORS: Registry[Callable[[Session, UUID], None]] = Registry()


def mark_revision(
    session: Session, revision_id: UUID, version_name: str, description: str | None, act: Act
) -> None:
    """Mark the current revision of a project, in the transaction of the task."""
    msg = "mark_revision is filled by US-0970"
    raise NotImplementedError(msg)


def register_indicators(compute: Callable[[Session, UUID], None]) -> Callable[[], None]:
    """Add what computes and keeps indicators of a revision being marked; give its withdrawal."""
    return _INDICATORS.register(compute)


def compute_indicators(session: Session, revision_id: UUID) -> None:
    """Compute and keep the indicators of a revision being marked, by each computation registered.

    Nothing, until EP-10 registers its own.
    """
    for compute in _INDICATORS.entries():
        compute(session, revision_id)


def load_marking(session: Session, revision_id: UUID, version_name: str, act: Act) -> None:
    """Mark a revision of the witness, at the instant it imposes."""
    msg = "load_marking is filled by US-0970"
    raise NotImplementedError(msg)
