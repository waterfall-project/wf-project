# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The register of the risks of a project (``listRisks``; US-2600).

The risks as a revision freezes them (WF-RIS-0030), filtered, sorted and paginated by the server,
with the provision totals of all those the filters retain, whatever the page (WF-RIS-0040,
WF-IHM-0130, #1367): the identified at their current provision, the occurred and the dismissed at
the share they held in the reference, and the reserve beside them (WF-RIS-0050).

Declared by US-2550/L1, the socle of EP-08; filled by US-2600/L1. What it asks for and gives lives
in ``views`` (``RiskFilters``, ``RiskSort``, ``RiskPage``, ``RiskList``, ``ProvisionTotals``).
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.registering import read_register

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.views import RiskFilters, RiskList, RiskPage, RiskSort


def list_risks(
    session: Session,
    project_id: UUID,
    query: tuple[RiskFilters, RiskSort, RiskPage],
    viewer: Viewer,
) -> RiskList:
    """Read a page of the register of a project in a revision, and the totals of those retained.

    The revision named, else the current, else the last marked; one of another project is not
    found (404). A risk is read as ``read_risk`` reads it; the filters, the sort and the totals
    follow the columns it is read at, those of the risks retained and not of the page.
    """
    return read_register(session, project_id, query, viewer)
