# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rates of a revision and what it keeps of the reference (WF-REV-0060, WF-REV-0090; US-1500).

A revision is priced at the rates it keeps (``revision_rate``): copied from its source, projected
when the year of reference changes, at the opening (``copy_rates``, registered by
``register_copy``); deleted when it is abandoned (``close_rates``, by ``register_closing``); updated
to those of the reference on a proposal (``rate_update_proposal``, ``apply_rate_update``,
``getRateUpdateProposal``, ``applyRateUpdate``). Its marking keeps the images of the roles, the
calendars and the categories its lines employ, the rates retained, and the rate of inflation and
the probability of winning of the project (``keep_images``, by ``register_marking``); the
designation of a reference refreshes the budgeted amounts of the lines of the current revision by
their lineage (``refresh_budgeted``, by ``register_designation``); a change of the rate of
inflation of the project prices its current revision again (``reinflate_project``, by
``register_estimate_facts``, which US-1490/L3 declares in ``core/projects``).

Declared by US-1490/L1. What a registry of EP-04 or EP-06 calls is registered without effect —
nothing to copy or delete while no rate is written —; the rest raises ``NotImplementedError``
naming the story that fills it, which registers it and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import (
        ReferenceDesignated,
        RevisionClosing,
        RevisionCopy,
        RevisionMarking,
    )


def copy_rates(copy: RevisionCopy) -> None:
    """Copy the rates of the source into the revision opened, projected if the year changes.

    Nothing to copy until US-1500 writes the rates.
    """
    del copy


def close_rates(closing: RevisionClosing) -> None:
    """Delete the rates of a revision abandoned: the lines follow their nodes.

    Nothing to delete until US-1500 writes the rates.
    """
    del closing


def keep_images(marking: RevisionMarking) -> None:
    """Keep the images and the rates of a revision being marked, and the values of its project."""
    msg = "keep_images is filled by US-1500"
    raise NotImplementedError(msg)


def refresh_budgeted(designation: ReferenceDesignated) -> None:
    """Refresh the budgeted amounts of the lines of the current revision, by their lineage."""
    msg = "refresh_budgeted is filled by US-1500"
    raise NotImplementedError(msg)


def rate_update_proposal(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the rates of a revision the reference would change (``getRateUpdateProposal``)."""
    msg = "rate_update_proposal is filled by US-1500"
    raise NotImplementedError(msg)


def apply_rate_update(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Price a revision at the rates of the reference for the categories named."""
    msg = "apply_rate_update is filled by US-1500"
    raise NotImplementedError(msg)


def reinflate_project(session: Session, project_id: UUID) -> None:
    """Price the current revision of a project again, its rate of inflation changed."""
    msg = "reinflate_project is filled by US-1500"
    raise NotImplementedError(msg)
