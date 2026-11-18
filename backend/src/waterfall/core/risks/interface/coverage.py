# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve for risks and the coverage of a project (``getProjectRiskCoverage``; US-2610).

The reserve is the sum of the shares the risks bear in the reference (``risk_reference_share``,
M-01), written when a revision becomes the reference, by designation or by merge; the coverage
compares it with the provisions of the risks identified in the revision read and the costs at
occurrence of the occurred ones (WF-RIS-0050), the re-estimated amount of the lines that came from
them beside, outside the variance (#1761). The estimate reads it in its indicators of the remaining
to commit, by the registry it declares (``register_coverage``), which this answers.

Declared by US-2550/L1, the socle of EP-08; filled by US-2610/L1.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.interface import Coverage


def risk_coverage_of(session: Session, project_id: UUID, revision_id: UUID) -> Coverage:
    """Give the coverage of the risks of a revision of a project: its reserve, provisions, costs."""
    msg = "risk_coverage_of is filled by US-2610/L1"
    raise NotImplementedError(msg)
