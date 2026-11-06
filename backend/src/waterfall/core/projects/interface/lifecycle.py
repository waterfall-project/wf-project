# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cycle of life of a project (§3.3.2): its next state, its transitions, its exits.

``next_state`` is a pure function of the facts — the state, whether the project has a revision, a
reference, a code — that gives the next state, its trigger and the conditions that remain
(WF-CYC-0050). The transactions that realise a fact — ``createRevision``,
``designateReferenceRevision``, ``updateProject`` for the code — call ``advance`` under the lock of
the project, which writes the state and the transition, at the instant of the transaction, its
author the account that realised the fact (Created → Pricing, Pricing → In progress, WF-CYC-0030).
An exit writes likewise, with its reason, and refuses a project that bears a current revision
(WF-CYC-0090). The transitions are listed in their order (WF-CYC-0130).

Declared by US-0910/L1, raising until filled — but ``advance``, without effect, which US-0920/L1,
US-0950 and US-0960 call before it moves anything: US-0980/L1 fills it, without the reference, and
US-0980/L2 the passage to In progress; ``load_transitions`` writes those of the witness at its
instants.
"""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface.projects import ProjectState
    from waterfall.platform.audit import Act

# The two facts that move a project forward, as the contract says them (``LifecycleTrigger``).
type LifecycleTrigger = Literal["first_revision_created", "reference_designated_and_code_set"]


def next_state(
    state: ProjectState, *, has_revision: bool, has_reference: bool, has_code: bool
) -> None:
    """Give the next state of a project, its trigger and the conditions that remain."""
    msg = "next_state is filled by US-0980/L1"
    raise NotImplementedError(msg)


def advance(session: Session, project_id: UUID, trigger: LifecycleTrigger, act: Act) -> None:
    """Move a project locked by the caller to its next state, if the fact realised does."""


def exit_project(
    session: Session, project_id: UUID, to_state: ProjectState, reason: str | None, act: Act
) -> None:
    """Take a project out of its cycle, to a terminal state, with its reason (``exitProject``)."""
    msg = "exit_project is filled by US-0980/L1"
    raise NotImplementedError(msg)


def list_state_transitions(session: Session, project_id: UUID) -> None:
    """List the transitions of a project, in their order (``listProjectStateTransitions``)."""
    msg = "list_state_transitions is filled by US-0980/L1"
    raise NotImplementedError(msg)


def load_transitions(session: Session, project_id: UUID, act: Act) -> None:
    """Write the transitions of a project of the witness, at the instants it imposes."""
    msg = "load_transitions is filled by US-0980/L1"
    raise NotImplementedError(msg)
