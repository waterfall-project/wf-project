# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision of an identified risk changed (``updateRiskProvision``; US-2580).

The category, the subproject and the task of the provision line of a risk, an entry of the current
revision (WF-RIS-0010, WF-RIS-0020; H-02, #1782), at the counter of the risk read: a field not sent
stays the risk's, a task named moves the line under it, the total of the estimate unchanged. The
line itself is written by the estimate, at the request of the risks alone (EP-08, "Modules").

Declared by US-2550/L1, the socle of EP-08; filled by US-2580/L1.
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.interface.risks import RiskView


class Omitted(Enum):
    """A field of the provision a change does not send: the risk's stays."""

    FIELD = "omitted"


OMITTED = Omitted.FIELD


@dataclass(frozen=True, slots=True)
class RiskProvisionChange:
    """The provision of a risk written at the counter read (``RiskProvisionUpdate``).

    ``OMITTED`` keeps what the risk designates; a subproject or a task ``None`` takes the provision
    out of its subproject, or gives the line back to the first task of the first level.
    """

    risk_id: UUID
    lock_version: int
    provision_cost_category_id: UUID | Omitted = OMITTED
    provision_subproject_id: UUID | Omitted | None = OMITTED
    provision_task_id: UUID | Omitted | None = OMITTED


def update_risk_provision(
    session: Session, project_id: UUID, change: RiskProvisionChange, writer: Writer, viewer: Viewer
) -> RiskView:
    """Change the provision of an identified risk, and read it in the current revision."""
    msg = "update_risk_provision is filled by US-2580/L1"
    raise NotImplementedError(msg)
