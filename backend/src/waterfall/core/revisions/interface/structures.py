# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cost structures of a revision: its main one here (WF-REV-0100), and their commands.

Created with the revision, copied with it, their lineage kept (WF-DAT-0030); the amendments and the
risks' own come with EP-08.

Declared by US-0910/L1, without effect: US-0960 fills it; ``load_cost_structures`` writes those of
the witness.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


def list_cost_structures(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """List the structures of a revision, with their commands (``listCostStructures``)."""


def structure_commands(session: Session, project_id: UUID, revision_id: UUID) -> None:
    """Give the commands of the structures of a revision and the conditions each lacks."""


def load_cost_structures(session: Session, project_id: UUID, revision_id: UUID, act: Act) -> None:
    """Write the structures of a revision of the witness, as it imposes them."""
