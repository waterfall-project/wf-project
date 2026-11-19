# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk declared, read and renamed (``createRisk``, ``getRisk``, ``updateRisk``; US-2570).

A risk is declared with its own estimate, a structure of the current revision of the kind ``risk``,
and its provision line in the main structure, under the task, the category and the subproject the
declaration designates or the defaults (WF-RIS-0010, #786): the current revision created first when
the project has none. It is read in a revision, which freezes the version of its own estimate, of
its probability and of its state (WF-RIS-0030): its severity is the total of its own estimate, its
provision that severity weighted by its probability while it is identified, and the share it held
in the reference revision once occurred or dismissed (WF-RIS-0040, WF-RIS-0050). Its identity — its
label, its description, its notes — is a datum of the project (H-02), written at the counter of the
risk read, which advances at every write of the risk, of its evaluation or of its own estimate.

What a reading gives is a ``RiskView``, which the register, the matrix and the portfolio read too;
the rules of its computed fields (``Risk.computed_fields``) follow from its state alone, and the API
writes them. The objects live in ``views``, which the files that read and write a risk build them
from (``declaring``, ``reading``); the conditions of its commands in ``commands``, which the lots
of its other operations judge their refusals by.

Declared by US-2550/L1, the socle of EP-08; filled by US-2570/L1.
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.declaring import change_identity, declare
from waterfall.core.risks.reading import read_found, risk_view
from waterfall.core.risks.stamping import stamp_of_risks

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Writer
    from waterfall.core.projects.interface import Viewer
    from waterfall.core.risks.stamping import RisksStamp
    from waterfall.core.risks.views import RiskEntry, RiskIdentityChange, RiskView


def create_risk(
    session: Session, project_id: UUID, entry: RiskEntry, writer: Writer, viewer: Viewer
) -> RiskView:
    """Declare a risk in the current revision, its own estimate and its provision line with it.

    Refused by the conditions of ``declare_risk`` (409), then by the designations of its provision
    (422), nothing written; the current revision created first when the project has none. Read in
    the revision it was declared in, before the transaction commits.
    """
    risk_id, revision_id = declare(session, project_id, entry, writer, viewer)
    return risk_view(
        session, project_id, read_found(session, project_id, risk_id, revision_id), viewer
    )


def read_risk(
    session: Session, project_id: UUID, risk_id: UUID, revision_id: UUID | None, viewer: Viewer
) -> RiskView:
    """Read a risk in a revision: the current one, or the last marked, when none is named.

    A risk unknown, a revision of another project or one that holds no evaluation of it is not
    found (404); a marked revision gives the evaluation it froze (WF-RIS-0030).
    """
    found = read_found(session, project_id, risk_id, revision_id)
    return risk_view(session, project_id, found, viewer)


def update_risk(
    session: Session, project_id: UUID, change: RiskIdentityChange, writer: Writer, viewer: Viewer
) -> RiskView:
    """Write the identity of a risk at the counter read, and read it in the current revision.

    A datum of the project (H-02, #1783): no revision created — the risk is read in the last marked
    one without a current one —, no entry of the history. Refused unknown (404), at another
    version (412), on a terminal project, then occurred (409).
    """
    change_identity(session, project_id, change, writer.act)
    return read_risk(session, project_id, change.risk_id, None, viewer)


def risks_stamp(session: Session, project_id: UUID) -> RisksStamp:
    """Give the number of the risks of a project and the sum of their counters.

    What the key of the cache of the indicators reads (EP-08, "Les indicateurs et le cache"; #3629):
    a declaration or a deletion moves the first, every write of a risk — a review, an occurrence, a
    change of its identity or of its provision — the second. Filled by US-2630/L1.
    """
    return stamp_of_risks(session, project_id)
