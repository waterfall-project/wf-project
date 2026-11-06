# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of a project and their kind (WF-PRJ-0060).

The kind of an account on a project, which the evaluation of an action reads (``contributor_kind``,
WF-ADM-0110); the list read, written whole under its own counter — a project keeps a project
manager —, and the suggestions of the screen, empty while no line of estimate employs a role
(WF-PRJ-0070, EP-07).

Declared by US-0910/L1, without effect: US-0910/L2 fills ``contributor_kind``, US-0930 the rest;
``load_contributors`` writes those of the witness.
"""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

# The two kinds of contributor, as the contract says them (``ContributorKind``).
type ContributorKind = Literal["project_manager", "contributor"]


def contributor_kind(session: Session, project_id: UUID, user_id: UUID) -> ContributorKind | None:
    """Give the kind of an account on a project, ``None`` if it is no contributor."""
    msg = "contributor_kind is filled by US-0910/L2"
    raise NotImplementedError(msg)


def list_contributors(session: Session, project_id: UUID) -> None:
    """List the contributors of a project, with the counter of the list (``listContributors``)."""
    msg = "list_contributors is filled by US-0930"
    raise NotImplementedError(msg)


def set_contributors(session: Session, project_id: UUID, lock_version: int, act: Act) -> None:
    """Write the whole list of the contributors at the version read (``setContributors``)."""
    msg = "set_contributors is filled by US-0930"
    raise NotImplementedError(msg)


def list_contributor_suggestions(session: Session, project_id: UUID) -> None:
    """Suggest the accounts the lines of the project employ (``listContributorSuggestions``)."""
    msg = "list_contributor_suggestions is filled by US-0930"
    raise NotImplementedError(msg)


def load_contributors(session: Session, project_id: UUID, act: Act) -> None:
    """Write the contributors of a project of the witness, as it imposes them."""
    msg = "load_contributors is filled by US-0930"
    raise NotImplementedError(msg)
