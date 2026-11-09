# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rates of a revision and what it keeps of the reference (WF-REV-0060, WF-REV-0090; US-1500).

A revision is priced at the rates it keeps (``revision_rate``): copied from its source, projected
when the year of reference changes, replaced by those of the reference when its creation accepts
the update, at the opening (``copy_rates``, registered by ``register_copy``); deleted when it is
abandoned (``close_rates``, by ``register_closing``); updated to those of the reference on a
proposal (``rate_update_proposal``, ``apply_rate_update``, ``getRateUpdateProposal``,
``applyRateUpdate``), the command ``apply_rate_update`` asking whether the proposal presents a
category (``rate_update_offered``, by ``register_rate_update``) — US-1500/L1, whose copy, closing
and question the interface takes from ``keeping``, where they are written. Its
marking keeps the images of the roles, the calendars and the categories its lines employ, the
rates retained, and the rate of inflation and the probability of winning of the project
(``keep_images``, by ``register_marking``); the designation of a reference refreshes the budgeted
amounts of the lines of the current revision by their lineage (``refresh_budgeted``, by
``register_designation``); a change of the rate of inflation of the project prices its current
revision again (``reinflate_project``, by ``register_estimate_facts``, which US-1490/L3 declares in
``core/projects``).

Declared by US-1490/L1. What is not filled yet raises ``NotImplementedError`` naming the story that
fills it, which registers it and gives it its arguments and its result.
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.keeping import apply_update, rate_proposal

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.keeping import RateProposal, RateUpdate
    from waterfall.core.revisions.interface import ReferenceDesignated, RevisionMarking
    from waterfall.platform.audit import Act


def keep_images(marking: RevisionMarking) -> None:
    """Keep the images and the rates of a revision being marked, and the values of its project."""
    msg = "keep_images is filled by US-1500"
    raise NotImplementedError(msg)


def refresh_budgeted(designation: ReferenceDesignated) -> None:
    """Refresh the budgeted amounts of the lines of the current revision, by their lineage."""
    msg = "refresh_budgeted is filled by US-1500"
    raise NotImplementedError(msg)


def rate_update_proposal(session: Session, project_id: UUID, revision_id: UUID) -> RateProposal:
    """Give the rates of a revision the reference would change (``getRateUpdateProposal``); 404."""
    return rate_proposal(session, project_id, revision_id)


def apply_rate_update(session: Session, project_id: UUID, update: RateUpdate, act: Act) -> None:
    """Price a revision at the rates proposed for the categories accepted (``applyRateUpdate``).

    Refused, nothing written: the revision unknown (404), at another counter (412), marked, without
    a category proposed, or while a background task writes in it (409, in this order), a category
    the proposal does not present (422). The revision advances by one version.
    """
    apply_update(session, project_id, update, act)


def reinflate_project(session: Session, project_id: UUID) -> None:
    """Price the current revision of a project again, its rate of inflation changed."""
    msg = "reinflate_project is filled by US-1500"
    raise NotImplementedError(msg)
